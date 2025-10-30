#!/bin/zsh

# Simple wrapper to run all extractors with your environment
# Usage: scripts/run_all_extractors.sh --folder_key october_2025 --recursive

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
REPO_DIR=$(cd -- "$SCRIPT_DIR/.." && pwd)

cd "$REPO_DIR"

if [ -f .venv/bin/activate ]; then
  source .venv/bin/activate
fi

# Load .env if present
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

python run_all_extractors.py "$@"


