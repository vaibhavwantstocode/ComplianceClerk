import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
SAMPLE_PDFS_DIR = DATA_DIR / "sample_pdfs"
OUTPUT_DIR = BASE_DIR / "output"
AUDIT_DB_PATH = BASE_DIR / "audit.db"


def _load_local_env_file() -> None:
	env_file = BASE_DIR / ".env"
	if not env_file.exists():
		return

	try:
		for line in env_file.read_text(encoding="utf-8").splitlines():
			stripped = line.strip()
			if not stripped or stripped.startswith("#") or "=" not in stripped:
				continue
			key, value = stripped.split("=", 1)
			key = key.strip()
			value = value.strip().strip('"').strip("'")
			if key and key not in os.environ:
				os.environ[key] = value
	except Exception:
		# Continue with process environment if local .env parsing fails.
		pass


_load_local_env_file()

# Ensure Output Dir exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# OpenAI Vision API configuration
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", "gpt-4o")
OPENAI_API_KEY_ENV = "OPENAI_API_KEY"

# Backward-compatible constants (legacy names)
QWEN_VISION_MODEL = os.getenv("QWEN_VISION_MODEL", "qwen3-vl:4b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_API_KEY_ENV = "OLLAMA_API_KEY"
OLLAMA_VISION_MODEL = QWEN_VISION_MODEL

# Python 3.10 command used for PaddleOCR Annexure-I detection subprocess.
# Examples:
# - Windows: "py -3.10"
# - Linux/macOS: "python3.10"
ANNEXURE_PY310_COMMAND = os.getenv("ANNEXURE_PY310_COMMAND", "py -3.10")

# Matching strict thresholds can be enabled/disabled
STRICT_MATCH_ENABLED = True
