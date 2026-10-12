#!/bin/sh
cd "$(dirname "$0")/.." || exit 1
if [ ! -x .runtime/ai-venv/bin/python ] || [ ! -f .runtime/weights/model.safetensors ]; then
  echo 'Local model is missing. Run ./scripts/setup-ai.sh with Python 3.12 first.' >&2
  exit 1
fi
export HF_HOME="$PWD/.runtime/hf-cache"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1
export MPLCONFIGDIR="$PWD/.runtime/mpl-cache"
export PYTHONPATH="$PWD/.runtime/fashn-src/src"
.runtime/ai-venv/bin/python -c 'from local_ai.download_models import verify; verify()' || exit 1
exec .runtime/ai-venv/bin/python -m uvicorn local_ai.server:app --host 127.0.0.1 --port 8765 --no-access-log
