#!/bin/sh
# One-time inbound downloads. Runtime inference is offline (see ai.sh).
set -eu
cd "$(dirname "$0")/.."
python_bin="${YOURFITTINGROOM_PYTHON:-${WEARVIEW_PYTHON:-python3.12}}"
if [ "$(uname -s)" != Darwin ]; then
  echo 'This setup package currently supports macOS only. Other platforms need separate validation.' >&2
  exit 1
fi
if [ ! -x .runtime/ai-venv/bin/python ]; then
  if ! command -v "$python_bin" >/dev/null 2>&1; then
    echo 'Python 3.12 was not found. Install Python 3.12 from python.org, then reopen Set up.command.' >&2
    exit 1
  fi
  if ! "$python_bin" -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3,12) else 1)'; then
    echo 'Python 3.12 is required. Use YOURFITTINGROOM_PYTHON to select it if installed at a custom path.' >&2
    exit 1
  fi
fi
echo 'Setting up local AI. First setup downloads several GB; keep this window open. No photos are sent.'
mkdir -p .runtime/weights/dwpose .runtime/hf-cache .runtime/mpl-cache
if [ ! -x .runtime/ai-venv/bin/python ]; then
  "$python_bin" -m venv .runtime/ai-venv
fi
.runtime/ai-venv/bin/python local_ai/setup_tls.py
.runtime/ai-venv/bin/python local_ai/source_integrity.py
.runtime/ai-venv/bin/python -m pip --isolated --disable-pip-version-check install --only-binary=:all: --require-hashes --index-url https://pypi.org/simple -r local_ai/requirements-bootstrap-hashed.txt
.runtime/ai-venv/bin/python -m pip --isolated --disable-pip-version-check install --only-binary=:all: --require-hashes --index-url https://pypi.org/simple -r local_ai/requirements-mac-hashed.txt
# Upstream requests CUDA ONNX; CPU ONNX is intentional for the Mac adapter.
.runtime/ai-venv/bin/python -m pip --isolated --disable-pip-version-check install --no-deps --no-build-isolation .runtime/fashn-src
.runtime/ai-venv/bin/python local_ai/download_models.py
export HF_HOME="$PWD/.runtime/hf-cache" MPLCONFIGDIR="$PWD/.runtime/mpl-cache"
export HF_HUB_OFFLINE=0 TRANSFORMERS_OFFLINE=0 HF_HUB_DISABLE_TELEMETRY=1 HF_HUB_DISABLE_XET=1
.runtime/ai-venv/bin/python local_ai/finish_setup.py
echo 'Setup complete. Open Start AI.command, keep its Terminal open, then pair in the separately running web app.'
