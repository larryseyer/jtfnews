#!/bin/bash
#
# JTF News Background Generator - Run All Seasons
# ================================================
# Generates 1920 images for each of the 4 seasons (7680 total)
# Runs in background with output logged to files
#
# Usage:
#   ./run_all.sh              # Run all seasons sequentially in background
#   ./run_all.sh --parallel   # Run all seasons in parallel (faster, higher API cost)
#   ./run_all.sh --test       # Test mode (1 image per season)
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
IMAGES_PER_SEASON=1920
LOG_DIR="$SCRIPT_DIR/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create logs directory
mkdir -p "$LOG_DIR"

# Check for .env file
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo -e "${RED}ERROR: .env file not found!${NC}"
    echo "Please copy .env.example to .env and add your STABILITY_API_KEY"
    exit 1
fi

# Check for virtual environment
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Running setup...${NC}"
    ./setup.sh
fi

# Activate virtual environment
source "$SCRIPT_DIR/venv/bin/activate"

# Parse arguments
PARALLEL=false
TEST_MODE=false

for arg in "$@"; do
    case $arg in
        --parallel)
            PARALLEL=true
            ;;
        --test)
            TEST_MODE=true
            IMAGES_PER_SEASON=1
            ;;
    esac
done

echo ""
echo "=============================================="
echo "  JTF News Background Image Generator"
echo "=============================================="
echo ""
echo "  Images per season: $IMAGES_PER_SEASON"
echo "  Total images: $((IMAGES_PER_SEASON * 4))"
echo "  Parallel mode: $PARALLEL"
echo "  Logs: $LOG_DIR"
echo ""

if [ "$TEST_MODE" = true ]; then
    echo -e "${YELLOW}TEST MODE: Generating 1 image per season${NC}"
    echo ""
    python generate.py --test
    exit $?
fi

if [ "$PARALLEL" = true ]; then
    echo -e "${GREEN}Starting all 4 seasons in PARALLEL...${NC}"
    echo "Each season will run in its own background process."
    echo ""

    # Start each season in background
    nohup python generate.py --season spring --count $IMAGES_PER_SEASON \
        > "$LOG_DIR/spring_$TIMESTAMP.log" 2>&1 &
    echo "  Spring: PID $! (log: spring_$TIMESTAMP.log)"

    nohup python generate.py --season summer --count $IMAGES_PER_SEASON \
        > "$LOG_DIR/summer_$TIMESTAMP.log" 2>&1 &
    echo "  Summer: PID $! (log: summer_$TIMESTAMP.log)"

    nohup python generate.py --season fall --count $IMAGES_PER_SEASON \
        > "$LOG_DIR/fall_$TIMESTAMP.log" 2>&1 &
    echo "  Fall:   PID $! (log: fall_$TIMESTAMP.log)"

    nohup python generate.py --season winter --count $IMAGES_PER_SEASON \
        > "$LOG_DIR/winter_$TIMESTAMP.log" 2>&1 &
    echo "  Winter: PID $! (log: winter_$TIMESTAMP.log)"

    echo ""
    echo -e "${GREEN}All seasons started!${NC}"
    echo ""
    echo "Monitor progress:"
    echo "  tail -f $LOG_DIR/spring_$TIMESTAMP.log"
    echo "  tail -f $LOG_DIR/summer_$TIMESTAMP.log"
    echo "  tail -f $LOG_DIR/fall_$TIMESTAMP.log"
    echo "  tail -f $LOG_DIR/winter_$TIMESTAMP.log"
    echo ""
    echo "Check running processes:"
    echo "  ps aux | grep generate.py"
    echo ""
    echo "Stop all:"
    echo "  pkill -f 'python generate.py'"

else
    echo -e "${GREEN}Starting all seasons SEQUENTIALLY in background...${NC}"
    echo ""

    # Run all seasons sequentially in one background process
    LOG_FILE="$LOG_DIR/all_seasons_$TIMESTAMP.log"

    nohup bash -c "
        source '$SCRIPT_DIR/venv/bin/activate'
        python generate.py --season all --count $IMAGES_PER_SEASON
    " > "$LOG_FILE" 2>&1 &

    MAIN_PID=$!
    echo "  Main process PID: $MAIN_PID"
    echo "  Log file: $LOG_FILE"
    echo ""
    echo "Monitor progress:"
    echo "  tail -f $LOG_FILE"
    echo ""
    echo "Stop generation:"
    echo "  kill $MAIN_PID"
fi

echo ""
echo "Generation started in background. You can close this terminal."
echo ""
