#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
"$PWD/.venv/bin/python" -m pip install -r requirements.txt
"$PWD/.venv/bin/pyinstaller" \
  --noconfirm \
  --clean \
  --onefile \
  --windowed \
  --name "SGD-Cargos-Downloader" \
  --paths "src" \
  "src/cargos_downloader/main.py"
