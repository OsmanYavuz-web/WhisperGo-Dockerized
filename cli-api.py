#!/usr/bin/env python3
"""
WhisperGo CLI Mode API
- Her istekte whisper-cli çağırır
- Model bellekte tutulmaz
- İşlem bitince RAM serbest kalır
"""
import os
import sys
import json
import tempfile
import subprocess
import shutil
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import cgi

# Konfigürasyon
PORT = int(os.environ.get("WHISPER_PORT", 6666))
HOST = os.environ.get("WHISPER_HOST", "0.0.0.0")
MODEL = os.environ.get("WHISPER_MODEL", "ggml-base.bin")
LANGUAGE = os.environ.get("WHISPER_LANGUAGE", "tr")
MODEL_PATH = f"/app/models/{MODEL}"
CLI_PATH = "/app/bin/whispergo-cli"


class CLIHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[CLI-API] {args[0]}", flush=True)

    def send_json(self, data, status=200):
        response = json.dumps(data, ensure_ascii=False)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(response.encode('utf-8')))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(response.encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/" or self.path == "/health":
            self.send_json({
                "status": "ok",
                "mode": "cli",
                "model": MODEL,
                "language": LANGUAGE,
                "message": "WhisperGo CLI Mode API"
            })
        else:
            self.send_json({"error": "Not found"}, 404)

    def do_POST(self):
        if self.path != "/inference":
            self.send_json({"error": "Not found"}, 404)
            return

        try:
            # Multipart form data parse et
            content_type = self.headers.get('Content-Type', '')
            
            if 'multipart/form-data' in content_type:
                form = cgi.FieldStorage(
                    fp=self.rfile,
                    headers=self.headers,
                    environ={
                        'REQUEST_METHOD': 'POST',
                        'CONTENT_TYPE': content_type
                    }
                )
                
                # Dosyayı al
                if 'file' not in form:
                    self.send_json({"error": "Dosya bulunamadı. 'file' alanı gerekli."}, 400)
                    return
                
                file_item = form['file']
                if not file_item.file:
                    self.send_json({"error": "Geçersiz dosya"}, 400)
                    return
                
                # Dil parametresi
                lang = LANGUAGE
                if 'language' in form:
                    lang = form['language'].value
                
                # Response format
                response_format = "json"
                if 'response_format' in form:
                    response_format = form['response_format'].value
                
                # Geçici dosyaya kaydet
                with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp:
                    shutil.copyfileobj(file_item.file, tmp)
                    tmp_path = tmp.name
                
                try:
                    # whisper-cli çağır
                    result = self.run_whisper(tmp_path, lang, response_format)
                    self.send_json(result)
                finally:
                    # Geçici dosyayı sil
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
            else:
                self.send_json({"error": "Content-Type multipart/form-data olmalı"}, 400)
                
        except Exception as e:
            print(f"[CLI-API] Hata: {e}", flush=True)
            self.send_json({"error": str(e)}, 500)

    def run_whisper(self, audio_path, language, response_format):
        """whisper-cli çalıştır ve sonucu döndür"""
        print(f"[CLI-API] 🎯 İşleniyor: {os.path.basename(audio_path)}, Dil: {language}", flush=True)
        
        # Output dosyası
        output_base = audio_path.rsplit('.', 1)[0]
        
        cmd = [
            CLI_PATH,
            "--model", MODEL_PATH,
            "--language", language,
            "--output-json",
            "--output-file", output_base,
            "--file", audio_path
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 dakika timeout
            )
            
            if result.returncode != 0:
                return {
                    "error": "Whisper işlemi başarısız",
                    "details": result.stderr
                }
            
            # JSON çıktısını oku
            json_output = f"{output_base}.json"
            if os.path.exists(json_output):
                with open(json_output, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                os.unlink(json_output)
                
                # Basit format
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
                # Fallback: stdout'tan al
                return {"text": result.stdout.strip()}
                
        except subprocess.TimeoutExpired:
            return {"error": "İşlem zaman aşımına uğradı (5 dakika)"}
        except Exception as e:
            return {"error": f"İşlem hatası: {str(e)}"}


def main():
    # Model kontrolü
    if not os.path.exists(MODEL_PATH):
        print(f"[CLI-API] ⚠️  Model bulunamadı: {MODEL_PATH}")
        print(f"[CLI-API] Model indiriliyor...")
    
    print("=" * 50)
    print("  WhisperGo CLI Mode API")
    print("=" * 50)
    print(f"  Host:     {HOST}")
    print(f"  Port:     {PORT}")
    print(f"  Model:    {MODEL}")
    print(f"  Language: {LANGUAGE}")
    print("=" * 50)
    print()
    print(f"[CLI-API] 🎧 Dinleniyor: http://{HOST}:{PORT}", flush=True)
    print(f"[CLI-API] 📝 Her istekte model yüklenir, işlem bitince bellek serbest", flush=True)
    print()
    
    server = HTTPServer((HOST, PORT), CLIHandler)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[CLI-API] Kapatılıyor...")
        server.shutdown()


if __name__ == "__main__":
    main()
