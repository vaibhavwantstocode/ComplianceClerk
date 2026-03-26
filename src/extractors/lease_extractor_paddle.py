import json
import re
import shlex
import subprocess
from pathlib import Path

from config import ANNEXURE_PY310_COMMAND
from src.audit.logger import log_llm_interaction


def _extract_json_from_stdout(stdout_text: str) -> dict:
    text = stdout_text or ""
    matches = re.findall(r"\{[\s\S]*\}", text)
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


def process_lease_document_with_paddle(pdf_path: str) -> dict:
    script_path = Path(__file__).parent / "lease_paddle_pipeline_py310.py"
    cmd = shlex.split(ANNEXURE_PY310_COMMAND) + [str(script_path), str(pdf_path)]

    proc_env = dict(__import__("os").environ)
    proc_env.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
    proc_env.setdefault("FLAGS_use_mkldnn", "0")
    proc_env.setdefault("FLAGS_enable_pir_api", "0")

    filename = Path(pdf_path).name
    step = "LEASE_PADDLE_EXTRACTION"

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=420, env=proc_env)
        payload = _extract_json_from_stdout(result.stdout)

        if result.returncode != 0:
            msg = result.stderr.strip() or "lease paddle subprocess failed"
            log_llm_interaction(filename, step, "paddleocr_pipeline", msg, {}, "failed")
            return {
                "ok": False,
                "annexure_page_index": -1,
                "data": {
                    "village": "",
                    "survey_no": "",
                    "district": "",
                    "taluka": "",
                    "area": "",
                    "lease_deed_no": "",
                    "date": "",
                },
                "error": msg,
            }

        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        normalized = {
            "village": str(data.get("village", "") or "").strip(),
            "survey_no": str(data.get("survey_no", "") or "").strip(),
            "district": str(data.get("district", "") or "").strip(),
            "taluka": str(data.get("taluka", "") or "").strip(),
            "area": str(data.get("area", "") or "").strip(),
            "lease_deed_no": str(data.get("lease_deed_no", "") or "").strip(),
            "date": str(data.get("date", "") or "").strip(),
        }

        parsed_out = {
            "ok": bool(payload.get("ok", False)),
            "annexure_page_index": int(payload.get("annexure_page_index", -1)) if str(payload.get("annexure_page_index", "")).strip() else -1,
            "data": normalized,
            "error": str(payload.get("error", "") or "").strip(),
        }

        log_llm_interaction(filename, step, "paddleocr_pipeline", result.stdout[-3000:], parsed_out, "success" if parsed_out["ok"] else "partial")
        return parsed_out

    except Exception as exc:
        log_llm_interaction(filename, step, "paddleocr_pipeline", str(exc), {}, "failed")
        return {
            "ok": False,
            "annexure_page_index": -1,
            "data": {
                "village": "",
                "survey_no": "",
                "district": "",
                "taluka": "",
                "area": "",
                "lease_deed_no": "",
                "date": "",
            },
            "error": str(exc),
        }
