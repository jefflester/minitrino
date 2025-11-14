#!/usr/bin/env bash
set -euo pipefail

cd /docs

# Dependencies are already installed in Dockerfile via: pip install /tmp/minitrino[docs]

rm -rf api

sphinx-apidoc -o api ../src/cli/minitrino -f -e --tocfile index

# Fix the title and underline in generated api/index.rst
sed -i '1s/.*/API Reference/' api/index.rst
sed -i '2s/.*/=============/' api/index.rst

sphinx-build -b html . _build/html
