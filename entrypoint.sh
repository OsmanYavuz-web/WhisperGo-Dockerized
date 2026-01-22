#!/bin/bash
set -e

# Default Settings
MODEL="${WHISPER_MODEL:-ggml-base.bin}"
LANG="${WHISPER_LANGUAGE:-tr}"
HOST="${WHISPER_HOST:-0.0.0.0}"
PORT="${WHISPER_PORT:-8080}"
MODEL_PATH="/app/models/${MODEL}"

# Model Download Logic
if [ ! -f "${MODEL_PATH}" ]; then
    echo "⬇️  Model indirilmesi gerekiyor: ${MODEL}"
    
    # Extract model type (e.g., ggml-base.bin -> base)
    MODEL_TYPE=$(echo "${MODEL}" | sed "s/ggml-//;s/\.bin//")
    
    echo "🔍 Model Tipi: ${MODEL_TYPE}"
    
    # Use the script from whisper.cpp repo structure
    # Note: We need to make sure this script exists in the runtime container
    if [ -f "/app/download-ggml-model.sh" ]; then
        bash /app/download-ggml-model.sh "${MODEL_TYPE}" /app/models
    else
        echo "❌ Hata: İndirme scripti bulunamadı!"
        exit 1
    fi
else
    echo "✅ Model mevcut: ${MODEL}"
fi

echo "🚀 WhisperGo-Dockerized Başlatılıyor..."
echo "----------------------------------------"
echo "🧠 Model: ${MODEL}"
echo "🗣️  Dil:   ${LANG}"
echo "🎧 Port:  ${PORT}"
echo "📝 Mode:  CLI (her istekte model yüklenir)"
echo "----------------------------------------"

# Run the CLI API (unbuffered for immediate log output)
exec python3 -u /app/cli-api.py

