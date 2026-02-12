#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate

# Log file with timestamp
LOG_FILE="jtf.log"

# Check for --fresh flag
if [ "$1" = "--fresh" ]; then
    echo "Clearing old stories for fresh start..."
    rm -f data/stories.json data/current.txt data/source.txt
    > "$LOG_FILE"
    echo "Cleared: stories.json, current.txt, source.txt, jtf.log"
fi

echo "Starting JTF News... (logging to $LOG_FILE)"

# Run python - main.py handles its own logging to jtf.log
python3 main.py
