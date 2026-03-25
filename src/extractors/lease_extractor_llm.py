import json
from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError
from config import GEMINI_API_KEY, GEMINI_MODEL
from src.audit.logger import log_llm_interaction
from src.model.schemas import LeaseDocData

def process_lease_document_with_llm(filename: str, page_images: dict) -> dict:
    """
    Uses Gemini Flash Vision to extract lease data from scanned image pages.
    page_images should be a dict: { 'echallan': bytes, 'annexure': bytes, 'dnr': bytes }
    Returns a dictionary matching LeaseDocData schema.
    """
    if not GEMINI_API_KEY:
        print("WARNING: GEMINI_API_KEY not set. Returning empty lease data.")
        return LeaseDocData().model_dump()

    client = genai.Client(api_key=GEMINI_API_KEY)

    # We want to pass images to Gemini. google-genai accepts bytes with mime type formatting.
    contents = [
        f"You are an expert document extraction system analyzing '{filename}'. Extract the following fields strictly into JSON.",
        "1. 'lease_start': From the e-Challan 'Printed On' date.",
        "2. 'lease_area': From the Annexure-I table. Look for 'Area in SQM' or similar. It should be a number, e.g., '4047.00'.",
        "3. 'lease_doc_no': Locate the large DNR stamp. In the box directly below 'DNR', there are numbers separated by lines. Combine the left-most number and the bottom year with a slash (e.g., '141/2026', '838/2026').",
        f"CRITICAL: The visual bounding boxes often look like the number '1'. For instance, you might see '1141' or '11/2026' instead of '141/2026'. The filename usually contains the true deed number (e.g., '{filename}'). Use context! Do not include table borders as digits!",
        "If a field is missing, return null."
    ]

    for key, img_bytes in page_images.items():
        if img_bytes:
            contents.append(types.Part.from_bytes(data=img_bytes, mime_type='image/png'))
            
    # Define JSON schema output
    response_schema = {
        "type": "OBJECT",
        "properties": {
            "lease_start": {"type": "STRING"},
            "lease_area": {"type": "STRING"},
            "lease_doc_no": {"type": "STRING"}
        }
    }

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=response_schema,
                temperature=0.0
            ) 
        )
        
        raw_text = response.text
        parsed_json = json.loads(raw_text)
        
        # Pydantic Schema Validation
        validated_data = LeaseDocData(**parsed_json)
        
        # Format the actual prompt strings for audit trailing
        prompt_text = "\n".join(contents[:6])
        
        # Audit Log
        log_llm_interaction(filename, "LEASE_EXTRACTION", prompt_text, raw_text, validated_data.model_dump(), "success")
        
        return validated_data.model_dump()
        
    except Exception as e:
        log_llm_interaction(filename, "LEASE_EXTRACTION", "Extract fields from Lease Image Pages", str(e), {}, "failed")
        print(f"Error during LLM extraction for {filename}: {e}")
        return LeaseDocData().model_dump()
