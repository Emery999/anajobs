#!/bin/bash
# Activation script for AnaJobs development environment
# Usage: source activate.sh

if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ AnaJobs virtual environment activated"
    echo "You can now use: anajobs setup, anajobs test, etc."
else
    echo "❌ Virtual environment not found. Run ./scripts/setup_dev.sh first"
fi