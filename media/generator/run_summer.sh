#!/bin/bash
# Generate Summer season images in background
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

source venv/bin/activate 2>/dev/null || { echo "Run ./setup.sh first"; exit 1; }

mkdir -p logs
LOG="logs/summer_$(date +%Y%m%d_%H%M%S).log"

echo "Starting Summer generation (1920 images)..."
echo "Log: $LOG"
echo ""

nohup python generate.py --season summer --count 1920 > "$LOG" 2>&1 &
echo "PID: $!"
echo "Monitor: tail -f $LOG"
