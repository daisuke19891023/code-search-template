#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'USAGE'
Usage: ./setup_ripgrep_fd.sh

Installs ripgrep and fd (fd-find) on Ubuntu-based systems using apt.
Run with sudo or as root. The script will:
  * Update the apt package index.
  * Install ripgrep and fd-find if they are not already installed.
  * Create a symlink named "fd" pointing to "fdfind" when needed.
USAGE
}

if [[ "${1-}" == "-h" || "${1-}" == "--help" ]]; then
    usage
    exit 0
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

update_packages() {
    echo "Updating apt package index..."
    "${sudo_cmd[@]}" apt-get update
}

install_package() {
    local package=$1
    if dpkg -s "$package" >/dev/null 2>&1; then
        echo "$package is already installed."
        return
    fi

    echo "Installing $package..."
    "${sudo_cmd[@]}" apt-get install -y "$package"
}

create_fd_symlink() {
    local fd_path
    fd_path=$(command -v fd || true)
    if [[ -n "$fd_path" ]]; then
        echo "fd command already available at $fd_path"
        return
    fi

    local fdfind_path
    fdfind_path=$(command -v fdfind || true)
    if [[ -z "$fdfind_path" ]]; then
        echo "fdfind is not installed; cannot create fd symlink." >&2
        return
    fi

    local link_path=/usr/local/bin/fd
    echo "Creating symlink $link_path -> $fdfind_path"
    "${sudo_cmd[@]}" ln -sf "$fdfind_path" "$link_path"
}

main() {
    update_packages
    install_package ripgrep
    install_package fd-find
    create_fd_symlink
    echo "ripgrep and fd are ready to use."
}

main "$@"
