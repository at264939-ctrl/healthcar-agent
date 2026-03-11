#!/bin/bash
# Run the Send to GitHub application

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Activate virtual environment and run
source venv/bin/activate
python main.py
