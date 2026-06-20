#!/usr/bin/env bash
set -e

echo "=== Installing Python dependencies ==="
pip install -r requirements.txt

echo "=== Checking Node.js availability ==="
if command -v node &> /dev/null; then
    echo "Node.js already available: $(node --version)"
else
    echo "Node.js not found, installing via apt..."
    apt-get update -qq && apt-get install -y -qq nodejs npm || true
    if command -v node &> /dev/null; then
        echo "Node.js installed: $(node --version)"
    else
        echo "WARNING: Could not install Node.js via apt"
    fi
fi

echo "=== Build complete ==="
