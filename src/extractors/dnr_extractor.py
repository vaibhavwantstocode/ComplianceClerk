import re
import os
import json
import ollama
from collections import Counter
from src.audit.logger import log_llm_interaction
from config import OLLAMA_VISION_MODEL

try:
    from pdf2image import convert_from_path
except ImportError:
    pass

try:
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

def extract_text_from_page(image):
    if not OCR_AVAILABLE:
        return ""
    try:
        return pytesseract.image_to_string(image).lower()
    except Exception:
        return ""

def extract_dnr_candidates(text):
    candidates = []
    if "dnr" in text:
        # handle split digits
        text = text.replace(" ", "")
        
        # remove noise
        cleaned = re.sub(r"[^\d\s\w]", " ", text)
        cleaned = re.sub(r"\s+", " ", cleaned)
        
        # find patterns like number + year
        matches = re.findall(r"(\d{2,5})\s*(20\d{2})", cleaned)
        for num, year in matches:
            if 2000 <= int(year) <= 2030:
                candidates.append(f"{num}/{year}")
                
    return candidates

def process_dnr_extraction(pdf_path: str) -> str:
    """
    Extracts the lease doc number using deterministic DNR scanning.
    Scans first 5, last 5, and some random middle pages.
    Uses Tesseract and majority voting.
    """
    if not OCR_AVAILABLE:
        print("WARNING: Tesseract not found. Will fallback to Qwen (if applicable).")

    try:
        from pdf2image.pdf2image import pdfinfo_from_path
        info = pdfinfo_from_path(pdf_path)
        total_pages = int(info["Pages"])
    except Exception:
        # Fallback if pdfinfo fails
        import fitz
        with fitz.open(pdf_path) as doc:
            total_pages = len(doc)
            
    # Page selection logic (1-indexed for pdf2image)
    pages_to_scan = set()
    for i in range(1, min(6, total_pages + 1)):
        pages_to_scan.add(i)
        
    for i in range(max(1, total_pages - 4), total_pages + 1):
        pages_to_scan.add(i)
        
    if total_pages > 10:
        pages_to_scan.add(total_pages // 2)
        pages_to_scan.add((total_pages // 2) + 1)
        
    pages_to_scan = sorted(list(pages_to_scan))
    
    filename = os.path.basename(pdf_path)
    all_candidates = []
    
    # Store first page image for fallback
    first_page_image = None

    try:
        if OCR_AVAILABLE:
            for page_num in pages_to_scan:
                # We convert just the specific page to save memory
                pages = convert_from_path(pdf_path, first_page=page_num, last_page=page_num)
                for page in pages:
                    if page_num == 1 and first_page_image is None:
                        first_page_image = page
                    
                    text = extract_text_from_page(page)
                    candidates = extract_dnr_candidates(text)
                    all_candidates.extend(candidates)
                    
        lease_doc_no = None
        if all_candidates:
            lease_doc_no = Counter(all_candidates).most_common(1)[0][0]
            log_llm_interaction(filename, "DNR_EXTRACTION", f"Pages scanned: {pages_to_scan}", str(all_candidates), {"lease_doc_no": lease_doc_no}, "success")
            return lease_doc_no
            
        # Fallback to Qwen
        if first_page_image is None:
            # Try to grab just page 1 if not previously loaded
            pages = convert_from_path(pdf_path, first_page=1, last_page=1)
            first_page_image = pages[0]
            
        return qwen_fallback_dnr(filename, first_page_image)
        
    except Exception as e:
        log_llm_interaction(filename, "DNR_EXTRACTION", f"Pages scanned: {pages_to_scan}", str(e), {}, "failed")
        return None

def qwen_fallback_dnr(filename: str, page_image) -> str:
    prompt = """You are extracting a document registration number (DNR stamp) from a document.

Find the document number which is typically in the format of NUMBER/YEAR (e.g., 56/2021).
Return ONLY the document number.

OUTPUT FORMAT (STRICT JSON ONLY):
{
  "lease_doc_no": ""
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
        doc_no = parsed.get("lease_doc_no")
        if doc_no:
            log_llm_interaction(filename, "DNR_EXTRACTION_FALLBACK", prompt, raw_text, {"lease_doc_no": doc_no}, "success")
            return doc_no
    except Exception as e:
        log_llm_interaction(filename, "DNR_EXTRACTION_FALLBACK", prompt, str(e), {}, "failed")
        
    return None
