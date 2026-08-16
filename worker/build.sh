#!/usr/bin/env bash
# Portable koboldcpp AI-Horde worker build for a real Linux host (x86_64/glibc).
# Run on any normal box/vps/CI with a C toolchain + 4GB RAM:
#   bash worker/build.sh            # build only
#   bash worker/build.sh --run      # build + launch worker (needs HF dl)
set -euo pipefail
cd "$(dirname "$0")"

ARCH="$(uname -m)"
case "$ARCH" in
  x86_64|amd64)  ;;
  aarch64|arm64) echo "[!] ARM CPU build OK but no CUDA; expect slow t/s" ;;
  *) echo "[!] untested arch $ARCH" ;;
esac

DEPS=(git make wget curl gcc g++ python3)
missing=0
for d in "${DEPS[@]}"; do command -v "$d" >/dev/null 2>&1 || { echo "MISSING: $d"; missing=1; }; done
if [ "$missing" = 1 ]; then echo "Install build deps first, e.g.:"
  echo "  Debian/Ubuntu: apt-get update && apt-get install -y build-essential git wget curl python3"
  exit 1
fi

[ -d koboldcpp ] || git clone https://github.com/LostRuins/koboldcpp.git
cd koboldcpp

# CPU + GPU (CUDA if nvcc present) build. Drop LLAMA_CUDA=1 if you lack an NVIDIA GPU.
if command -v nvcc >/dev/null 2>&1; then
  echo "[*] nvcc found -> compiling with CUDA"
  make LLAMA_CUDA=1 LLAMA_CUBLAS=1 -j"$(nproc)"
else
  echo "[*] no CUDA -> compiling CPU with OpenBLAS"
  make LLAMA_OPENBLAS=1 -j"$(nproc)"
fi

mkdir -p models
if [ ! -f models/model.gguf ]; then
  echo "[*] downloading Qwen1.5-0.5B-Chat Q4_K_M (~400MB)"
  wget -O models/model.gguf \
    "https://huggingface.co/Qwen/Qwen1.5-0.5B-Chat-GGUF/resolve/main/qwen1_5-0_5b-chat-q4_k_m.gguf"
fi
echo "[✓] build complete: $(pwd)"

if [ "${1:-}" = "--run" ]; then
  # <APIKEY> = your registered AI-Horde key (0000000000 = anonymous)
  python3 koboldcpp.py models/model.gguf --useblas \
    --hordeconfig "FractalMesh_Worker" "${HORDE_API_KEY:-0000000000}" "Qwen1.5-0.5B" 1 1
fi
