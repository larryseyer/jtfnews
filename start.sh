#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate

# Log file with timestamp
LOG_FILE="jtf.log"

# Check for --fresh flag
if [ "$1" = "--fresh" ]; then
    echo "Clearing old stories for fresh start..."
    rm -f data/stories.json data/current.txt data/source.txt
    echo "Cleared: stories.json, current.txt, source.txt"
fi

# Clear old log and start fresh
> "$LOG_FILE"

echo "Starting JTF News... (logging to $LOG_FILE)"
echo "Started at $(date)" >> "$LOG_FILE"

# Run python, capture both stdout and stderr to log AND terminal
python3 main.py 2>&1 | tee -a "$LOG_FILE"
