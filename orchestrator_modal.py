"""
Modal application to run the Scraperrr orchestrator on a schedule.
"""

import modal
from pathlib import Path
import sys

# Define the Modal Image with necessary dependencies
# We also need to copy the project files into the image
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
        "lxml>=5.0.0",
        "python-dateutil>=2.9.0",
        "playwright>=1.42.0",
        "defusedxml>=0.7.1"
    )
    .run_commands("playwright install chromium")
    .add_local_dir(".", remote_path="/root/scraperrr")
)

app = modal.App("scraperrr-orchestrator", image=image)

# Define the scheduled function
# Runs every 24 hours
@app.function(
    schedule=modal.Period(hours=24),
    timeout=600, # 10 minutes timeout to be safe
)
def run_scrapers_job():
    print("Starting scheduled Scraperrr run in Modal...")
    
    # Add the mounted directory to sys.path so we can import our tools
    sys.path.insert(0, "/root/scraperrr")
    
    try:
        from tools.run_all_scrapers import run
        result = run()
        print(f"Modal scrape completed successfully.")
        print(f"Total articles found: {result.get('total_count', 0)}")
        
        if result.get("errors"):
            print("Errors encountered during scrape:")
            for err in result["errors"]:
                print(f" - {err}")
    except Exception as e:
        print(f"Failed to run scrapers in Modal: {e}")

@app.local_entrypoint()
def main():
    print("Triggering a manual run of the scraper job...")
    run_scrapers_job.remote()
    print("Manual run finished.")
