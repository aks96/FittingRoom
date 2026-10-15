#!/bin/sh
# Distributed at the companion folder root.
cd "$(dirname "$0")" || exit 1
./scripts/ai.sh
start_result=$?
printf '\nThe companion stopped. Press Return to close this window.\n'
read -r unused
exit "$start_result"
