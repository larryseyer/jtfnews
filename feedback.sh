#!/bin/bash
# JTF News Feedback Viewer launcher
# Starts the localhost-only feedback viewer and opens it in your browser.
# Press Ctrl+C to stop.

PORT=${1:-8899}
DIR="$(cd "$(dirname "$0")" && pwd)"

# Kill any existing instance on this port
lsof -ti:$PORT | xargs kill 2>/dev/null

# Start the server in the background
python3 "$DIR/view_feedback.py" --port $PORT &
SERVER_PID=$!

# Wait for server to start
sleep 1

# Open in browser
open "http://127.0.0.1:$PORT"

# Wait for Ctrl+C
trap "kill $SERVER_PID 2>/dev/null; exit 0" INT TERM
echo ""
echo "  Press Ctrl+C to stop the feedback viewer."
echo ""
wait $SERVER_PID
