#!/bin/sh
# Distributed at the companion folder root; no shell commands from the website.
cd "$(dirname "$0")" || exit 1
./scripts/setup-ai.sh
setup_result=$?
printf '\nPress Return to close this setup window.\n'
read -r unused
exit "$setup_result"
