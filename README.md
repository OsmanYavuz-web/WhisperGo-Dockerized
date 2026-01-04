# 🐳 WhisperGo-Dockerized

Bu proje, OpenAI'nin Whisper modelinin yüksek performanslı C/C++ implementasyonu olan [whisper.cpp](https://github.com/ggml-org/whisper.cpp) üzerine inşa edilmiş, Dockerize edilmiş, bağımsız ve hafif bir API servisidir.

## ✨ Özellikler

*   🚀 **Yüksek Performans:** C/C++ tabanlı motor, Multi-Stage build ile optimize edilmiş imaj.
*   🐋 **Docker Ready:** Tek komutla (Docker Compose) ayağa kalkmaya hazır.
*   🔒 **Güvenli:** Non-root (yetkisiz) kullanıcı ile çalışarak prodüksiyon güvenliği sağlar.
*   🌐 **REST API:** Kolay entegrasyon için hazır HTTP server.
*   🖥️ **Web Arayüzü:** Ses dosyalarını tarayıcı üzerinden test etmek için yerleşik arayüz.
*   🌍 **Çok Dilli:** Türkçe dahil 99+ dilde yüksek doğrulukta transkripsiyon.
*   📦 **Standalone:** Harici hiçbir kütüphaneye veya bağımlılığa ihtiyaç duymaz.
*   💾 **CLI Mode:** Her istekte model yüklenir, bellek sadece işlem sırasında kullanılır.

## 🚀 Hızlı Başlangıç

Projeyi ayağa kaldırmak için aşağıdaki adımları izleyin:

```bash
# Servisi başlat (Model yoksa otomatik indirilecektir)
docker-compose up -d --build

# Logları takip et
docker-compose logs -f
```

Server varsayılan olarak `http://localhost:6666` adresinde çalışır.

## ⚙️ Yapılandırma

Yapılandırma için `.env` dosyasını kullanabilirsiniz. Eğer yoksa `.env.example` dosyasını kopyalayarak oluşturun:

```bash
cp .env.example .env
```

### `.env` Değişkenleri:

| Değişken | Açıklama | Varsayılan |
|----------|----------|------------|
| `PORT` | Dış erişim portu | `6666` |
| `WHISPER_PORT` | İç WhisperGo portu | `6666` |
| `WHISPER_HOST` | Bind adresi | `0.0.0.0` |
| `WHISPER_MODEL` | Kullanılacak model | `ggml-base.bin` |
| `WHISPER_LANGUAGE` | Varsayılan dil | `tr` |

### Environment değişikliklerini yaptıktan sonra servisi güncellemek için:

```bash
docker-compose up -d
```

### Mevcut Modeller:

| Model | Boyut | Not |
|-------|-------|-----|
| `ggml-tiny.bin` | 75 MB | ⚡ En Hızlı |
| `ggml-base.bin` | 142 MB | ✅ Dengeli (Önerilen) |
| `ggml-small.bin` | 466 MB | ⭐ İyi Doğruluk |
| `ggml-medium.bin` | 1.5 GB | 🎯 Yüksek Doğruluk |
| `ggml-large-v3-turbo.bin` | 1.5 GB | 🚀 Hızlı & Güçlü |

## 💾 CLI Mode (Bellek Optimize)

WhisperGo **CLI Mode** ile çalışır:

- Her istek için model yüklenir
- İşlem bitince bellek serbest kalır
- Avantaj: RAM sadece işlem sırasında kullanılır
- Dezavantaj: Her istek ~2-5 saniye ekstra (model yükleme)

```
┌─────────────────────────────────────────┐
│            HER İSTEKTE                  │
│                                         │
│  1. Model yüklenir (~2-5s)              │
│  2. Ses dosyası işlenir                 │
│  3. Sonuç döndürülür                    │
│  4. Bellek serbest kalır                │
└─────────────────────────────────────────┘
```

## 📡 API Kullanımı

### Ses Dosyası Gönderme (cURL)

```bash
curl http://localhost:6666/inference \
  -H "Content-Type: multipart/form-data" \
  -F file="@ses-dosyasi.wav" \
  -F language="tr" \
  -F response_format="json"
```

### Health Check

```bash
curl http://localhost:6666/health
```

## 📁 Klasör Yapısı

```text
WhisperGo-Dockerized/
├── Dockerfile          # Multi-Stage build tanımı (Builder & Runtime)
├── docker-compose.yml  # Servis orkestrasyonu
├── entrypoint.sh       # Konteyner başlangıç ve model kontrol scripti
├── cli-api.py          # CLI mode API handler
├── .env                # Yapılandırma (Git-ignored)
├── .env.example        # Örnek yapılandırma
└── models/             # İndirilen modeller (Kalıcı depolama)
```

## 🛠️ Teknik Notlar

*   **Multi-Stage Build:** İmaj boyutu optimize edilmiştir, gereksiz derleme araçları son imajda bulunmaz.
*   **Security Context:** Konteyner `whisper` adında non-root bir kullanıcı ile çalışır.
*   **CLI Mode:** Her istekte `whispergo-cli` çağrılır, model bellekte tutulmaz.
*   Servis başlatıldığında seçili model `models/` klasöründe yoksa otomatik olarak Hugging Face üzerinden indirilir.

## 👤 Hazırlayan

**Hazırlayan:** Osman Yavuz  
**📧 E-posta:** omnyvz.yazilim@gmail.com