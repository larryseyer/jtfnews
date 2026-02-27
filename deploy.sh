#!/bin/bash
# deploy.sh - Smart deployment from development to production
#
# Development (Apple Silicon): /Users/larryseyer/JTFNews
# Deployment (Intel/Mojave):   /Volumes/MacLive/Users/larryseyer/JTFNews
#
# Usage:
#   ./deploy.sh              # Default: code + web only (fast, daily use)
#   ./deploy.sh --media      # Add media sync (only copies newer files)
#   ./deploy.sh --data       # Sync data folder (REQUIRES CONFIRMATION)
#   ./deploy.sh --full       # Code + web + media (no data)
#   ./deploy.sh --dry-run    # Preview any operation without executing
#   ./deploy.sh --help       # Show this help
#
# Flags can be combined: ./deploy.sh --media --dry-run

DEV_DIR="/Users/larryseyer/JTFNews"
DEPLOY_DIR="/Volumes/MacLive/Users/larryseyer/JTFNews"

# Parse flags
SYNC_MEDIA=false
SYNC_DATA=false
DRY_RUN=false
SHOW_HELP=false

for arg in "$@"; do
    case $arg in
        --media)
            SYNC_MEDIA=true
            ;;
        --data)
            SYNC_DATA=true
            ;;
        --full)
            SYNC_MEDIA=true
            ;;
        --dry-run)
            DRY_RUN=true
            ;;
        --help|-h)
            SHOW_HELP=true
            ;;
        *)
            echo "Unknown option: $arg"
            echo "Use --help to see available options"
            exit 1
            ;;
    esac
done

# Show help
if [ "$SHOW_HELP" = true ]; then
    echo "deploy.sh - Smart deployment from development to production"
    echo ""
    echo "Usage:"
    echo "  ./deploy.sh              Default: code + web only (fast, daily use)"
    echo "  ./deploy.sh --media      Add media sync (only copies newer files)"
    echo "  ./deploy.sh --data       Sync data folder (REQUIRES CONFIRMATION)"
    echo "  ./deploy.sh --full       Code + web + media (no data)"
    echo "  ./deploy.sh --dry-run    Preview any operation without executing"
    echo "  ./deploy.sh --help       Show this help"
    echo ""
    echo "Flags can be combined: ./deploy.sh --media --dry-run"
    echo ""
    echo "Examples:"
    echo "  Daily code changes:      ./deploy.sh"
    echo "  Preview what deploys:    ./deploy.sh --dry-run"
    echo "  Added spring images:     ./deploy.sh --media"
    echo "  Preview media sync:      ./deploy.sh --media --dry-run"
    echo "  Full refresh (rare):     ./deploy.sh --full"
    exit 0
fi

# Check if deployment volume is mounted
if [ ! -d "$DEPLOY_DIR" ]; then
    echo "ERROR: Deployment folder not accessible: $DEPLOY_DIR"
    echo "Is the deployment volume mounted?"
    exit 1
fi

# Set rsync flags
RSYNC_FLAGS="-av"
if [ "$DRY_RUN" = true ]; then
    RSYNC_FLAGS="-avn"
    echo "=== DRY RUN MODE - No files will be copied ==="
    echo ""
fi

echo "Deploying from $DEV_DIR to $DEPLOY_DIR"
echo "====================================================="
echo ""

# =============================================================================
# STEP 1: Code + Web (always runs)
# =============================================================================
echo ">>> Deploying code + web assets..."
echo "    (source code, config, web/, scripts)"
echo ""

rsync $RSYNC_FLAGS \
    --exclude='venv/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='.git/' \
    --exclude='.gitignore' \
    --exclude='data/' \
    --exclude='audio/' \
    --exclude='archive/' \
    --exclude='media/' \
    --exclude='documentation/' \
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

# =============================================================================
# STEP 2: Media (optional, uses -u for incremental)
# =============================================================================
if [ "$SYNC_MEDIA" = true ]; then
    echo ""
    echo ">>> Deploying media (incremental, only newer files)..."
    echo "    Excluding: generator/ (39MB, not needed on deploy)"
    echo ""

    # Use -u flag: only copy if source is newer than destination
    MEDIA_FLAGS="-avu"
    if [ "$DRY_RUN" = true ]; then
        MEDIA_FLAGS="-avun"
    fi

    rsync $MEDIA_FLAGS \
        --exclude='generator/' \
        --exclude='.DS_Store' \
        "$DEV_DIR/media/" "$DEPLOY_DIR/media/"
fi

# =============================================================================
# STEP 3: Data (optional, requires confirmation)
# =============================================================================
if [ "$SYNC_DATA" = true ]; then
    echo ""
    echo "!!! WARNING: You are about to sync the data folder !!!"
    echo "    This will overwrite stories.json, queue.json, etc. on deploy"
    echo ""

    if [ "$DRY_RUN" = true ]; then
        echo ">>> Preview of data sync:"
        rsync -avn \
            --exclude='.DS_Store' \
            "$DEV_DIR/data/" "$DEPLOY_DIR/data/"
    else
        read -p "Are you sure? Type 'yes' to confirm: " confirm
        if [ "$confirm" = "yes" ]; then
            echo ">>> Syncing data folder..."
            rsync -av \
                --exclude='.DS_Store' \
                "$DEV_DIR/data/" "$DEPLOY_DIR/data/"
        else
            echo "Data sync cancelled."
        fi
    fi
fi

# =============================================================================
# DONE
# =============================================================================
echo ""
if [ "$DRY_RUN" = true ]; then
    echo "=== DRY RUN COMPLETE - No files were copied ==="
else
    echo "=== Deployment complete ==="
    echo ""
    echo "NEXT STEPS on the deployment machine:"
    echo "  1. If venv doesn't work: ./fix-after-copy.sh"
    echo "  2. To run: ./start.sh"
fi
