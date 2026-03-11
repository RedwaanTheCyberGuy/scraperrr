"""
Vercel serverless entry point.
Exposes the Flask app for Vercel's Python runtime.
"""

import sys
from pathlib import Path

# Ensure project root is importable
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# Import the Flask app — Vercel looks for the `app` variable
from tools.serve_dashboard import app
