#!/bin/bash
# deploy.sh - Copy source files from development to deployment
#
# Development (Apple Silicon): /Users/larryseyer/JTFNews
# Deployment (Intel/Mojave):   /Volumes/MacLive/Users/larryseyer/JTFNews
#
# IMPORTANT: This only copies SOURCE CODE, not the venv or runtime data.
# After deploying, run fix-after-copy.sh on the deployment machine to:
#   - Recreate the venv with Intel-compatible packages
#   - Set up the gh-pages worktree

DEV_DIR="/Users/larryseyer/JTFNews"
DEPLOY_DIR="/Volumes/MacLive/Users/larryseyer/JTFNews"

# Check if deployment volume is mounted
if [ ! -d "$DEPLOY_DIR" ]; then
    echo "ERROR: Deployment folder not accessible: $DEPLOY_DIR"
    echo "Is the deployment volume mounted?"
    exit 1
fi

echo "Deploying source files from $DEV_DIR to $DEPLOY_DIR"
echo "====================================================="
echo ""
echo "Copying: source code, config, web assets, media"
echo "Excluding: venv, runtime data, git, documentation"
echo ""

# Use rsync to copy source files only
# -a = archive mode (preserves permissions, timestamps)
# -v = verbose
# NOTE: No -u flag! Dev is ALWAYS authoritative - deploy is overwritten regardless of timestamps
# --delete = remove files on deployment that don't exist in dev (within copied dirs)

rsync -av \
    --exclude='venv/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='.git/' \
    --exclude='.gitignore' \
    --exclude='data/' \
    --exclude='audio/' \
    --exclude='archive/' \
    --exclude='gh-pages-dist/' \
    --exclude='.env' \
    --exclude='.DS_Store' \
    --exclude='*.log' \
    --exclude='*.zip' \
    --exclude='SPECIFICATION.md' \
    --exclude='PromptStart.md' \
    --exclude='Readme.md' \
    --exclude='CLAUDE.md' \
    --exclude='LICENSE.md' \
    --exclude='keywords.md' \
    --exclude='docs/' \
    --exclude='.claude/' \
    --exclude='.serena/' \
    --exclude='bu.sh' \
    --exclude='deploy.sh' \
    "$DEV_DIR/" "$DEPLOY_DIR/"

echo ""
echo "=== Deployment complete ==="
echo ""
echo "Files copied: main.py, config.json, requirements.txt, web/, media/, etc."
echo ""
echo "NEXT STEPS on the deployment machine:"
echo "  1. If venv doesn't work: ./fix-after-copy.sh"
echo "  2. To run: ./start.sh"
