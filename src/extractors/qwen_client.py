import base64
import json
import urllib.error
import urllib.request
from typing import Iterable

from config import OLLAMA_API_KEY_ENV, OLLAMA_BASE_URL, QWEN_VISION_MODEL


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
    out = {}
    for key in required_fields:
        value = data.get(key, "") if isinstance(data, dict) else ""
        if value is None:
            out[key] = ""
            continue
        sval = str(value).strip()
        out[key] = "" if sval.lower() == "null" else sval
    return out


def _missing_fields(data: dict, required_fields: Iterable[str]) -> list[str]:
    missing = []
    for key in required_fields:
        value = data.get(key, "") if isinstance(data, dict) else ""
        if not isinstance(value, str) or not value.strip():
            missing.append(key)
    return missing


def _ollama_generate(prompt: str, image_bytes: bytes) -> str:
    endpoint = f"{OLLAMA_BASE_URL.rstrip('/')}/api/chat"
    api_key = __import__("os").getenv(OLLAMA_API_KEY_ENV, "").strip()

    payload = {
        "model": QWEN_VISION_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt,
                "images": [base64.b64encode(image_bytes).decode("utf-8")],
            }
        ],
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0,
        },
    }

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Qwen/Ollama HTTP {exc.code}: {details}") from exc
    except Exception as exc:
        raise RuntimeError(f"Qwen/Ollama request failed: {exc}") from exc

    parsed = json.loads(body)
    message = parsed.get("message", {}) if isinstance(parsed, dict) else {}
    content = message.get("content", "") if isinstance(message, dict) else ""
    return content or ""


def run_qwen_with_retry(
    primary_prompt: str,
    image_bytes: bytes,
    required_fields: list[str],
    retry_context: str,
) -> tuple[dict, str, str, list[str]]:
    primary_raw = _ollama_generate(primary_prompt, image_bytes)
    primary_parsed = _sanitize_fields(_extract_json_dict(primary_raw), required_fields)
    missing = _missing_fields(primary_parsed, required_fields)

    if not missing:
        return primary_parsed, primary_raw, "", []

    retry_prompt = (
        f"{retry_context}\n\n"
        "You must fill ONLY the missing fields listed below from this same page image.\n"
        f"Missing fields: {', '.join(missing)}\n"
        "Return STRICT JSON with all required fields."
    )

    retry_raw = _ollama_generate(retry_prompt, image_bytes)
    retry_parsed = _sanitize_fields(_extract_json_dict(retry_raw), required_fields)

    merged = dict(primary_parsed)
    for key in missing:
        retry_value = retry_parsed.get(key, "")
        if isinstance(retry_value, str) and retry_value.strip():
            merged[key] = retry_value.strip()

    final_missing = _missing_fields(merged, required_fields)
    return merged, primary_raw, retry_raw, final_missing
