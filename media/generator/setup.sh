#!/bin/bash
#
# JTF News Background Generator - Setup Script
# =============================================
# Sets up the Python virtual environment and installs dependencies
#
# Usage:
#   ./setup.sh
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo -e "${BLUE}=============================================="
echo "  JTF News Background Generator - Setup"
echo -e "==============================================${NC}"
echo ""

# Check Python version
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo -e "${RED}ERROR: Python not found!${NC}"
    echo "Please install Python 3.9 or later."
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
echo -e "Found: ${GREEN}$PYTHON_VERSION${NC}"

# Create virtual environment
echo ""
echo -e "${YELLOW}Creating virtual environment...${NC}"
$PYTHON_CMD -m venv venv

if [ ! -d "venv" ]; then
    echo -e "${RED}ERROR: Failed to create virtual environment${NC}"
    exit 1
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# Upgrade pip
echo ""
echo -e "${YELLOW}Upgrading pip...${NC}"
pip install --upgrade pip

# Install dependencies
echo ""
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo -e "${RED}ERROR: Failed to install dependencies${NC}"
    exit 1
fi

# Create .env from example if it doesn't exist
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo ""
        echo -e "${YELLOW}Creating .env from .env.example...${NC}"
        cp .env.example .env
        echo -e "${YELLOW}IMPORTANT: Edit .env and add your STABILITY_API_KEY${NC}"
    fi
fi

# Create output directories
echo ""
echo -e "${YELLOW}Creating output directories...${NC}"
mkdir -p ../spring ../summer ../fall ../winter logs

# Make scripts executable
chmod +x *.sh

# Summary
echo ""
echo -e "${GREEN}=============================================="
echo "  Setup Complete!"
echo -e "==============================================${NC}"
echo ""
echo "Next steps:"
echo ""
echo "  1. Get your Stability AI API key from:"
echo "     https://platform.stability.ai/account/keys"
echo ""
echo "  2. Add your API key to .env:"
echo -e "     ${BLUE}nano .env${NC}"
echo "     or"
echo -e "     ${BLUE}echo 'STABILITY_API_KEY=sk-your-key-here' > .env${NC}"
echo ""
echo "  3. Test with a single image:"
echo -e "     ${BLUE}./run_all.sh --test${NC}"
echo ""
echo "  4. Generate all images:"
echo -e "     ${BLUE}./run_all.sh${NC}              (sequential, ~6-8 hours)"
echo -e "     ${BLUE}./run_all.sh --parallel${NC}   (parallel, ~2-3 hours)"
echo ""
echo "  Or generate individual seasons:"
echo -e "     ${BLUE}./run_spring.sh${NC}"
echo -e "     ${BLUE}./run_summer.sh${NC}"
echo -e "     ${BLUE}./run_fall.sh${NC}"
echo -e "     ${BLUE}./run_winter.sh${NC}"
echo ""
echo "Estimated cost: ~\$80-150 for 7,680 images"
echo ""
