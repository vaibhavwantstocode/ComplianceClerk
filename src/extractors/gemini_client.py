import base64
import json
import re
import urllib.error
import urllib.request
from typing import Iterable

from config import GEMINI_API_KEY_ENV, GEMINI_MODEL


def _extract_json_dict(raw_text: str) -> dict:
    text = (raw_text or "").strip()
    if "```json" in text:
        text = text.split("```json")[-1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[-1].split("```")[0].strip()

    if "{" in text and "}" in text:
        text = text[text.find("{"):text.rfind("}") + 1]

    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _sanitize_fields(data: dict, required_fields: Iterable[str]) -> dict:
    clean = {}
    for key in required_fields:
        value = data.get(key, "") if isinstance(data, dict) else ""
        if value is None:
            clean[key] = ""
            continue
        sval = str(value).strip()
        clean[key] = "" if sval.lower() == "null" else sval
    return clean


def _missing_fields(data: dict, required_fields: Iterable[str]) -> list[str]:
    missing = []
    for key in required_fields:
        value = data.get(key, "") if isinstance(data, dict) else ""
        if not isinstance(value, str) or not value.strip():
            missing.append(key)
    return missing


def _gemini_generate(prompt: str, image_bytes: bytes) -> str:
    api_key = __import__("os").getenv(GEMINI_API_KEY_ENV, "").strip()
    if not api_key:
        raise RuntimeError(f"Missing {GEMINI_API_KEY_ENV} environment variable.")

    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={api_key}"

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/png",
                            "data": base64.b64encode(image_bytes).decode("utf-8"),
                        }
                    },
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0,
            "responseMimeType": "application/json",
        },
    }

    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Gemini HTTP {exc.code}: {details}") from exc

    parsed = json.loads(body)
    candidates = parsed.get("candidates", [])
    if not candidates:
        return ""

    parts = candidates[0].get("content", {}).get("parts", [])
    text_chunks = [p.get("text", "") for p in parts if isinstance(p, dict)]
    return "\n".join([chunk for chunk in text_chunks if chunk]).strip()


def run_gemini_with_retry(
    primary_prompt: str,
    image_bytes: bytes,
    required_fields: list[str],
    retry_context: str,
) -> tuple[dict, str, str, list[str]]:
    primary_raw = _gemini_generate(primary_prompt, image_bytes)
    primary_parsed = _sanitize_fields(_extract_json_dict(primary_raw), required_fields)
    missing = _missing_fields(primary_parsed, required_fields)

    if not missing:
        return primary_parsed, primary_raw, "", []

    retry_prompt = (
        f"{retry_context}\n\n"
        "You must fill ONLY the missing fields listed below using the same document image.\n"
        f"Missing fields: {', '.join(missing)}\n"
        "Return STRICT JSON with all required fields. Keep already-correct fields unchanged."
    )

    retry_raw = _gemini_generate(retry_prompt, image_bytes)
    retry_parsed = _sanitize_fields(_extract_json_dict(retry_raw), required_fields)

    merged = dict(primary_parsed)
    for key in missing:
        retry_value = retry_parsed.get(key, "")
        if isinstance(retry_value, str) and retry_value.strip():
            merged[key] = retry_value.strip()

    final_missing = _missing_fields(merged, required_fields)
    return merged, primary_raw, retry_raw, final_missing
