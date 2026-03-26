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

# Gemini configuration
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_API_KEY_ENV = "GEMINI_API_KEY"

# Backward-compatible legacy model constant used by deprecated modules.
OLLAMA_VISION_MODEL = os.getenv("OLLAMA_VISION_MODEL", "qwen3-vl:4b")

# Python 3.10 command used for PaddleOCR Annexure-I detection subprocess.
# Examples:
# - Windows: "py -3.10"
# - Linux/macOS: "python3.10"
ANNEXURE_PY310_COMMAND = os.getenv("ANNEXURE_PY310_COMMAND", "py -3.10")

# Matching strict thresholds can be enabled/disabled
STRICT_MATCH_ENABLED = True
