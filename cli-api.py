#!/usr/bin/env python3
"""
WhisperGo CLI Mode API (Queue-Based)
- İstekleri sıraya alır (ThreadingHTTPServer + Queue)
- Tek worker thread ile işlemleri sırayla yapar (RAM/CPU koruması)
- Timeout .env dosyasından yönetilir
"""
import os
import sys
import json
import tempfile
import subprocess
import shutil
import threading
import queue
import time
import uuid
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
import cgi

# ==========================================
# KONFİGÜRASYON
# ==========================================
PORT = int(os.environ.get("WHISPER_PORT", 8080))
HOST = os.environ.get("WHISPER_HOST", "0.0.0.0")
MODEL = os.environ.get("WHISPER_MODEL", "ggml-base.bin")
LANGUAGE = os.environ.get("WHISPER_LANGUAGE", "tr")
TIMEOUT = int(os.environ.get("WHISPER_TIMEOUT", 1200))  # Default 20dk

MODEL_PATH = os.environ.get("WHISPER_MODEL_PATH", f"/app/models/{MODEL}")
# Path ayarları
# Öncelik: Env Var -> Local Bin -> Docker Path
DEFAULT_LOCAL_CLI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin", "whisper-cli.exe")
if os.path.exists(DEFAULT_LOCAL_CLI):
    DEFAULT_CLI = DEFAULT_LOCAL_CLI
else:
    DEFAULT_CLI = "/app/bin/whispergo-cli"

CLI_PATH = os.environ.get("WHISPER_CLI_PATH", DEFAULT_CLI)

# ==========================================
# QUEUE SISTEMI
# ==========================================
# İşleri sıraya koymak için kuyruk
job_queue = queue.Queue()

# İş sonuçlarını saklamak için dictionary (Thread-safe dict kullanımı basittir)
# Structure: { job_id: { "status": "pending"|"processing"|"completed"|"failed", "result": ..., "error": ... } }
job_results = {}
results_lock = threading.Lock()

class WorkerThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.daemon = True

    def run(self):
        print(f"[WORKER] 🚀 Kuyruk işleyicisi başlatıldı. Timeout: {TIMEOUT}sn", flush=True)
        while True:
            # Kuyruktan iş al
            job = job_queue.get()
            job_id = job['id']
            audio_path = job['path']
            lang = job['lang']
            fmt = job['format']

            print(f"[WORKER] ⏳ İş alınıyor: {job_id} (Kuyruk: {job_queue.qsize()})", flush=True)

            # Durumu güncelle: Processing
            with results_lock:
                job_results[job_id]['status'] = 'processing'

            try:
                # Whisper işlemini başlat
                result = self.run_whisper(audio_path, lang, fmt)
                
                with results_lock:
                    job_results[job_id]['status'] = 'completed'
                    job_results[job_id]['result'] = result
            
            except Exception as e:
                print(f"[WORKER] ❌ Hata: {e}", flush=True)
                with results_lock:
                    job_results[job_id]['status'] = 'failed'
                    job_results[job_id]['error'] = str(e)
            
            finally:
                # Geçici dosyayı her durumda sil
                if os.path.exists(audio_path):
                    try:
                        os.unlink(audio_path)
                    except:
                        pass
                
                # İş tamamlandı sinyali
                job_queue.task_done()
                print(f"[WORKER] ✅ İş bitti: {job_id}", flush=True)

    def run_whisper(self, audio_path, language, response_format):
        output_base = audio_path.rsplit('.', 1)[0]
        
        cmd = [
            CLI_PATH,
            "--model", MODEL_PATH,
            "--language", language,
            "--output-json",
            "--output-file", output_base,
            "--file", audio_path
        ]

        # Subprocess çalıştır
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=TIMEOUT
        )

        if res.returncode != 0:
            raise Exception(f"CLI Error: {res.stderr}")

        # JSON oku
        json_output = f"{output_base}.json"
        if os.path.exists(json_output):
            with open(json_output, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # Json dosyasını silmeye gerek yok, unlink yukarıda yapılıyor ama clean kalması için silelim
            os.unlink(json_output)
            
            text = data.get("transcription", [{}])[0].get("text", "").strip()

            if response_format == "text":
                return {"text": text}
            else:
                return {
                    "text": text,
                    "language": language,
                    "model": MODEL,
                    "segments": data.get("transcription", [])
                }
        else:
            # Fallback
            return {"text": res.stdout.strip()}


# ==========================================
# HTTP SERVER
# ==========================================

# Çoklu thread desteği için (requestler birbirini bloklamasın, queue'ya atsın)
class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

class CLIHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Log kirliliğini azaltmak için sadece önemli logları basabiliriz
        pass

    def send_json(self, data, status=200):
        try:
            response = json.dumps(data, ensure_ascii=False)
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(response.encode('utf-8'))
        except Exception as e:
            print(f"[API] Response error: {e}", flush=True)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        # ------------------------------------------------
        # SWAGGER UI & DOCS
        # ------------------------------------------------
        if self.path == "/docs":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = """
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <title>WhisperGo API Docs</title>
                <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css" />
                <style>
                    body { margin: 0; padding: 0; }
                    .swagger-ui .topbar { display: none; } 
                </style>
            </head>
            <body>
                <div id="swagger-ui"></div>
                <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
                <script>
                    window.onload = () => {
                        window.ui = SwaggerUIBundle({
                            url: '/swagger.json',
                            dom_id: '#swagger-ui',
                        });
                    };
                </script>
            </body>
            </html>
            """
            self.wfile.write(html.encode('utf-8'))
            return

        if self.path == "/swagger.json":
            try:
                # Docker ve Local uyumlu path
                # Öncelik: Çalışılan dizindeki dosya (Local)
                swagger_path = "swagger.json"
                if not os.path.exists(swagger_path):
                    # Fallback: Docker path
                    swagger_path = "/app/swagger.json"

                with open(swagger_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(content.encode('utf-8'))
            except Exception as e:
                self.send_json({"error": "Swagger dosyası bulunamadı", "details": str(e)}, 404)
            return

        # ------------------------------------------------
        # NORMAL API ENDPOINTS
        # ------------------------------------------------
        # Sağlık kontrolü
        if self.path == "/" or self.path == "/health":
            self.send_json({
                "status": "ok",
                "queue_size": job_queue.qsize(),
                "timeout_setting": TIMEOUT,
                "active_jobs": len(job_results)
            })
            return

        # Job durumu sorgulama: /status/JOB_ID
        if self.path.startswith("/status/"):
            job_id = self.path.split("/")[-1]
            with results_lock:
                job_data = job_results.get(job_id)
            
            if job_data:
                self.send_json(job_data)
            else:
                self.send_json({"error": "Job not found"}, 404)
            return

        self.send_json({"error": "Not found"}, 404)

    def do_POST(self):
        if self.path != "/inference":
            self.send_json({"error": "Not found"}, 404)
            return

        try:
            ctype = self.headers.get('Content-Type', '')
            if 'multipart/form-data' not in ctype:
                self.send_json({"error": "Content-Type multipart/form-data olmalı"}, 400)
                return

            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={'REQUEST_METHOD': 'POST', 'CONTENT_TYPE': ctype}
            )

            if 'file' not in form:
                self.send_json({"error": "Dosya gerekli"}, 400)
                return

            file_item = form['file']
            if not file_item.file:
                self.send_json({"error": "Geçersiz dosya"}, 400)
                return

            # Parametreler
            lang = LANGUAGE
            if 'language' in form:
                lang = form['language'].value
            
            resp_format = "json"
            if 'response_format' in form:
                resp_format = form['response_format'].value
            
            # Async mod isteği? (Varsayılan: Asenkron - True)
            # Eğer client 'async=false' gönderirse bekleriz.
            is_async = True
            if 'async' in form and form['async'].value.lower() == 'false':
                is_async = False

            # Temp dosyaya kaydet
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp:
                shutil.copyfileobj(file_item.file, tmp)
                tmp_path = tmp.name

            # Job oluştur
            job_id = str(uuid.uuid4())
            job_info = {
                "id": job_id,
                "path": tmp_path,
                "lang": lang,
                "format": resp_format
            }

            # Sonuç deposuna 'pending' olarak ekle
            with results_lock:
                job_results[job_id] = {"status": "pending", "submitted_at": time.time()}

            # Kuyruğa at
            job_queue.put(job_info)
            print(f"[API] 📥 Yeni iş kuyruğa eklendi: {job_id} (Mod: {'ASYNC' if is_async else 'SYNC'})", flush=True)

            if is_async:
                # Hemen job_id dön
                self.send_json({
                    "job_id": job_id,
                    "status": "queued",
                    "message": "İşlem sıraya alındı. /status/<job_id> ile kontrol edebilirsiniz."
                })
            else:
                # İş bitene kadar bekle (Polling)
                # Client timeout'a düşmemesi için arada heartbeat atamıyoruz HTTP 1.1'de kolayca.
                # Bu yüzden sadece while loop ile bekleyeceğiz.
                start_time = time.time()
                while True:
                    # Timeout kontrolü (Global timeout + 10sn buffer)
                    if time.time() - start_time > TIMEOUT + 10:
                        self.send_json({"error": "Server-side timeout waiting for job"}, 504)
                        break

                    with results_lock:
                        status = job_results[job_id]['status']
                        result = job_results[job_id].get('result')
                        error = job_results[job_id].get('error')

                    if status == 'completed':
                        self.send_json(result)
                        # Memory cleanup (optional logic needed for production long-run)
                        with results_lock:
                            del job_results[job_id]
                        break
                    
                    elif status == 'failed':
                        self.send_json({"error": error}, 500)
                        with results_lock:
                            del job_results[job_id]
                        break
                    
                    time.sleep(0.5)

        except Exception as e:
            print(f"[API] Critical Error: {e}", flush=True)
            self.send_json({"error": str(e)}, 500)

def download_model_if_missing():
    """Model dosyası yoksa indirir"""
    
    # Model yolu environment variable'dan mı geliyor yoksa default mu?
    # Eğer environment'ta tam path verildiyse ve dosya yoksa, sadece uyarı verip çıkabiliriz veya indirmeyi deneyebiliriz.
    # Biz burada varsayılan 'models/' klasörüne indirmeyi hedefleyeceğiz.
    
    global MODEL_PATH
    
    if os.path.exists(MODEL_PATH):
        return

    print(f"[CLI-API] ⬇️  Model bulunamadı: {MODEL_PATH}")
    print(f"[CLI-API] Model indiriliyor (Hugging Face)...")

    # Model adını path'ten çıkar (örn: .../ggml-base.bin -> base)
    filename = os.path.basename(MODEL_PATH)
    if filename.startswith("ggml-") and filename.endswith(".bin"):
        model_name = filename.replace("ggml-", "").replace(".bin", "")
    else:
        # Standart isimlendirme değilse varsayılan 'base' kabul et
        model_name = "base"
    
    # İndirme URL'si (ggerganov repo)
    url = f"https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-{model_name}.bin"
    
    import urllib.request
    
    # Klasörü oluştur
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    
    try:
        def progress(block_num, block_size, total_size):
            downloaded = block_num * block_size
            if total_size > 0:
                percent = downloaded * 100 / total_size
                if block_num % 100 == 0:  # Her seferinde basma
                    print(f"\r[DOWNLOAD] {percent:.1f}% ", end="")

        urllib.request.urlretrieve(url, MODEL_PATH, progress)
        print("\n[CLI-API] ✅ Model başarıyla indirildi!")
    except Exception as e:
        print(f"\n[CLI-API] ❌ Model indirilemedi: {e}")
        print(f"Lütfen manuel indirin: {url}")


def main():
    # Modeli kontrol et / indir
    download_model_if_missing()

    if not os.path.exists(MODEL_PATH):
        print(f"[CLI-API] ⚠️  KRİTİK HATA: Model dosyası yok: {MODEL_PATH}")
        # Devam edersek worker hata verir ama sunucu açık kalır.
    
    print(f"🚀 WhisperGo Queue-API Başlatılıyor...")
    print(f"   Port: {PORT}, Timeout: {TIMEOUT}s")
    
    # Worker thread başlat
    w = WorkerThread()
    w.start()

    # Server başlat
    server = ThreadingHTTPServer((HOST, PORT), CLIHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()

if __name__ == "__main__":
    main()
