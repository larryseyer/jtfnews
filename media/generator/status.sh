#!/bin/bash
#
# JTF News Background Generator - Status Check
# =============================================
# Shows progress of image generation
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

TARGET=1920  # Images per season

echo ""
echo -e "${BLUE}=============================================="
echo "  JTF News Background Generator - Status"
echo -e "==============================================${NC}"
echo ""

# Count images in each season folder
count_images() {
    local dir="$1"
    if [ -d "$dir" ]; then
        find "$dir" -name "*.png" 2>/dev/null | wc -l | tr -d ' '
    else
        echo "0"
    fi
}

SPRING=$(count_images "../spring")
SUMMER=$(count_images "../summer")
FALL=$(count_images "../fall")
WINTER=$(count_images "../winter")
TOTAL=$((SPRING + SUMMER + FALL + WINTER))

# Calculate percentages
spring_pct=$((SPRING * 100 / TARGET))
summer_pct=$((SUMMER * 100 / TARGET))
fall_pct=$((FALL * 100 / TARGET))
winter_pct=$((WINTER * 100 / TARGET))
total_pct=$((TOTAL * 100 / (TARGET * 4)))

# Progress bar function
progress_bar() {
    local pct=$1
    local width=30
    local filled=$((pct * width / 100))
    local empty=$((width - filled))
    printf "["
    printf "%${filled}s" | tr ' ' '='
    printf "%${empty}s" | tr ' ' ' '
    printf "]"
}

echo "Season Progress:"
echo ""
printf "  Spring: %4d / %d  %3d%% " "$SPRING" "$TARGET" "$spring_pct"
progress_bar $spring_pct
echo ""

printf "  Summer: %4d / %d  %3d%% " "$SUMMER" "$TARGET" "$summer_pct"
progress_bar $summer_pct
echo ""

printf "  Fall:   %4d / %d  %3d%% " "$FALL" "$TARGET" "$fall_pct"
progress_bar $fall_pct
echo ""

printf "  Winter: %4d / %d  %3d%% " "$WINTER" "$TARGET" "$winter_pct"
progress_bar $winter_pct
echo ""

echo ""
echo "=============================================="
printf "  TOTAL:  %4d / %d  %3d%% " "$TOTAL" "$((TARGET * 4))" "$total_pct"
progress_bar $total_pct
echo ""
echo "=============================================="
echo ""

# Check for running processes
RUNNING=$(pgrep -f "python generate.py" | wc -l | tr -d ' ')
if [ "$RUNNING" -gt 0 ]; then
    echo -e "${GREEN}Active generators: $RUNNING${NC}"
    echo ""
    ps aux | grep "[p]ython generate.py" | awk '{print "  PID: " $2 "  Started: " $9}'
else
    echo -e "${YELLOW}No generators currently running${NC}"
fi

echo ""

# Show recent log activity
if [ -d "logs" ]; then
    LATEST_LOG=$(ls -t logs/*.log 2>/dev/null | head -1)
    if [ -n "$LATEST_LOG" ]; then
        echo "Latest log: $LATEST_LOG"
        echo "Last 3 lines:"
        tail -3 "$LATEST_LOG" | sed 's/^/  /'
    fi
fi

echo ""
