#!/bin/sh
# One-time inbound downloads. Runtime inference is offline (see ai.sh).
set -eu
cd "$(dirname "$0")/.."
python_bin="${YOURFITTINGROOM_PYTHON:-${WEARVIEW_PYTHON:-python3.12}}"
mkdir -p .runtime/weights/dwpose .runtime/hf-cache .runtime/mpl-cache
if [ ! -x .runtime/ai-venv/bin/python ]; then
  "$python_bin" -m venv .runtime/ai-venv
fi
if [ ! -f .runtime/fashn-src/pyproject.toml ]; then
  curl -fL --retry 3 https://codeload.github.com/fashn-AI/fashn-vton-1.5/tar.gz/7c0f10af3f91ad4048fe9729c470a13ef905d25a -o .runtime/fashn-source.tar.gz
  mkdir -p .runtime/fashn-src
  tar -xzf .runtime/fashn-source.tar.gz --strip-components=1 -C .runtime/fashn-src
fi
.runtime/ai-venv/bin/python -m pip install 'pip==26.2.1'
.runtime/ai-venv/bin/python -m pip install -r local_ai/requirements-lock.txt
# Upstream requests CUDA ONNX; CPU ONNX is intentional for the Mac adapter.
.runtime/ai-venv/bin/python -m pip install --no-deps --no-build-isolation .runtime/fashn-src
.runtime/ai-venv/bin/python local_ai/download_models.py
export HF_HOME="$PWD/.runtime/hf-cache" MPLCONFIGDIR="$PWD/.runtime/mpl-cache"
export HF_HUB_OFFLINE=0 TRANSFORMERS_OFFLINE=0 HF_HUB_DISABLE_TELEMETRY=1 HF_HUB_DISABLE_XET=1
.runtime/ai-venv/bin/python - <<'PY'
from pathlib import Path
from transformers import CLIPModel, CLIPProcessor
from fashn_human_parser import FashnHumanParser
destination = Path('.runtime/weights/clip')
if not (destination / 'model.safetensors').exists():
    revision = '3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268'
    # Existing safetensors conversion on the model repository; avoid pickle
    # loading or contacting a conversion service during setup.
    CLIPModel.from_pretrained('openai/clip-vit-base-patch32',revision='c237dc49a33fc61debc9276459120b7eac67e7ef',use_safetensors=True).save_pretrained(destination)
    CLIPProcessor.from_pretrained('openai/clip-vit-base-patch32',revision=revision).save_pretrained(destination)
FashnHumanParser(model_id=str(Path('.runtime/weights/parser')),device='cpu')
print('Local AI installed. Run ./scripts/ai.sh, then ./scripts/dev.sh in another terminal.')
PY
