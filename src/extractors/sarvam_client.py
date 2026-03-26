import base64
import json
import urllib.error
import urllib.request
from typing import Iterable

from config import SARVAM_API_KEY_ENV, SARVAM_BASE_URL, SARVAM_VISION_MODEL


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


def _content_to_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks = []
        for part in content:
            if isinstance(part, dict) and part.get("type") in ("text", "output_text"):
                chunks.append(str(part.get("text", "")))
        return "\n".join([c for c in chunks if c]).strip()
    return ""


def _sarvam_generate(prompt: str, image_bytes: bytes) -> str:
    api_key = __import__("os").getenv(SARVAM_API_KEY_ENV, "").strip()
    if not api_key:
        raise RuntimeError(f"Missing {SARVAM_API_KEY_ENV} environment variable.")

    endpoint = f"{SARVAM_BASE_URL.rstrip('/')}/chat/completions"

    payload = {
        "model": SARVAM_VISION_MODEL,
        "temperature": 0,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "data:image/png;base64," + base64.b64encode(image_bytes).decode("utf-8")
                        },
                    },
                ],
            }
        ],
        "response_format": {"type": "json_object"},
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "api-subscription-key": api_key,
    }

    def _post(req_payload: dict) -> str:
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(req_payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=180) as resp:
            return resp.read().decode("utf-8")

    try:
        body = _post(payload)
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")
        # Some deployments reject response_format or multimodal schema differences.
        if exc.code in (400, 422):
            fallback_payload = dict(payload)
            fallback_payload.pop("response_format", None)
            try:
                body = _post(fallback_payload)
            except urllib.error.HTTPError as exc2:
                details2 = exc2.read().decode("utf-8", errors="ignore")
                raise RuntimeError(f"Sarvam HTTP {exc2.code}: {details2}") from exc2
            except Exception as exc2:
                raise RuntimeError(f"Sarvam request failed: {exc2}") from exc2
        else:
            raise RuntimeError(f"Sarvam HTTP {exc.code}: {details}") from exc
    except Exception as exc:
        raise RuntimeError(f"Sarvam request failed: {exc}") from exc

    parsed = json.loads(body)
    choices = parsed.get("choices", [])
    if not choices:
        return ""

    message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
    return _content_to_text(message.get("content", ""))


def run_sarvam_with_retry(
    primary_prompt: str,
    image_bytes: bytes,
    required_fields: list[str],
    retry_context: str,
) -> tuple[dict, str, str, list[str]]:
    primary_raw = _sarvam_generate(primary_prompt, image_bytes)
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

    retry_raw = _sarvam_generate(retry_prompt, image_bytes)
    retry_parsed = _sanitize_fields(_extract_json_dict(retry_raw), required_fields)

    merged = dict(primary_parsed)
    for key in missing:
        retry_value = retry_parsed.get(key, "")
        if isinstance(retry_value, str) and retry_value.strip():
            merged[key] = retry_value.strip()

    final_missing = _missing_fields(merged, required_fields)
    return merged, primary_raw, retry_raw, final_missing
