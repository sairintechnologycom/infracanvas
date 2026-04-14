#!/bin/bash
set -e

OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)
VERSION="0.1.0"

echo "Installing InfraCanvas v${VERSION}..."

# Prefer pip if Python 3.12+ available
if command -v python3 &>/dev/null && python3 -c "import sys; assert sys.version_info >= (3,12)" 2>/dev/null; then
    pip3 install "infracanvas==${VERSION}"
    echo "Installed via pip. Run: infracanvas --help"
    exit 0
fi

# Fall back to binary
BASE_URL="https://github.com/infracanvas/infracanvas/releases/download/v${VERSION}"
if [[ "$OS" == "darwin" ]]; then
    BINARY="infracanvas-macos-arm64"
elif [[ "$OS" == "linux" ]]; then
    BINARY="infracanvas-linux-amd64"
else
    echo "Unsupported OS: $OS. Install manually: pip install infracanvas"
    exit 1
fi

curl -sSL "${BASE_URL}/${BINARY}" -o /usr/local/bin/infracanvas
chmod +x /usr/local/bin/infracanvas
echo "Installed to /usr/local/bin/infracanvas"
