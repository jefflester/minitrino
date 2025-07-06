#!/usr/bin/env bash
set -euo pipefail

cd /docs

pip install --no-cache-dir -r requirements.txt

rm -rf api

sphinx-apidoc -o api ../src/cli/minitrino -f -e --tocfile index
sed -i '1s/.*/API Reference/' api/index.rst
sphinx-build -b html . _build/html
