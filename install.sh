#!/usr/bin/env bash

function install() {
    if pip --version 2>&1 | grep -q -e "python.*3.[8-9]" -e "python.*3.[1][0-1]"; then
        PIP=pip
    elif pip3 --version 2>&1 | grep -q -e "python.*3.[8-9]" -e "python.*3.[1][0-1]"; then
        PIP=pip3
    else
        echo "Minitrino requires Python 3.8+. Please install a compatible Python version and ensure Pip points to it."
        exit 1
    fi

    if [[ $1 == "-v" ]]; then
        set -ex
    else
        set -e
    fi

    echo "Installing Minitrino CLI and test modules..."
    "${PIP}" install -q --editable "${BASH_SOURCE%/*}"/src/cli/
    "${PIP}" install -q --editable "${BASH_SOURCE%/*}"/src/test/
}

time install "$1"

echo -e "\nInstallation complete! Start with the CLI by configuring it running 'minitrino config' \
(you can do this later). Alternatively, get started immediately with 'minitrino provision'.\n"

minitrino
echo -e "\n"
