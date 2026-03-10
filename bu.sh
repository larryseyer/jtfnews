#!/bin/bash

if [ -z "$1" ]; then
    echo "Usage: bu.sh \"commit message\""
    exit 1
fi

# =============================================================================
# RUNTIME FILES — main.py pushes these via GitHub API, never stage them
# =============================================================================
RUNTIME_FILES=(
    "docs/feed.xml"
    "docs/stories.json"
    "docs/monitor.json"
    "docs/podcast.xml"
    "docs/archive/index.json"
    "docs/corrections.json"
    "docs/journalists.json"
    "docs/alexa.json"
    "data/"
    "jtf.log"
)

# =============================================================================
# PULL FIRST — remote is always ahead from main.py API pushes
# Stash first because main.py may have modified runtime files locally
# =============================================================================
echo "Pulling latest from remote..."
git stash --quiet 2>/dev/null
STASHED=$?
git pull --rebase origin main
PULL_STATUS=$?
if [ $STASHED -eq 0 ]; then
    git stash pop --quiet 2>/dev/null
fi

# If rebase conflicts occur on runtime files, keep local (this IS the live server)
if [ $PULL_STATUS -ne 0 ]; then
    echo ""
    echo "Rebase conflict detected. Checking for runtime file conflicts..."
    CONFLICT_FILES=$(git diff --name-only --diff-filter=U)
    ALL_RUNTIME=true
    for file in $CONFLICT_FILES; do
        IS_RUNTIME=false
        for rf in "${RUNTIME_FILES[@]}"; do
            if [[ "$file" == "$rf" || "$file" == "$rf"* ]]; then
                IS_RUNTIME=true
                break
            fi
        done
        if [ "$IS_RUNTIME" = true ]; then
            echo "  Resolving runtime file (keeping local): $file"
            git checkout --ours "$file"
            git add "$file"
        else
            ALL_RUNTIME=false
            echo "  NON-RUNTIME CONFLICT: $file — resolve manually"
        fi
    done
    if [ "$ALL_RUNTIME" = false ]; then
        echo ""
        echo "Non-runtime conflicts need manual resolution. Run 'git rebase --continue' after fixing."
        exit 1
    fi
    git rebase --continue --no-edit 2>/dev/null || git rebase --continue
fi

# =============================================================================
# STAGE EVERYTHING EXCEPT RUNTIME FILES
# =============================================================================
git add .

# Unstage runtime files
for rf in "${RUNTIME_FILES[@]}"; do
    git reset HEAD -- "$rf" 2>/dev/null
done

# Check if anything is staged
if git diff --cached --quiet; then
    echo "Nothing to commit (only runtime files changed)."
    exit 0
fi

echo ""
echo "Staged changes:"
git diff --cached --stat

# =============================================================================
# COMMIT AND PUSH
# =============================================================================
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
zip -r "$ZIP_FILE" . -x "media/*" "media/" "video/*" "video/" "audio/*" "audio/" "data/*" "data/" "venv/*" "venv/" "__pycache__/*" "__pycache__/" ".git/*" ".git/" ".env"

echo ""
echo "Done!"
