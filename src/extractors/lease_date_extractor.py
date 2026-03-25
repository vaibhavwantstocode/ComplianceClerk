import re
import json
import ollama
from src.audit.logger import log_llm_interaction
from src.extractors.dnr_extractor import extract_text_from_page
from config import OLLAMA_VISION_MODEL

def extract_lease_start_date(filename: str, page_image) -> str:
    """
    Extracts the 'Printed On' date or generic date from the e-Challan text (via Tesseract).
    Falls back to Qwen if regex fails.
    """
    page_text = extract_text_from_page(page_image)
    
    if page_text:
        patterns = [
            r"(?:printed\s*on|dated|date)\s*:?\s*(\d{2}[-/]\d{2}[-/]\d{4})",
            r"(\d{2}[-/]\d{2}[-/]\d{4})"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                # Log the successful regex execution just like any other extraction
                log_llm_interaction(filename, "LEASE_DATE_EXTRACTION", f"Regex pattern: {pattern}", page_text[:500], {"lease_start": date_str}, "success")
                return date_str
                
        log_llm_interaction(filename, "LEASE_DATE_EXTRACTION", f"Regex patterns failed", page_text[:500], {}, "failed")

    # Qwen fallback
    return qwen_fallback_echallan_date(filename, page_image)

def qwen_fallback_echallan_date(filename: str, page_image) -> str:
    prompt = """You are extracting a date from a structured table.

TASK:
Find the field "Printed On" and extract ONLY the date (ignore time).

INSTRUCTIONS:
- Format is usually DD/MM/YYYY HH:MM:SS
- Return only the date part (DD/MM/YYYY)

OUTPUT FORMAT (STRICT JSON ONLY):
{
  "lease_start": ""
}"""

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
        if date_str:
            log_llm_interaction(filename, "LEASE_DATE_EXTRACTION_FALLBACK", prompt, raw_text, {"lease_start": date_str}, "success")
            return date_str
    except Exception as e:
        log_llm_interaction(filename, "LEASE_DATE_EXTRACTION_FALLBACK", prompt, str(e), {}, "failed")
        
    return None
