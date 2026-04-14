#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Building InfraCanvas viewer..."
cd "$SCRIPT_DIR/viewer"

if [ ! -d "node_modules" ]; then
  echo "==> Installing dependencies..."
  npm install
fi

echo "==> Running Vite build (single-file HTML)..."
npm run build

echo "==> Copying viewer template to CLI package..."
cp dist/index.html "$SCRIPT_DIR/cli/infracanvas/export/viewer_template.html"

echo "==> Done! Template at cli/infracanvas/export/viewer_template.html"
