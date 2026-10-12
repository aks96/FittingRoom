#!/bin/sh
cd "$(dirname "$0")/.." || exit 1
if [ -x .runtime/bin/node ]; then
  export PATH="$PWD/.runtime/bin:$PATH"
fi
exec npm run dev
