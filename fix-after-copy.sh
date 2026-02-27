#!/bin/bash
# Run this script on the DEPLOY machine after copying or when venv breaks
# WARNING: Must be run DIRECTLY on the deploy machine, NOT through mounted volume

set -e

echo "=== JTFNews Post-Copy Fix ==="
echo ""

# Architecture check - abort if running on wrong architecture
ARCH=$(uname -m)
if [[ "$ARCH" == "arm64" ]]; then
    echo "ERROR: This script is running on ARM64 (Apple Silicon)."
    echo "The deploy machine is Intel (x86_64)."
    echo ""
    echo "You CANNOT run this through the mounted volume!"
    echo "Run it DIRECTLY on the deploy machine (SSH or physical access)."
    exit 1
fi
echo "Architecture: $ARCH (correct for deploy machine)"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "Working directory: $SCRIPT_DIR"
echo ""

# Check Python version
echo "Checking Python..."
PYTHON_VERSION=$(python3 --version 2>&1)
echo "Found: $PYTHON_VERSION"

# Verify Python 3.9+
if [[ "$PYTHON_VERSION" == *"2.7"* ]] || [[ "$PYTHON_VERSION" == *"3.6"* ]] || [[ "$PYTHON_VERSION" == *"3.7"* ]] || [[ "$PYTHON_VERSION" == *"3.8"* ]]; then
    echo ""
    echo "ERROR: Python 3.9+ required. You have: $PYTHON_VERSION"
    echo "Download from: https://www.python.org/ftp/python/3.9.13/python-3.9.13-macosx10.9.pkg"
    exit 1
fi
echo ""

# 1. Fix virtual environment
echo "[1/3] Recreating virtual environment..."
# Clear macOS metadata that can prevent deletion after copying
find venv -name ".DS_Store" -delete 2>/dev/null || true
find venv -name "._*" -delete 2>/dev/null || true
xattr -cr venv 2>/dev/null || true
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "Virtual environment ready."
echo ""

# 2. Create data directories if missing
echo "[2/3] Ensuring data directories exist..."
mkdir -p data audio archive
echo "Directories ready."
echo ""

# 3. Verify docs folder exists (for GitHub Pages)
echo "[3/3] Checking docs folder..."
if [ -d "docs" ]; then
    echo "docs/ folder exists"
else
    echo "WARNING: docs/ folder missing - website content not present"
fi
echo ""

# Verify
echo "=== Verification ==="
source venv/bin/activate
echo "Python: $(python3 --version)"
echo "Pip packages: $(pip list 2>/dev/null | wc -l | tr -d ' ') installed"
echo ""

# Check .env
if [ -f ".env" ]; then
    echo ".env file: Found"
else
    echo ".env file: MISSING - copy from dev machine!"
fi

echo ""
echo "=== Done ==="
echo ""
echo "To start: ./start.sh"
echo "To start fresh (clear old stories): ./start.sh --fresh"
