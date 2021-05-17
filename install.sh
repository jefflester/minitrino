#!/usr/bin/env bash

function install() {
    if pip --version 2>&1 | grep -q -e "python3.[6-9]" -e "python 3.[6-9]"; then
        PIP=pip
    elif pip3 --version 2>&1 | grep -q -e "python3.[6-9]" -e "python 3.[6-9]"; then
        PIP=pip3
    else
        echo "Minitrino requires Python 3.6+. Please install a compatible Python version and ensure Pip points to it."
        exit 1
    fi

    if [[ $1 == "-v" ]]; then
        set -ex
        echo "Installing minitrino CLI..."
        "${PIP}" install --editable "${BASH_SOURCE%/*}"/cli/
    else
        set -e
        echo "Installing minitrino CLI..."
        "${PIP}" install -q --editable "${BASH_SOURCE%/*}"/cli/
    fi
}

time install $1

echo -e "\nInstallation complete! Start with the CLI by configuring it running 'minitrino config' \
(you can do this later). Alternatively, get started immediately with 'minitrino provision'.\n"

minitrino

echo -e "\n"