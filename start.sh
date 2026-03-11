#!/bin/bash
# start.sh — Bootstrap and run Scraperrr
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ⚡ Scraperrr — AI Intelligence Feed"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Create .tmp if missing
mkdir -p .tmp

# Check/create venv
if [ ! -d "venv" ]; then
  echo "→ Creating virtual environment..."
  python3 -m venv venv
fi

# Activate
source venv/bin/activate

# Install dependencies
echo "→ Installing dependencies..."
pip install -q -r requirements.txt

# Install Playwright browsers if not already installed
echo "→ Checking Playwright browsers..."
python -m playwright install chromium --quiet 2>/dev/null || true

# Launch
echo "→ Starting server at http://localhost:5001"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
PYTHONPATH="$PROJECT_DIR" python tools/serve_dashboard.py
