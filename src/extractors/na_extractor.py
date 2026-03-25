import json
import ollama
from pydantic import ValidationError
from config import OLLAMA_VISION_MODEL
from src.audit.logger import log_llm_interaction
from src.model.schemas import NAOrderData

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
            options={"temperature": 0.0}
        )
        
        raw_text = response["message"]["content"]
        
        # Cleanup markdown if necessary
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[-1].split("```")[0].strip()    
        elif "```" in raw_text:
            raw_text = raw_text.split("```")[-1].split("```")[0].strip()        

        parsed_json = json.loads(raw_text)
        validated_data = NAOrderData(**parsed_json)
        
        log_llm_interaction(filename, "NA_ORDER_EXTRACTION", prompt, raw_text, validated_data.model_dump(), "success")
        return validated_data.model_dump()
        
    except Exception as e:
        log_llm_interaction(filename, "NA_ORDER_EXTRACTION", prompt, str(e), {}, "failed")
        return NAOrderData().model_dump()

