#!/usr/bin/env sh

set -eu

NO_VENV=0
for arg in "$@"; do
    if [ "$arg" = "--no-venv" ]; then
        NO_VENV=1
        break
    fi
done

find_python() {
    for py in python3 python /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
        if command -v "${py}" >/dev/null 2>&1; then
            version=$("${py}" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')
            echo "Detected Python version: ${version} (${py})"
            case "${version}" in
                3.8|3.9|3.1[0-9])
                    PYTHON="${py}"
                    return
                    ;;
            esac
        fi
    done
    echo "Error: Python 3.8+ is required but not found." >&2
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

handle_managed_python() {
    if [ "${NO_VENV}" -eq 1 ]; then
        echo "Skipping virtual environment setup due to --no-venv flag."
        return
    fi

    if [ -z "${VIRTUAL_ENV:-}" ]; then
        echo "Checking if pip install is blocked (PEP 668)..."
        if ! "${PYTHON}" -m pip install --dry-run --upgrade pip >/dev/null 2>&1; then
            echo "Detected a managed Python environment (PEP 668 or similar)."
            echo "Creating a virtual environment in ./venv..."
            "${PYTHON}" -m venv "${SCRIPT_DIR}/venv"
            echo "Re-running install.sh using the virtual environment..."
            . "${SCRIPT_DIR}/venv/bin/activate"
            exec "${SCRIPT_PATH}" "$@"
        fi
    fi
}

pip_install() {
    if [ -z "${VIRTUAL_ENV:-}" ] && [ "$(id -u)" -ne 0 ]; then
        pip_args="--user"
    else
        pip_args=""
    fi

    echo "Installing editable CLI and test modules from source..."
    "${PYTHON}" -m pip install ${pip_args} --disable-pip-version-check --upgrade pip setuptools wheel || {
        echo "Error: Failed to upgrade pip, setuptools, or wheel"
        exit 1
    }

    "${PYTHON}" -m pip install ${pip_args} --editable "${SCRIPT_DIR}/src/cli/" --use-pep517 || {
        echo "Error: Failed to install CLI module"
        exit 1
    }

    "${PYTHON}" -m pip install ${pip_args} --editable "${SCRIPT_DIR}/src/test/" --use-pep517 || {
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

install() {
    [ "${1:-}" = "-v" ] && set -eux

    if command -v realpath >/dev/null 2>&1; then
        SCRIPT_PATH=$(realpath "$0")
    else
        SCRIPT_PATH=$(python -c "import os; print(os.path.realpath('$0'))")
    fi
    SCRIPT_DIR=$(dirname "${SCRIPT_PATH}")

    find_python
    check_wsl
    check_pip
    check_docker
    handle_managed_python "$@"
    pip_install
    handle_path_and_symlink
    check_install
}

time install "$@"

echo "
Installation complete! Start with the CLI by configuring it with 'minitrino config'.
Alternatively, get started immediately with 'minitrino provision'.
"

minitrino
