#!/bin/bash
# Run this script after copying JTFNews folder to a new machine

set -e

echo "=== JTFNews Post-Copy Fix ==="
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "Working directory: $SCRIPT_DIR"
echo ""

# 1. Fix virtual environment
echo "[1/2] Recreating virtual environment..."
# Clear macOS metadata that can prevent deletion after copying
find venv -name ".DS_Store" -delete 2>/dev/null || true
find venv -name "._*" -delete 2>/dev/null || true
xattr -cr venv 2>/dev/null || true
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
echo "Virtual environment ready."
echo ""

# 2. Fix gh-pages worktree
echo "[2/2] Recreating gh-pages worktree..."
# Clear macOS metadata that can prevent deletion after copying
find gh-pages-dist -name ".DS_Store" -delete 2>/dev/null || true
xattr -cr gh-pages-dist 2>/dev/null || true
rm -rf gh-pages-dist
rm -rf .git/worktrees/gh-pages-dist 2>/dev/null || true
git fetch origin gh-pages
git worktree add gh-pages-dist gh-pages
echo "Worktree ready."
echo ""

# Verify
echo "=== Verification ==="
echo "Python: $(which python)"
echo "Pip packages: $(pip list | wc -l) installed"
echo "gh-pages-dist: $(ls gh-pages-dist | wc -l) files"
echo ""

# Check .env
if [ -f ".env" ]; then
    echo ".env file: Found"
else
    echo ".env file: MISSING - copy from dev machine!"
fi

echo ""
echo "=== Done ==="
echo "Run with: source venv/bin/activate && python main.py"
