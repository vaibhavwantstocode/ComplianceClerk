import re
import os
from collections import Counter
from src.audit.logger import log_llm_interaction

try:
    from pdf2image import convert_from_path
except ImportError:
    pass

try:
    from paddleocr import PaddleOCR
    # Initialize globally so we don't reload model each time
    OCR_ENGINE = PaddleOCR(use_angle_cls=True, lang='en')
except ImportError:
    OCR_ENGINE = None

def extract_text_from_page(image):
    if not OCR_ENGINE:
        return ""
    import numpy as np
    
    # PaddleOCR takes numpy arrays
    img_array = np.array(image)
    result = OCR_ENGINE.ocr(img_array, cls=True)
    if not result or not result[0]:
        return ""
    
    return " ".join([line[1][0] for line in result[0]]).lower()

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
    Uses PaddleOCR and majority voting.
    """
    if not OCR_ENGINE:
        print("WARNING: PaddleOCR not found. Returning empty DNR.")
        return None

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
    
    try:
        for page_num in pages_to_scan:
            # We convert just the specific page to save memory
            pages = convert_from_path(pdf_path, first_page=page_num, last_page=page_num)
            for page in pages:
                text = extract_text_from_page(page)
                candidates = extract_dnr_candidates(text)
                all_candidates.extend(candidates)
                
        lease_doc_no = None
        if all_candidates:
            lease_doc_no = Counter(all_candidates).most_common(1)[0][0]
            
        log_llm_interaction(filename, "DNR_EXTRACTION", f"Pages scanned: {pages_to_scan}", str(all_candidates), {"lease_doc_no": lease_doc_no}, "success")
        return lease_doc_no
        
    except Exception as e:
        log_llm_interaction(filename, "DNR_EXTRACTION", f"Pages scanned: {pages_to_scan}", str(e), {}, "failed")
        return None
