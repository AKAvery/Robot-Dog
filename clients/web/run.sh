#!/bin/bash
# Activate the virtual environment and run the Flask app
cd "$(dirname "$0")/../.."
source venv/bin/activate
python clients/web/app.py
