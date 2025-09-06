#!/bin/bash
# Run anajobs commands without needing to remember to activate venv
# Usage: ./scripts/run.sh setup
#        ./scripts/run.sh test
#        ./scripts/run.sh search "term"

set -e

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Run ./scripts/setup_dev.sh first"
    exit 1
fi

# Activate virtual environment and run command
source venv/bin/activate
anajobs "$@"