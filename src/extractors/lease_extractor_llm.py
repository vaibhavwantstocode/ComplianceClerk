import json
import ollama
from pydantic import ValidationError
from config import OLLAMA_VISION_MODEL
from src.audit.logger import log_llm_interaction
from src.model.schemas import LeaseDocData

def process_lease_document_with_llm(filename: str, page_images: dict) -> dict:
    prompt = """You are extracting land details from an Annexure-I table.

TASK:
Extract the following:

- Village
- Survey Number
- District
- Lease Area (in sq.m)

INSTRUCTIONS:
- This page contains a table
- Extract exact values
- Do not infer or guess

OUTPUT:
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

