#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/src"
"$PWD/.venv/bin/python" -m cargos_downloader.main
