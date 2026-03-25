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
GEMINI_API_KEY = "AIzaSyAJeEiJmRbvTZ28p-vbCkBmAu6osbgHclg"
GEMINI_MODEL = "gemini-2.5-flash"  # Usually the correct identifier for the latest experimental flash models if 1.5 fails, or try "gemini-2.0-flash"

# Matching strict thresholds can be enabled/disabled
STRICT_MATCH_ENABLED = True
