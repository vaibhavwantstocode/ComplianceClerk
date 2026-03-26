import json
import re
import ollama
from config import OLLAMA_VISION_MODEL
from src.audit.logger import log_llm_interaction
from src.model.schemas import LeaseDocData


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
        for key in ["village", "survey_no", "district", "lease_area"]:
            match = re.search(rf'"{key}"\s*:\s*"([^"]*)"', text)
            fallback[key] = match.group(1).strip() if match else ""
        return fallback

def process_lease_document_with_llm(filename: str, page_images: dict) -> dict:
    prompt = """You are extracting land details from an Annexure-I table in a lease document.

TASK:
Extract the following fields:

- Village
- Survey Number
- District
- Lease Area (in sq.m)

DOCUMENT STRUCTURE:
- The page contains a structured table with columns such as:
  No | District | Taluka | Village | Owner's Name | R.S. No (Old/New) | Area in SQM

FIELD DEFINITIONS:

1. District:
- Extract from the "District" column

2. Village:
- Extract from the "Village" column

3. Survey Number:
- Extract from "R.S. No → New" column
- This is the correct survey number to use (NOT Old)
- Example: "257"

4. Lease Area:
- Extract from "Area in SQM" column
- This is the lease area value
- Example: "16792"

IMPORTANT INSTRUCTIONS:
- Use ONLY the main table (ignore boundary table below)
- Ignore the "Four side Boundaries of Subject Lands" table
- Do NOT use values like East, West, North, South
- Do NOT extract Old survey number
- Extract values exactly as written
- Do not guess or infer missing values

ROBUSTNESS:
- The table may have slight OCR noise
- Focus on column headers to locate correct values

OUTPUT FORMAT (STRICT JSON ONLY):
{
  "village": "",
  "survey_no": "",
  "district": "",
  "lease_area": ""
}"""

    images = []
    for _, img_bytes in page_images.items():
        if img_bytes:
            images.append(img_bytes)

    if not images:
        return LeaseDocData().model_dump()

    try:
        best_data = LeaseDocData().model_dump()
        best_score = -1

        # Try a few candidate annexure pages and keep the richest extraction.
        for img in images[:4]:
            response = ollama.chat(
                model=OLLAMA_VISION_MODEL,
                messages=[{
                    "role": "user",
                    "content": prompt,
                    "images": [img]
                }],
                format="json",
                think=False,
                options={"temperature": 0.0}
            )

            raw_text = response.message.content or ""
            if not raw_text and getattr(response.message, "thinking", None):
                raw_text = response.message.thinking
            parsed_json = _extract_json_dict(raw_text)
            cleaned = _sanitize_strings(parsed_json, ["village", "survey_no", "district", "lease_area"])
            validated_data = LeaseDocData(**cleaned)
            candidate = validated_data.model_dump()
            score = sum(1 for v in candidate.values() if isinstance(v, str) and v.strip())

            if score > best_score:
                best_score = score
                best_data = candidate

        log_llm_interaction(filename, "LEASE_EXTRACTION", prompt, json.dumps(best_data), best_data, "success")
        return best_data
        
    except Exception as e:
        log_llm_interaction(filename, "LEASE_EXTRACTION", prompt, str(e), {}, "failed")
        return LeaseDocData().model_dump()


