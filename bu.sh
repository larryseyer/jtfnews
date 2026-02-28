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
# BACKUP TO DOWNLOADS
# =============================================================================
SOURCE="/Users/larryseyer/JTFNews"
DEST_DIR="/Users/larryseyer/Downloads/JTFNews Backups"
TIMESTAMP=$(date +"%Y_%m_%d_%H_%M_%S")
# Take first line only, limit to 50 chars, replace spaces/special chars
MESSAGE=$(echo "$1" | head -1 | cut -c1-50 | sed 's/[^a-zA-Z0-9]/_/g' | sed 's/__*/_/g' | sed 's/_$//')
ZIP_FILE="$DEST_DIR/JTFNews_${TIMESTAMP}_${MESSAGE}.zip"
cd "$SOURCE" || exit 1
zip -r "$ZIP_FILE" . -x "media/*" "media/" "audio/*" "audio/" "data/*" "data/" "venv/*" "venv/" "__pycache__/*" "__pycache__/" ".git/*" ".git/" ".env"

echo ""
echo "Done! Website updates (feed.xml, stories.json, etc.) are pushed automatically by main.py"
