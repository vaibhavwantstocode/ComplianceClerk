import json
import ollama
from src.audit.logger import log_llm_interaction
from config import OLLAMA_VISION_MODEL

def extract_lease_start_date(filename: str, page_image) -> str:
    """
    Extracts the 'Printed On' date or generic date from the e-Challan text directly via Qwen vision.
    Runs strictly on Qwen LLM bypassing regex.
    """
    prompt = """You are extracting a date from a structured table. TASK: Find the field "Printed On" and extract ONLY the date (ignore time). INSTRUCTIONS: - Format is usually DD/MM/YYYY HH:MM:SS - Return only the date part (DD/MM/YYYY) OUTPUT: { "lease_start": "" }"""

    import io
    img_byte_arr = io.BytesIO()
    page_image.save(img_byte_arr, format='JPEG')
    img_bytes = img_byte_arr.getvalue()
    
    try:
        response = ollama.chat(
            model=OLLAMA_VISION_MODEL,
            messages=[{
                "role": "user",
                "content": prompt,
                "images": [img_bytes]
            }],
            format="json",
            options={"temperature": 0.0}
        )
        
        raw_text = response["message"]["content"]
        
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[-1].split("```")[0].strip()    
        elif "```" in raw_text:
            raw_text = raw_text.split("```")[-1].split("```")[0].strip() 

        parsed = json.loads(raw_text)
        date_str = parsed.get("lease_start")
        # Ensure we don't crash if it returns missing value
        if date_str:
            log_llm_interaction(filename, "LEASE_DATE_EXTRACTION", prompt, raw_text, {"lease_start": date_str}, "success")
            return date_str
    except Exception as e:
        log_llm_interaction(filename, "LEASE_DATE_EXTRACTION", prompt, str(e), {}, "failed")
        
    return None
