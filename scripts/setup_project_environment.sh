#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'USAGE'
Usage: ./setup_project_environment.sh [--env <path>]

Installs uv when missing, creates a virtual environment, and installs the project
with its development dependencies. Designed for Ubuntu-based systems.

Options:
  --env <path>  Path to the virtual environment directory (default: .venv in the
                project root).
  -h, --help    Show this help message and exit.
USAGE
}

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(cd "${SCRIPT_DIR}/.." && pwd)
ENV_DIR="${PROJECT_ROOT}/.venv"

if [[ $# -gt 0 ]]; then
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --env)
                if [[ $# -lt 2 ]]; then
                    echo "Missing value for --env option." >&2
                    exit 1
                fi
                ENV_DIR=$(realpath "$2")
                shift 2
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                echo "Unknown option: $1" >&2
                usage >&2
                exit 1
                ;;
        esac
    done
fi

if ! command -v apt-get >/dev/null 2>&1; then
    echo "This setup script currently supports Ubuntu-based systems with apt-get." >&2
    exit 1
fi

if [[ $(id -u) -eq 0 ]]; then
    sudo_cmd=()
else
    if ! command -v sudo >/dev/null 2>&1; then
        echo "Please run this script as root or install sudo." >&2
        exit 1
    fi
    sudo_cmd=(sudo)
fi

apt_updated=false
update_apt_once() {
    if [[ ${apt_updated} == false ]]; then
        echo "Updating apt package index..."
        "${sudo_cmd[@]}" apt-get update
        apt_updated=true
    fi
}

ensure_package() {
    local package=$1
    if dpkg -s "$package" >/dev/null 2>&1; then
        return
    fi
    update_apt_once
    echo "Installing $package..."
    "${sudo_cmd[@]}" apt-get install -y "$package"
}

ensure_curl() {
    if command -v curl >/dev/null 2>&1; then
        return
    fi
    echo "curl is required to install uv."
    ensure_package curl
}

install_uv_if_needed() {
    if command -v uv >/dev/null 2>&1; then
        return
    fi

    ensure_curl
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh

    export PATH="${HOME}/.local/bin:${PATH}"
    if ! command -v uv >/dev/null 2>&1; then
        echo "uv installation did not succeed. Please ensure ~/.local/bin is on your PATH." >&2
        exit 1
    fi
}

create_virtualenv() {
    if [[ -d "$ENV_DIR" ]]; then
        echo "Virtual environment already exists at $ENV_DIR"
    else
        echo "Creating virtual environment at $ENV_DIR"
        (cd "$PROJECT_ROOT" && UV_PROJECT_ENVIRONMENT="$ENV_DIR" uv venv)
    fi
}

sync_project() {
    echo "Syncing project dependencies into $ENV_DIR"
    (cd "$PROJECT_ROOT" && UV_PROJECT_ENVIRONMENT="$ENV_DIR" uv sync --frozen --extra dev)
}

main() {
    install_uv_if_needed
    create_virtualenv
    sync_project
    cat <<SUMMARY

Setup complete.
To activate the environment, run:
  source "$ENV_DIR/bin/activate"
SUMMARY
}

main
