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

# Refuse to leave a PDF older than the page it came from.
#
# chromium exits 0 on some failures, and the `|| true` above exists to swallow
# its unrelated chatter -- which means a render that produced nothing at all
# looks exactly like one that worked. The file's own timestamp is the only
# thing here that knows the difference.
#
# t/test_portfolio.py asserts the same property, but only when someone runs
# the suite. The person who ran render.sh and saw no error is the one who needs
# telling, at the moment it happened.
if [ ! -f portfolio.pdf ]; then
  echo "render.sh: chromium wrote no portfolio.pdf" >&2
  exit 1
fi
# shortcut: -ot is not in POSIX test, it is a widely implemented extension.
# dash and bash both have it, which covers every /bin/sh this will meet here.
# Upgrade path if that stops being true: compare two `stat -c %Y` readings.
if [ portfolio.pdf -ot portfolio.html ]; then
  echo "render.sh: portfolio.pdf is older than portfolio.html, so chromium" >&2
  echo "           did not rewrite it -- the PDF you have is the previous one" >&2
  exit 1
fi
ls -la portfolio.pdf
