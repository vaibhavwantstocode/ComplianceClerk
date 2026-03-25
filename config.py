import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
SAMPLE_PDFS_DIR = DATA_DIR / "sample_pdfs"
OUTPUT_DIR = BASE_DIR / "output"
AUDIT_DB_PATH = BASE_DIR / "audit.db"

# Ensure Output Dir exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Gemini API Configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-1.5-flash"  # Upgraded model natively

# Matching strict thresholds can be enabled/disabled
STRICT_MATCH_ENABLED = True
