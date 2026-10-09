#!/bin/sh
# Render portfolio.html to PDF with headless chromium.
# --no-pdf-header-footer: chromium otherwise stamps a URL and date on every page.
set -eu
cd "$(dirname "$0")"
python3 build.py
timeout 180 chromium --headless --disable-gpu --no-sandbox --no-pdf-header-footer \
  --virtual-time-budget=6000 \
  --print-to-pdf="$(pwd)/portfolio.pdf" "file://$(pwd)/portfolio.html" 2>&1 \
  | grep -viE 'mojo|DevTools|GPU|Fontconfig' || true
ls -la portfolio.pdf
