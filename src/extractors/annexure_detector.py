import json
import re
import shlex
import subprocess
from pathlib import Path

import fitz

from config import ANNEXURE_PY310_COMMAND


def _scan_text_layer_for_annexure(pdf_path: str) -> dict:
    pattern = re.compile(r"annexure\s*[-–]?\s*i", re.IGNORECASE)
    with fitz.open(pdf_path) as doc:
        total = len(doc)
        start_idx = 29
        end_idx = min(37, total - 1)
        if total <= start_idx:
            return {
                "annexure_page_index": -1,
                "page_index": max(0, total - 1),
                "confidence": 0.0,
                "method": "text-layer-range30_38",
                "ok": False,
                "error": "Document has fewer than 30 pages.",
            }

        for i in range(start_idx, end_idx + 1):
            page = doc[i]
            text = page.get_text("text") or ""
            if pattern.search(text):
                return {
                    "annexure_page_index": i,
                    "page_index": i,
                    "confidence": 0.85,
                    "method": "text-layer-range30_38",
                    "ok": True,
                }

        return {
            "annexure_page_index": -1,
            "page_index": end_idx,
            "confidence": 0.0,
            "method": "text-layer-range30_38",
            "ok": False,
            "error": "Annexure-I not found in pages 30-38.",
        }


def _extract_json_from_stdout(stdout_text: str) -> dict:
    text = stdout_text or ""
    matches = re.findall(r"\{[\s\S]*?\}", text)
    if not matches:
        return {}
    for candidate in reversed(matches):
        try:
            payload = json.loads(candidate)
            if isinstance(payload, dict):
                return payload
        except Exception:
            continue
    return {}


def detect_annexure_page(pdf_path: str) -> dict:
    script_path = Path(__file__).parent / "annexure_detector_py310.py"
    cmd = shlex.split(ANNEXURE_PY310_COMMAND) + [str(script_path), str(pdf_path)]
    proc_env = dict(__import__("os").environ)
    proc_env.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
    proc_env.setdefault("FLAGS_use_mkldnn", "0")
    proc_env.setdefault("FLAGS_enable_pir_api", "0")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=180, env=proc_env)
        if result.returncode == 0:
            payload = _extract_json_from_stdout(result.stdout)
            if payload.get("ok") and isinstance(payload.get("annexure_page_index"), int):
                payload.setdefault("page_index", payload.get("annexure_page_index"))
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
