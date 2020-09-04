#!/usr/bin/env bash 

function install() {

    if pip --version 2>&1 | grep -q "python3.[6-9]"; then
        PIP=pip
    elif pip3 --version 2>&1 | grep -q "python3.[6-9]"; then
        PIP=pip3
    else
        echo "Minipresto requires Python 3.6+. Please install a compatible Python version and ensure Pip points to it."
        exit 1
    fi

    if [[ $1 == "-v" ]]; then
        set -ex
        echo "Installing minipresto CLI..."
        "${PIP}" install --editable cli/
    else
        set -e
        echo "Installing minipresto CLI..."
        "${PIP}" install -q --editable cli/
    fi
}

time install $1

echo -e "\nInstallation complete! Start with the CLI by configuring it running 'minipresto config' \
(you can do this later). Alternatively, get started immediately with 'minipresto provision'.\n"

minipresto

echo -e "\n"