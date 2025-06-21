#!/usr/bin/env bash

# Deactivate any active virtual environment
if [ -n "${VIRTUAL_ENV:-}" ]; then
    echo "Deactivating currently active virtual environment: ${VIRTUAL_ENV}"
    if declare -f deactivate >/dev/null 2>&1; then
        deactivate || true
    else
        echo "(Skipping deactivate — not defined in this shell)"
    fi
    unset VIRTUAL_ENV
fi

set -eu

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
    local venv_dir="${SCRIPT_DIR}/venv"
    if [ ! -d "${venv_dir}" ]; then
        echo "Creating virtual environment in ./venv..."
        "${PYTHON}" -m venv "${venv_dir}"
    else
        echo "Using existing virtual environment in ./venv"
    fi

    # shellcheck source=/dev/null
    . "${venv_dir}/bin/activate"
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

    "${PYTHON}" -m pip install -e "${SCRIPT_DIR}/src/tests/" --use-pep517 || {
        echo "Error: Failed to install test module"
        exit 1
    }
}

handle_path_and_symlink() {
    MINITRINO_BIN=$(command -v minitrino 2>/dev/null || "${PYTHON}" -c "import os; print(os.path.realpath('${SCRIPT_DIR}/venv/bin/minitrino'))")
    local target_bin_dir="${HOME}/.local/bin"

    mkdir -p "${target_bin_dir}"

    if ln -sf "${MINITRINO_BIN}" "${target_bin_dir}/minitrino"; then
        echo "Symlinked minitrino to: ${target_bin_dir}/minitrino"

        case ":${PATH}:" in
            *":${target_bin_dir}:"*) ;; # already in PATH
            *)
                export PATH="${target_bin_dir}:${PATH}"
                echo "Note: ${target_bin_dir} was added to your PATH for this session."

                local user_shell
                user_shell=$(basename "${SHELL:-$0}")
                case "${user_shell}" in
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
        echo "Error: Failed to create symlink to ${target_bin_dir}"
        echo "You can run minitrino directly from:"
        echo "  ${MINITRINO_BIN}"
        return 1
    fi
}

symlink_test_runner() {
    local test_runner_src="${SCRIPT_DIR}/src/tests/lib/runner.py"
    local target_bin_dir="${HOME}/.local/bin"
    local target_link="${target_bin_dir}/minitrino-lib-test"

    mkdir -p "${target_bin_dir}"

    chmod +x "${test_runner_src}"
    if ln -sf "${test_runner_src}" "${target_link}"; then
        echo "Symlinked test runner to: ${target_link}"
    else
        echo "Error: Failed to create symlink for test runner"
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
    symlink_test_runner
    check_install
}

perform_install "$@"

echo "
Installation complete! Start with the CLI by configuring it with 'minitrino config'.
Alternatively, get started immediately with 'minitrino provision'.
"

if command -v minitrino-lib-test >/dev/null 2>&1; then
    echo -e "Running minitrino-lib-test...\n"
    minitrino-lib-test --help
fi

echo ""

if command -v minitrino >/dev/null 2>&1; then
    echo -e "Running minitrino...\n"
    minitrino
else
    echo "You may now run minitrino by sourcing your venv or using the symlink:"
    echo "  source ./venv/bin/activate && minitrino"
    echo "  OR"
    echo "  ~/.local/bin/minitrino"
fi
