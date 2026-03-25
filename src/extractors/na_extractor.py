import json
from google import genai
from google.genai import types
from pydantic import ValidationError
from config import GEMINI_API_KEY, GEMINI_MODEL
from src.audit.logger import log_llm_interaction
from src.model.schemas import NAOrderData

def process_na_order_with_llm(filename: str, page_image: bytes) -> dict:
    """
    Uses Gemini Flash Vision to extract NA Order data from scanned Gujarati image page.
    Returns a dictionary matching NAOrderData schema.
    """
    if not GEMINI_API_KEY:
        print("WARNING: GEMINI_API_KEY not set. Returning empty NA Order data.")
        return NAOrderData().model_dump()

    client = genai.Client(api_key=GEMINI_API_KEY)

    contents = [
        "You are an expert Gujarati document extractor. Read this non-agricultural (NA) permission order.",
        "Extract the required fields and return strictly in JSON format. Translate dates to DD/MM/YYYY. Translate numbers to English numerals. If a field is not found, use null.",
        types.Part.from_bytes(data=page_image, mime_type='image/png')
    ]
            
    # Define JSON schema output
    response_schema = {
        "type": "OBJECT",
        "properties": {
            "district": {"type": "STRING"},
            "taluka": {"type": "STRING"},
            "village": {"type": "STRING"},
            "survey_no": {"type": "STRING"},
            "area_na": {"type": "STRING"},
            "date": {"type": "STRING"},
            "order_no": {"type": "STRING"}
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
        validated_data = NAOrderData(**parsed_json)
        
        # Audit Log
        log_llm_interaction(filename, "NA_ORDER_EXTRACTION", "Extract fields from NA Order Image", raw_text, validated_data.model_dump(), "success")
        
        return validated_data.model_dump()
        
    except Exception as e:
        log_llm_interaction(filename, "NA_ORDER_EXTRACTION", "Extract fields from NA Order Image", str(e), {}, "failed")
        print(f"Error during LLM extraction for NA Order {filename}: {e}")
        return NAOrderData().model_dump()
