#!/usr/bin/env bash
# Run all frontend code quality checks
set -e

FRONTEND_DIR="$(cd "$(dirname "$0")/../frontend" && pwd)"

echo "==> Frontend quality checks"
cd "$FRONTEND_DIR"

echo ""
echo "--- Prettier (format check) ---"
npx prettier --check .

echo ""
echo "--- ESLint (lint check) ---"
npx eslint script.js

echo ""
echo "All frontend checks passed."
