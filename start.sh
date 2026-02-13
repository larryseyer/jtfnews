#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate

# Log file with timestamp
LOG_FILE="jtf.log"

# Check for --rebuild flag
if [ "$1" = "--rebuild" ]; then
    echo "Rebuilding stories.json from daily log..."
    python3 main.py --rebuild
    exit $?
fi

# Check for --fresh flag
if [ "$1" = "--fresh" ]; then
    echo ""
    echo "=========================================="
    echo "  WARNING: --fresh will DELETE data!"
    echo "=========================================="
    echo ""
    echo "This will delete:"
    echo "  - stories.json (all today's stories)"
    echo "  - current.txt, source.txt"
    echo "  - jtf.log"
    echo ""
    echo "Only use when file structure has changed."
    echo "If you accidentally cleared stories, use --rebuild instead."
    echo ""
    read -p "Are you sure? (y/N): " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo "Aborted."
        exit 1
    fi
    echo "Clearing old stories for fresh start..."
    rm -f data/stories.json data/current.txt data/source.txt
    > "$LOG_FILE"
    echo "Cleared: stories.json, current.txt, source.txt, jtf.log"
fi

echo "Starting JTF News... (logging to $LOG_FILE)"

# Run python - main.py handles its own logging to jtf.log
python3 main.py
