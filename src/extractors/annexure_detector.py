import json
import re
import shlex
import subprocess
from pathlib import Path

import fitz

from config import ANNEXURE_PY310_COMMAND


def _scan_text_layer_for_annexure(pdf_path: str) -> dict:
    pattern = re.compile(r"annexure\s*[-:]?\s*i\b", re.IGNORECASE)
    with fitz.open(pdf_path) as doc:
        for i, page in enumerate(doc):
            text = page.get_text("text") or ""
            if pattern.search(text):
                return {
                    "page_index": i,
                    "confidence": 0.85,
                    "method": "text-layer-fallback",
                    "ok": True,
                }

        return {
            "page_index": max(0, len(doc) - 1),
            "confidence": 0.1,
            "method": "last-page-fallback",
            "ok": False,
            "error": "Annexure-I not found; defaulted to last page.",
        }


def detect_annexure_page(pdf_path: str) -> dict:
    script_path = Path(__file__).parent / "annexure_detector_py310.py"
    cmd = shlex.split(ANNEXURE_PY310_COMMAND) + [str(script_path), str(pdf_path)]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=180)
        if result.returncode == 0:
            payload = json.loads(result.stdout.strip() or "{}")
            if payload.get("ok") and isinstance(payload.get("page_index"), int):
                return payload

            fallback = _scan_text_layer_for_annexure(pdf_path)
            fallback["py310_error"] = payload.get("error", "Unknown py310 detector issue")
            return fallback

        fallback = _scan_text_layer_for_annexure(pdf_path)
        fallback["py310_error"] = result.stderr.strip() or "py310 subprocess failed"
        return fallback
    except Exception as exc:
        fallback = _scan_text_layer_for_annexure(pdf_path)
        fallback["py310_error"] = str(exc)
        return fallback
