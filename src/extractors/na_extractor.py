import json
import re
import ollama
from config import OLLAMA_VISION_MODEL
from src.audit.logger import log_llm_interaction
from src.model.schemas import NAOrderData


def _sanitize_strings(data: dict, keys: list[str]) -> dict:
    cleaned = {}
    for key in keys:
        value = data.get(key, "")
        cleaned[key] = str(value).strip() if value is not None else ""
    return cleaned


def _extract_json_dict(raw_text: str) -> dict:
    text = raw_text or ""
    if "```json" in text:
        text = text.split("```json")[-1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[-1].split("```")[0].strip()

    if "{" in text and "}" in text:
        text = text[text.find("{"):text.rfind("}") + 1]

    try:
        return json.loads(text)
    except Exception:
        fallback = {}
        for key in ["village", "survey_no", "district", "area_na", "date", "na_order_no"]:
            match = re.search(rf'"{key}"\s*:\s*"([^"]*)"', text)
            fallback[key] = match.group(1).strip() if match else ""
        return fallback

def process_na_order_with_llm(filename: str, page_image: bytes) -> dict:
    prompt = """You are extracting structured data from a government land document.

TASK:
Extract the following fields from this document:

- Village
- Survey Number (including subdivision like 251/p2)
- District
- Area in NA Order (total land area in sq.m)
- Date (order date)
- NA Order Number

INSTRUCTIONS:
- This is a government NA permission order
- The document may be in Gujarati
- Extract exact values as written
- Do not translate numbers incorrectly
- Do not guess missing values

OUTPUT FORMAT (STRICT JSON ONLY):
{
  "village": "",
  "survey_no": "",
  "district": "",
  "area_na": "",
  "date": "",
  "na_order_no": ""
}"""
    
    try:
        response = ollama.chat(
            model=OLLAMA_VISION_MODEL,
            messages=[{
                "role": "user",
                "content": prompt,
                "images": [page_image]
            }],
            format="json",
            think=False,
            options={"temperature": 0.0}
        )

        raw_text = response.message.content or ""
        if not raw_text and getattr(response.message, "thinking", None):
            raw_text = response.message.thinking
        parsed_json = _extract_json_dict(raw_text)
        cleaned = _sanitize_strings(parsed_json, ["village", "survey_no", "district", "area_na", "date", "na_order_no"])
        validated_data = NAOrderData(**cleaned)
        
        log_llm_interaction(filename, "NA_ORDER_EXTRACTION", prompt, raw_text, validated_data.model_dump(), "success")
        return validated_data.model_dump()
        
    except Exception as e:
        log_llm_interaction(filename, "NA_ORDER_EXTRACTION", prompt, str(e), {}, "failed")
        return NAOrderData().model_dump()


