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

REPO_ROOT=$(dirname "$(dirname "$(dirname "${SCRIPT_PATH}")")")

VERBOSE=0
FORCE=0

show_help() {
    echo "Usage: ./install/src/install.sh [options]"
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
    # Dynamically find all python3.1* binaries in PATH (deduped)
    dynamic_candidates=()
    while IFS= read -r line; do
        if [[ -n "$line" ]]; then
            dynamic_candidates+=("$line")
        fi
    done < <(command -v -a python3.1* 2>/dev/null | awk '!seen[$0]++')

    # Find all python3.1* in common Homebrew and local bin dirs, even if not in PATH
    homebrew_candidates=()
    while IFS= read -r line; do
        [ -n "$line" ] && homebrew_candidates+=("$line")
    done < <(ls /opt/homebrew/bin/python3.1* 2>/dev/null || true)
    
    usr_local_candidates=()
    while IFS= read -r line; do
        [ -n "$line" ] && usr_local_candidates+=("$line")
    done < <(ls /usr/local/bin/python3.1* 2>/dev/null || true)

    # Add generic candidates for robustness
    static_candidates=(
        python3
        python
    )

    candidates=()
    
    # Add dynamic candidates if any
    if [[ ${#dynamic_candidates[@]} -gt 0 ]]; then
        candidates+=("${dynamic_candidates[@]}")
    fi
    
    # Add homebrew candidates if any
    if [[ ${#homebrew_candidates[@]} -gt 0 ]]; then
        candidates+=("${homebrew_candidates[@]}")
    fi
    
    # Add usr/local candidates if any
    if [[ ${#usr_local_candidates[@]} -gt 0 ]]; then
        candidates+=("${usr_local_candidates[@]}")
    fi
    
    # Add static candidates
    candidates+=("${static_candidates[@]}")

    best_py=""
    best_major=0
    best_minor=0
    for py in "${candidates[@]}"; do
        echo "Checking candidate: $py"
        if ! [ -x "$py" ] && ! command -v "$py" >/dev/null 2>&1; then
            continue
        fi
        version=$(
            "$py" -c \
            'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")' \
            2>/dev/null || echo "0.0"
        )
        echo "Detected Python version: ${version} (${py})"
        major=$(echo "${version}" | cut -d. -f1)
        minor=$(echo "${version}" | cut -d. -f2)
        if ! [[ "${major}" =~ ^[0-9]+$ ]] || ! [[ "${minor}" =~ ^[0-9]+$ ]]; then
            continue
        fi
        if [ "${major}" -lt 3 ] || { [ "${major}" -eq 3 ] && [ "${minor}" -lt 10 ]; }; then
            continue
        fi
        if [ "${major}" -gt "${best_major}" ] || \
           { [ "${major}" -eq "${best_major}" ] && \
             [ "${minor}" -gt "${best_minor}" ]; }; then
            best_py="${py}"
            best_major="${major}"
            best_minor="${minor}"
        fi
    done
    if [ -n "$best_py" ]; then
        PYTHON="$best_py"
        echo "Using Python interpreter: $PYTHON (${best_major}.${best_minor})"
        return
    fi
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
    local venv_dir="${REPO_ROOT}/venv"
    if [ ! -d "${venv_dir}" ]; then
        echo "Creating virtual environment in ${REPO_ROOT}/venv..."
        "${PYTHON}" -m venv "${venv_dir}"
    else
        echo "Using existing virtual environment in ${REPO_ROOT}/venv"
    fi

    # shellcheck source=/dev/null
    . "${venv_dir}/bin/activate"
    echo "Switching to venv python..."
    PYTHON="$(which python)"
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

    "${PYTHON}" -m pip install -e "${REPO_ROOT}/.[dev,docs]" --use-pep517 || {
        echo "Error: Failed to install CLI module with [dev,docs] extras"
        exit 1
    }

    "${PYTHON}" -m pip install -e "${REPO_ROOT}/src/tests/" --use-pep517 || {
        echo "Error: Failed to install test module"
        exit 1
    }
}

handle_path_and_symlink() {
    # Always symlink to the venv's minitrino binary to avoid circular symlinks
    local venv_bin_dir="${REPO_ROOT}/venv/bin"
    local minitrino_venv_bin="${venv_bin_dir}/minitrino"
    local target_bin_dir="${HOME}/.local/bin"

    mkdir -p "${target_bin_dir}"

    if ln -sf "${minitrino_venv_bin}" "${target_bin_dir}/minitrino"; then
        echo "Symlinked minitrino to: ${target_bin_dir}/minitrino (-> ${minitrino_venv_bin})"

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
    local test_runner_src="${REPO_ROOT}/src/tests/lib/runner.py"
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

print_activation_help() {
    echo -e "\033[1;33mFailed to run $1. You may need to activate the virtual environment first:"
    echo "    source ./venv/bin/activate"
    echo -e "Or ensure ~/.local/bin is in your PATH.\033[0m"
}

echo "
Installation complete! Start with the CLI by configuring it with 'minitrino config'.
Alternatively, get started immediately with 'minitrino provision'.
"

if command -v minitrino-lib-test >/dev/null 2>&1; then
    echo -e "Running minitrino-lib-test...\n"
    minitrino-lib-test --help || print_activation_help "minitrino-lib-test"
fi

echo ""

if command -v minitrino >/dev/null 2>&1; then
    echo -e "Running minitrino...\n"
    minitrino || print_activation_help "minitrino"
else
    echo "You may now run minitrino by sourcing your venv or using the symlink:"
    echo "  source ./venv/bin/activate && minitrino"
    echo "  OR"
    echo "  ~/.local/bin/minitrino"
fi
