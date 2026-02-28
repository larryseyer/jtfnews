#!/bin/bash
# Generate daily digests for ALL archived dates that don't already have videos.
# Steps per date:
#   1. Regenerate TTS audio (since audio is cleaned up after 7 days)
#   2. Record digest via OBS and upload to YouTube
#
# Usage:
#   ./generate_all_digests.sh           # Run all missing dates
#   ./generate_all_digests.sh --dry-run # Show what would be done

PYTHON="./venv/bin/python"
ARCHIVE_DIR="docs/archive/2026"
VIDEO_DIR="video"

DRY_RUN=false
if [ "$1" = "--dry-run" ]; then
    DRY_RUN=true
fi

# Collect all archived dates (sorted chronologically)
DATES=()
for gz in $(ls "$ARCHIVE_DIR"/*.txt.gz 2>/dev/null | sort); do
    DATE=$(basename "$gz" .txt.gz)
    DATES+=("$DATE")
done

if [ ${#DATES[@]} -eq 0 ]; then
    echo "No archived dates found in $ARCHIVE_DIR"
    exit 1
fi

# Filter out dates that already have videos or have no stories
TODO=()
for DATE in "${DATES[@]}"; do
    if [ -f "$VIDEO_DIR/${DATE}-daily-digest.mp4" ]; then
        echo "SKIP $DATE — video already exists"
    else
        # Check if date has stories
        STORY_COUNT=$($PYTHON -c "
from main import load_stories_for_date
stories = load_stories_for_date('$DATE')
print(len(stories))
" 2>/dev/null)
        if [ "$STORY_COUNT" = "0" ] || [ -z "$STORY_COUNT" ]; then
            echo "SKIP $DATE — no stories"
        else
            echo "TODO $DATE — $STORY_COUNT stories"
            TODO+=("$DATE")
        fi
    fi
done

if [ ${#TODO[@]} -eq 0 ]; then
    echo ""
    echo "All dates already have digests. Nothing to do."
    exit 0
fi

echo ""
echo "=== Dates to process: ${#TODO[@]} ==="
for DATE in "${TODO[@]}"; do
    echo "  $DATE"
done
echo ""

if [ "$DRY_RUN" = true ]; then
    echo "(dry run — exiting)"
    exit 0
fi

# Process each date
PASSED=0
FAILED=0
FAILED_DATES=()

for DATE in "${TODO[@]}"; do
    echo ""
    echo "================================================================"
    echo "  Processing $DATE"
    echo "================================================================"

    # Step 1: Regenerate audio
    echo "--- Regenerating audio for $DATE ---"
    $PYTHON main.py --regenerate-audio "$DATE"
    if [ $? -ne 0 ]; then
        echo "FAILED: Audio regeneration failed for $DATE"
        FAILED=$((FAILED + 1))
        FAILED_DATES+=("$DATE")
        continue
    fi

    # Step 2: Run digest (record + upload)
    echo ""
    echo "--- Running digest for $DATE ---"
    $PYTHON test_digest.py --full --date "$DATE" --upload
    if [ $? -ne 0 ]; then
        echo "FAILED: Digest failed for $DATE"
        FAILED=$((FAILED + 1))
        FAILED_DATES+=("$DATE")
        continue
    fi

    PASSED=$((PASSED + 1))
    echo "DONE: $DATE"

    # Brief pause between digests to let OBS settle
    echo "Waiting 10 seconds before next digest..."
    sleep 10
done

echo ""
echo "================================================================"
echo "  SUMMARY"
echo "================================================================"
echo "  Passed: $PASSED"
echo "  Failed: $FAILED"
if [ ${#FAILED_DATES[@]} -gt 0 ]; then
    echo "  Failed dates:"
    for DATE in "${FAILED_DATES[@]}"; do
        echo "    $DATE"
    done
fi
echo "================================================================"
