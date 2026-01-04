# ==========================================
# Stage 1: Builder
# ==========================================
FROM ubuntu:22.04 AS builder

WORKDIR /build

# Build dependencies
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y \
    build-essential \
    cmake \
    git \
    && rm -rf /var/lib/apt/lists/*

# Clone and Build whisper.cpp
# Using specific commit or tag is often safer, but sticking to master for latest features as per original
RUN git clone --depth 1 https://github.com/ggml-org/whisper.cpp.git . && \
    cmake -B build -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF && \
    cmake --build build --config Release -j$(nproc)

# ==========================================
# Stage 2: Runtime
# ==========================================
FROM ubuntu:22.04

WORKDIR /app

# Runtime dependencies only
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y \
    curl \
    ffmpeg \
    bash \
    python3 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r whisper && useradd -r -g whisper whisper

# Copy artifacts from builder
COPY --from=builder /build/build/bin/whisper-server /app/bin/whispergo
COPY --from=builder /build/build/bin/whisper-cli /app/bin/whispergo-cli
COPY --from=builder /build/models/download-ggml-model.sh /app/download-ggml-model.sh
COPY entrypoint.sh /app/entrypoint.sh
COPY cli-api.py /app/cli-api.py

# Set Permissions
RUN chmod +x /app/entrypoint.sh /app/download-ggml-model.sh /app/bin/whispergo /app/bin/whispergo-cli && \
    mkdir -p /app/models && \
    chown -R whisper:whisper /app

# Switch to non-root user
USER whisper

# Environment Defaults
ENV PATH="/app/bin:${PATH}"
EXPOSE 6666

ENTRYPOINT ["/app/entrypoint.sh"]
