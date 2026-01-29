from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from typing import List
import subprocess
import sys
import os
from pathlib import Path
from app.db.database import get_async_db

router = APIRouter()

# Define script path (adjust based on deployment structure)
# Assuming llm-pipeline is a sibling of backend or deployed together
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
SCRAPER_SCRIPT = BASE_DIR / "llm-pipeline" / "recruit" / "src" / "recruitment_info_gathering.py"

def run_crawler_script():
    """Background task to run the crawler script."""
    try:
        # Check if script exists
        if not SCRAPER_SCRIPT.exists():
            print(f"Error: Scraper script not found at {SCRAPER_SCRIPT}")
            return

        # Run script
        print(f"Triggering crawler: {SCRAPER_SCRIPT}")
        result = subprocess.run(
            [sys.executable, str(SCRAPER_SCRIPT)],
            capture_output=True,
            text=True,
            cwd=str(SCRAPER_SCRIPT.parent) # Run in script dir to resolve relative paths
        )
        
        if result.returncode != 0:
            print(f"Crawler Failed:\n{result.stderr}")
        else:
            print(f"Crawler Success:\n{result.stdout}")
            
    except Exception as e:
        print(f"Crawler Task Exception: {e}")

@router.post("/crawl", status_code=202)
def trigger_crawling(background_tasks: BackgroundTasks, secret: str):
    """
    Trigger the recruitment crawling process in the background.
    Requires a secret key for basic security.
    """
    # Simple security check (in production, use proper admin auth)
    # For now, we'll check against an environment variable or a hardcoded one for demo
    ADMIN_SECRET = os.getenv("ADMIN_SECRET", "nlp-final-admin-secret")
    
    if secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Invalid admin secret")
    
    background_tasks.add_task(run_crawler_script)
    return {"message": "Crawling started in background", "script_path": str(SCRAPER_SCRIPT)}

@router.delete("/clear", status_code=200)
async def clear_database(
    secret: str,
    db = Depends(get_async_db)  # Use dependency for session
):
    """
    Clear all recruitment and recommendation data.
    """
    # Security check
    ADMIN_SECRET = os.getenv("ADMIN_SECRET", "nlp-final-admin-secret")
    if secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Invalid admin secret")

    try:
        from sqlalchemy import text
        # Order matters due to foreign keys (delete recommendations first)
        await db.execute(text("DELETE FROM recommendations"))
        await db.execute(text("DELETE FROM recruitments"))
        await db.commit()
        return {"message": "Recruitments and Recommendations cleared successfully."}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to clear DB: {str(e)}")
