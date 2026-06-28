#!/usr/bin/env bash
# Auto-format all frontend files and fix lint issues
set -e

FRONTEND_DIR="$(cd "$(dirname "$0")/../frontend" && pwd)"

echo "==> Formatting frontend files"
cd "$FRONTEND_DIR"

echo ""
echo "--- Prettier (auto-format) ---"
npx prettier --write .

echo ""
echo "--- ESLint (auto-fix) ---"
npx eslint --fix script.js

echo ""
echo "Frontend formatting complete."
