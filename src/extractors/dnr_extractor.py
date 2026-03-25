import json
import os
from collections import Counter
import ollama
from src.audit.logger import log_llm_interaction
from config import OLLAMA_VISION_MODEL

try:
    from pdf2image import convert_from_path
except ImportError:
    pass

def process_dnr_extraction(pdf_path: str) -> str:
    """
    Extracts the lease doc number using Qwen on multiple pages.
    """
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
    
    import io
    images = []
    try:
        for page_num in pages_to_scan:
            pages = convert_from_path(pdf_path, first_page=page_num, last_page=page_num)
            for page in pages:
                img_byte_arr = io.BytesIO()
                page.save(img_byte_arr, format='JPEG')
                images.append(img_byte_arr.getvalue())
                
        # if too many images, Qwen might struggle or run out of memory, but let's pass them all
        # or maybe we should pass 3 images max to avoid token limit? 
        # The prompt says: "You will be given multiple page images from the same document."
        # We will pass up to 5 images to keep it safe.
        max_images_to_pass = min(len(images), 5)
        images = images[:max_images_to_pass]
        return qwen_extract_dnr(filename, images)
    except Exception as e:
        log_llm_interaction(filename, "DNR_EXTRACTION", f"Pages scanned: {pages_to_scan[:5]}", str(e), {}, "failed")
        return None

def qwen_extract_dnr(filename: str, images: list) -> str:
    prompt = """You are extracting the Lease Deed Document Number from scanned document pages.

TASK:
Extract the Lease Deed Document Number from the DNR stamp.

CONTEXT:
- The DNR stamp is a boxed structure located typically at the top-right area of the page.
- Inside the box:
  - The top contains the label "DNR"
  - The bottom row contains the year (e.g., 2026)
  - The middle row contains multiple numbers

MEANING OF NUMBERS:
- The FIRST number in the middle row is the document number (e.g., 141)
- The bottom number is the year (e.g., 2026)
- Other numbers (e.g., 35, 54) represent page numbering and MUST BE IGNORED

OUTPUT REQUIREMENT:
- Combine document number and year in the format:
  <document_number>/<year>

EXAMPLE:
- If document number = 141 and year = 2026
- Output → "141/2026"

INSTRUCTIONS:
- Use only the FIRST number from the middle row
- Ignore any other numbers in the box
- Do not include page numbers
- The year must be a 4-digit number (e.g., 2025, 2026)
- The document number is usually 2–5 digits

ROBUSTNESS:
- The same DNR stamp appears on multiple pages
- Some pages may have OCR noise or incorrect digits
- Identify the most consistent document number across all provided pages

INPUT:
You will be given multiple page images from the same document.

OUTPUT (STRICT JSON ONLY):
{
  "lease_doc_no": ""
}

First identify all candidate document numbers across pages.
Then select the most frequent valid pair."""

    try:
        response = ollama.chat(
            model=OLLAMA_VISION_MODEL,
            messages=[{
                "role": "user",
                "content": prompt,
                "images": images
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
            log_llm_interaction(filename, "DNR_EXTRACTION", prompt, raw_text, {"lease_doc_no": doc_no}, "success")
            return doc_no
    except Exception as e:
        log_llm_interaction(filename, "DNR_EXTRACTION", prompt, str(e), {}, "failed")
        
    return None
