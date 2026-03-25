import re
from src.audit.logger import log_llm_interaction
from src.extractors.dnr_extractor import extract_text_from_page

def extract_lease_start_date(filename: str, page_image) -> str:
    """
    Extracts the 'Printed On' date or generic date from the e-Challan text (via PaddleOCR).
    """
    page_text = extract_text_from_page(page_image)
    if not page_text:
        return None
        
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
    return None
