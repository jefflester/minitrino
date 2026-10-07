#!/usr/bin/env bash
# Read the Docs pre_build hook. RTD runs build.jobs commands without a shell,
# so quoting/spaces in inline commands break; keep the logic in a script.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../.."

sphinx-apidoc -o docs/api src/minitrino -f -e --tocfile index

# Fix the title and underline in generated api/index.rst
sed -i '1s/.*/API Reference/' docs/api/index.rst
sed -i '2s/.*/=============/' docs/api/index.rst
