#!/usr/bin/env bash
# VOID RECON - Setup Script
# Installs dependencies and registers 'void-recon' as a global command.

set -e

TOOL_NAME="void-recon"
TOOL_FILE="void_recon.py"
INSTALL_DIR="/usr/local/bin"


if [ -d "/data/data/com.termux" ]; then
    INSTALL_DIR="$PREFIX/bin"
fi

RED='\033[0;31m'
GRN='\033[0;32m'
YLW='\033[0;33m'
CYN='\033[0;36m'
RST='\033[0m'

info()  { echo -e "  ${CYN}[*]${RST} $1"; }
ok()    { echo -e "  ${GRN}[+]${RST} $1"; }
warn()  { echo -e "  ${YLW}[!]${RST} $1"; }
err()   { echo -e "  ${RED}[-]${RST} $1"; exit 1; }

echo ""
echo -e "  ${CYN}VOID RECON - Setup${RST}"
echo "  ──────────────────────────────────────"


if ! command -v python3 &>/dev/null; then
    err "python3 not found. Install it first."
fi
PYTHON=$(command -v python3)
info "Python : $PYTHON ($(python3 --version 2>&1))"


if ! command -v pip3 &>/dev/null && ! python3 -m pip --version &>/dev/null 2>&1; then
    warn "pip3 not found. Attempting to install..."
    if command -v apt &>/dev/null; then
        apt install -y python3-pip
    elif command -v pkg &>/dev/null; then
        pkg install -y python3-pip
    else
        err "Cannot install pip. Install manually and re-run."
    fi
fi
PIP="python3 -m pip"
info "pip    : OK"


info "Installing required packages..."
$PIP install --quiet --upgrade requests colorama urllib3

ok "Packages installed: requests, colorama, urllib3"


SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOL_PATH="$SCRIPT_DIR/$TOOL_FILE"

if [ ! -f "$TOOL_PATH" ]; then
    err "$TOOL_FILE not found in $SCRIPT_DIR"
fi


info "Installing to $INSTALL_DIR/$TOOL_NAME ..."


cp "$TOOL_PATH" "$INSTALL_DIR/$TOOL_NAME"
chmod +x "$INSTALL_DIR/$TOOL_NAME"


sed -i '1s|^.*|#!/usr/bin/env python3|' "$INSTALL_DIR/$TOOL_NAME"

ok "Installed: $INSTALL_DIR/$TOOL_NAME"


if command -v "$TOOL_NAME" &>/dev/null; then
    ok "Command registered: '$TOOL_NAME' is now available globally."
else
    warn "'$TOOL_NAME' not in PATH. Add $INSTALL_DIR to your PATH:"
    echo ""
    echo "    export PATH=\"\$PATH:$INSTALL_DIR\""
    echo ""
    echo "  Add this line to ~/.bashrc or ~/.zshrc and run: source ~/.bashrc"
fi

echo ""
echo -e "  ${GRN}Setup complete.${RST}"
echo ""
echo -e "  Usage:  ${CYN}void-recon -m bypass -u https://target.com/admin${RST}"
echo -e "  Help:   ${CYN}void-recon --help${RST}"
echo ""
