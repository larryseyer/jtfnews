#!/bin/bash

if [ -z "$1" ]; then
    echo "Usage: bu.sh \"commit message\""
    exit 1
fi

# =============================================================================
# COMMIT MAIN BRANCH
# =============================================================================
git add .
git commit -m "$1"
git push origin main

# =============================================================================
# BACKUP TO DROPBOX
# =============================================================================
SOURCE="/Users/larryseyer/JTFNews"
DEST_DIR="/Users/larryseyer/Dropbox/Automagic Art/Source Backup/JTFNews Backups"
TIMESTAMP=$(date +"%Y_%m_%d_%H_%M_%S")
# Take first line only, limit to 50 chars, replace spaces/special chars
MESSAGE=$(echo "$1" | head -1 | cut -c1-50 | sed 's/[^a-zA-Z0-9]/_/g' | sed 's/__*/_/g' | sed 's/_$//')
ZIP_FILE="$DEST_DIR/JTFNews_${TIMESTAMP}_${MESSAGE}.zip"
cd "$SOURCE" || exit 1
zip -r "$ZIP_FILE" . -x "media/*" "media/" "gh-pages-dist/*" "gh-pages-dist/" "audio/*" "audio/" "data/*" "data/" "venv/*" "venv/" "__pycache__/*" "__pycache__/" ".git/*" ".git/" ".env"

# =============================================================================
# DEPLOY TO PRODUCTION
# =============================================================================
echo ""
echo "=== Deploying to production ==="
./deploy.sh

# =============================================================================
# DEPLOY TO GITHUB PAGES (using worktree)
# =============================================================================
echo ""
echo "=== Deploying to GitHub Pages ==="
cd "$SOURCE/gh-pages-dist"
git add -A
# Only commit and push if there are changes
if ! git diff --cached --quiet; then
    git commit -m "Deploy: $1"
    git push origin gh-pages
    echo "GitHub Pages deployed successfully"
else
    echo "GitHub Pages: no changes to deploy"
fi
cd "$SOURCE"
