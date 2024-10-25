#!/usr/bin/env bash

function install() {
    # Find a compatible version of pip
    if command -v pip &>/dev/null && pip --version 2>&1 | grep -q -E "python.*3\.[8-9]|python.*3\.(1[0-1])"; then
        PIP=pip
    elif command -v pip3 &>/dev/null && pip3 --version 2>&1 | grep -q -E "python.*3\.[8-9]|python.*3\.(1[0-1])"; then
        PIP=pip3
    else
        echo "Minitrino requires Python 3.8+. Please install a compatible Python version and ensure Pip points to it."
        exit 1
    fi

    # Set verbose if "-v" is passed
    if [[ $1 == "-v" ]]; then
        set -ex
    else
        set -e
    fi

    # Get the directory of the script
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

    # Check for pyproject.toml dependencies
    "${PIP}" install -q --upgrade pip setuptools wheel

    echo "Installing Minitrino CLI and test modules..."
    "${PIP}" install -q --editable "${SCRIPT_DIR}/src/cli/"
    "${PIP}" install -q --editable "${SCRIPT_DIR}/src/test/"
}

time install "$1"

echo -e "\nInstallation complete! Start with the CLI by configuring it with 'minitrino config' \
(you can do this later). Alternatively, get started immediately with 'minitrino provision'.\n"

minitrino
echo -e "\n"
