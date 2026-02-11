#!/bin/bash

if [ -z "$1" ]; then
    echo "Usage: bu.sh \"commit message\""
    exit 1
fi

git add .
git commit -m "$1"
git push origin main

# Backup
SOURCE="/Users/larryseyer/JTFNews"
DEST_DIR="/Users/larryseyer/Dropbox/Automagic Art/Source Backup/JTFNews Backups"
TIMESTAMP=$(date +"%Y_%m_%d_%H_%M_%S")
MESSAGE=$(echo "$1" | sed 's/ /_/g')
ZIP_FILE="$DEST_DIR/JTFNews_${TIMESTAMP}_${MESSAGE}.zip"
cd "$SOURCE" || exit 1
zip -r "$ZIP_FILE" . -x "media/*" "media/"
