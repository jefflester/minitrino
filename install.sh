#!/usr/bin/env bash

# Deactivate any active virtual environment
if [ -n "${VIRTUAL_ENV:-}" ]; then
    echo "Deactivating currently active virtual environment: $VIRTUAL_ENV"
    if declare -f deactivate >/dev/null 2>&1; then
        deactivate || true
    else
        echo "(Skipping deactivate — not defined in this shell)"
    fi
    unset VIRTUAL_ENV
fi

set -eu

# Determine SCRIPT_PATH and SCRIPT_DIR early for use in all functions
if command -v realpath >/dev/null 2>&1; then
    SCRIPT_PATH=$(realpath "$0")
else
    SCRIPT_PATH=$(python -c "import os; print(os.path.realpath('$0'))")
fi
SCRIPT_DIR=$(dirname "${SCRIPT_PATH}")

VERBOSE=0
FORCE=0

show_help() {
    echo "Usage: ./install.sh [options]"
    echo ""
    echo "Options:"
    echo "  -v            Enable verbose output"
    echo "  -h, --help    Show this help message"
    exit 0
}

for arg in "$@"; do
    case "$arg" in
        --force)
            FORCE=1
            ;;
        -h|--help)
            show_help
            ;;
        -v)
            VERBOSE=1
            ;;
    esac
done

find_python() {
    for py in python3 python /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
        if command -v "${py}" >/dev/null 2>&1; then
            version=$("${py}" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')
            echo "Detected Python version: ${version} (${py})"
            major=$(echo "${version}" | cut -d. -f1)
            minor=$(echo "${version}" | cut -d. -f2)
            if [ "${major}" -eq 3 ] && [ "${minor}" -ge 10 ]; then
                PYTHON="${py}"
                return
            fi
        fi
    done
    echo "Error: Python 3.10+ is required but not found." >&2
    exit 1
}

check_wsl() {
    if [ "$(uname -s)" = "Linux" ] && grep -qEi "(Microsoft|WSL)" /proc/version 2>/dev/null; then
        echo "Note: You're running inside WSL. Make sure Docker Desktop is installed and WSL integration is enabled."
    fi
}

check_pip() {
    if ! "${PYTHON}" -m pip --version >/dev/null 2>&1; then
        echo "Error: Pip is not available for ${PYTHON}. Please install pip."
        exit 1
    fi
}

check_docker() {
    if ! command -v docker >/dev/null 2>&1; then
        echo "Error: Docker is required but not installed or not in your PATH."
        exit 1
    fi
}

handle_venv() {
    VENV_DIR="${SCRIPT_DIR}/venv"
    if [ ! -d "${VENV_DIR}" ]; then
        echo "Creating virtual environment in ./venv..."
        "${PYTHON}" -m venv "${VENV_DIR}"
    else
        echo "Using existing virtual environment in ./venv"
    fi

    # shellcheck source=/dev/null
    . "${VENV_DIR}/bin/activate"
}

pip_install() {
    echo "Installing editable CLI and test modules from source..."
    if [ "${FORCE}" -eq 1 ]; then
        echo "Forcing reinstall of CLI and test modules..."
        "${PYTHON}" -m pip uninstall -y minitrino || true
    fi
    "${PYTHON}" -m pip install --disable-pip-version-check --upgrade pip setuptools wheel black || {
        echo "Error: Failed to upgrade pip, setuptools, wheel, or black"
        exit 1
    }

    "${PYTHON}" -m pip install -e "${SCRIPT_DIR}/.[dev]" --use-pep517 || {
        echo "Error: Failed to install CLI module"
        exit 1
    }

    "${PYTHON}" -m pip install -e "${SCRIPT_DIR}/src/test/" --use-pep517 || {
        echo "Error: Failed to install test module"
        exit 1
    }
}

handle_path_and_symlink() {
    MINITRINO_BIN=$(command -v minitrino 2>/dev/null || "${PYTHON}" -c "import os; print(os.path.realpath('${SCRIPT_DIR}/venv/bin/minitrino'))")
    TARGET_BIN_DIR="${HOME}/.local/bin"

    mkdir -p "${TARGET_BIN_DIR}"

    if ln -sf "${MINITRINO_BIN}" "${TARGET_BIN_DIR}/minitrino"; then
        echo "Symlinked minitrino to: ${TARGET_BIN_DIR}/minitrino"

        case ":${PATH}:" in
            *":${TARGET_BIN_DIR}:"*) ;; # already in PATH
            *)
                export PATH="${TARGET_BIN_DIR}:${PATH}"
                echo "Note: ${TARGET_BIN_DIR} was added to your PATH for this session."

                USER_SHELL=$(basename "${SHELL:-$0}")
                case "${USER_SHELL}" in
                    bash)
                        echo "To make it permanent, add this line to one of the following (depending on your setup):"
                        echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
                        echo "  ~/.bash_profile  (macOS default login shell)"
                        echo "  ~/.bashrc        (Linux interactive shells)"
                        echo "  ~/.profile       (fallback on some systems)"
                        ;;
                    zsh)
                        echo "To make it permanent, add this to your ~/.zprofile or ~/.zshrc:"
                        echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
                        ;;
                    *)
                        echo "To make it permanent, add this to your shell config (e.g., ~/.profile):"
                        echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
                        ;;
                esac
                ;;
        esac
    else
        echo "Error: Failed to create symlink to ${TARGET_BIN_DIR}"
        echo "You can run minitrino directly from:"
        echo "  ${MINITRINO_BIN}"
        return 1
    fi
}

check_install() {
    hash -r 2>/dev/null || true
    if ! command -v minitrino >/dev/null 2>&1; then
        echo "Warning: 'minitrino' is installed but not found in your shell."
        echo "Try running this instead:"
        echo "  ${MINITRINO_BIN}"
    else
        echo "'minitrino' is now available in your PATH (via ~/.local/bin)."
    fi
}

perform_install() {
    if [ "${VERBOSE}" -eq 1 ]; then
        set -x
    fi

    find_python
    check_wsl
    check_pip
    check_docker
    handle_venv
    pip_install
    handle_path_and_symlink
    check_install
}

perform_install "$@"

echo "
Installation complete! Start with the CLI by configuring it with 'minitrino config'.
Alternatively, get started immediately with 'minitrino provision'.
"

if command -v minitrino >/dev/null 2>&1; then
    echo "Running minitrino..."
    minitrino
else
    echo "You may now run minitrino by sourcing your venv or using the symlink:"
    echo "  source ./venv/bin/activate && minitrino"
    echo "  OR"
    echo "  ~/.local/bin/minitrino"
fi
