import json
import ollama
from pydantic import ValidationError
from config import OLLAMA_VISION_MODEL
from src.audit.logger import log_llm_interaction
from src.model.schemas import LeaseDocData

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
    # Currently assuming annexure is the only page processed by Qwen here
    for key, img_bytes in page_images.items():
        if img_bytes:
            images.append(img_bytes)
            # break after first if only one needed for annexure, usually Annexure is just 1 page

    if not images:
        return LeaseDocData().model_dump()

    try:
        response = ollama.chat(
            model=OLLAMA_VISION_MODEL,
            messages=[{
                "role": "user",
                "content": prompt,
                "images": images[:1]  # Just pass the annexure image
            }],
            format="json",
            options={"temperature": 0.0}
        )
        
        raw_text = response["message"]["content"]
        
        # Cleanup markdown if necessary
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[-1].split("```")[0].strip()    
        elif "```" in raw_text:
            raw_text = raw_text.split("```")[-1].split("```")[0].strip()        

        parsed_json = json.loads(raw_text)
        validated_data = LeaseDocData(**parsed_json)
        
        log_llm_interaction(filename, "LEASE_EXTRACTION", prompt, raw_text, validated_data.model_dump(), "success")
        return validated_data.model_dump()
        
    except Exception as e:
        log_llm_interaction(filename, "LEASE_EXTRACTION", prompt, str(e), {}, "failed")
        return LeaseDocData().model_dump()


