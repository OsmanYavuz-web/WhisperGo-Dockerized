# 🐳 WhisperGo-Dockerized

Bu proje, OpenAI'nin Whisper modelinin yüksek performanslı C/C++ implementasyonu olan [whisper.cpp](https://github.com/ggml-org/whisper.cpp) üzerine inşa edilmiş, Dockerize edilmiş, bağımsız ve hafif bir API servisidir.

## ✨ Özellikler

*   🚀 **Yüksek Performans:** C/C++ tabanlı motor, Multi-Stage build ile optimize edilmiş imaj.
*   🐋 **Docker Ready:** Tek komutla (Docker Compose) ayağa kalkmaya hazır.
*   🔒 **Güvenli:** Non-root (yetkisiz) kullanıcı ile çalışarak prodüksiyon güvenliği sağlar.
*   🌐 **REST API:** Kolay entegrasyon için hazır HTTP server (Queue & Async Support).
*   🖥️ **Web Arayüzü:** Ses dosyalarını tarayıcı üzerinden test etmek için yerleşik Swagger UI.
*   🌍 **Çok Dilli:** Türkçe dahil 99+ dilde yüksek doğrulukta transkripsiyon.
*   📦 **Standalone:** Harici hiçbir kütüphaneye veya bağımlılığa ihtiyaç duymaz.
*   💾 **CLI Mode:** Her istekte model yüklenir, bellek sadece işlem sırasında kullanılır.

---

## 🚀 Kurulum (Seçiminizi Yapın)

### Seçenek 1: Docker (Önerilen)
Hiçbir şey kurmanıza gerek yok, sadece Docker yeterli.

```bash
# Servisi başlat (Model yoksa otomatik indirilecektir)
docker-compose up -d --build

# Logları takip et
docker-compose logs -f
```
Server: `http://localhost:8080`

---

### Seçenek 2: Local Geliştirme (Python - Docker'sız)
Eğer kendi makinenizde `whisper.cpp` binary'si ile çalıştırmak isterseniz:

1.  **Gereksinimler:** Python 3.9+, [whisper-cli](https://github.com/ggml-org/whisper.cpp) binary dosyası.
2.  **Çalıştırma:**

**Windows (PowerShell):**
```powershell
# Yolları kendi sistemine göre düzenle
$env:WHISPER_CLI_PATH="C:\Tools\whisper.cpp\main.exe"
$env:WHISPER_MODEL_PATH="C:\Tools\whisper.cpp\models\ggml-base.bin"
$env:WHISPER_PORT="8080"

python cli-api.py
```

---

## 📡 API Kullanımı

### 1. Swagger UI (Web Arayüzü)
Tarayıcıdan **[http://localhost:8080/docs](http://localhost:8080/docs)** adresine gidin.

### 2. cURL ile Kullanım

**Senkron (Bekleyerek):**
```bash
curl http://localhost:8080/inference \
  -H "Content-Type: multipart/form-data" \
  -F file="@ses-dosyasi.wav" \
  -F language="tr"
```

**Asenkron (Hemen Job ID Al):**
```bash
curl http://localhost:8080/inference \
  -H "Content-Type: multipart/form-data" \
  -F file="@ses-dosyasi.wav" \
  -F async="true"
```
_Dönen `job_id` ile durum sorgulama: `/status/{job_id}`_

---

## ⚙️ Yapılandırma (`.env`)

Varsayılan ayarları değiştirmek için `.env` dosyasını düzenleyin:

| Değişken | Varsayılan | Açıklama |
|----------|------------|----------|
| `PORT` | `8080` | Dış erişim portu |
| `WHISPER_MODEL` | `ggml-base.bin` | Model boyutu (tiny, base, small, medium, large) |
| `WHISPER_TIMEOUT` | `1200` | İşlem başına zaman aşımı (saniye) |

---

## 📁 Klasör Yapısı

```text
WhisperGo-Dockerized/
├── Dockerfile          # Multi-Stage build
├── docker-compose.yml  # Servis orkestrasyonu
├── cli-api.py          # Queue & Thread tabanlı Python API
├── swagger.json        # OpenAPI Dokümantasyonu
├── .env                # Ayarlar
└── models/             # Modeller (Otomatik iner)
```

## 👤 Hazırlayan

**Hazırlayan:** Osman Yavuz  
**📧 E-posta:** omnyvz.yazilim@gmail.com