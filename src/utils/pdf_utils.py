import fitz  # PyMuPDF
from pathlib import Path

def extract_text_from_pdf(pdf_path: str | Path, start_page: int = 0, end_page: int = None) -> list[str]:
    """
    Extracts text from a PDF, page by page.
    Returns a list of strings, where each string is the text of a page.
    """
    doc = fitz.open(pdf_path)
    pages_text = []
    
    if end_page is None:
        end_page = len(doc)
        
    for i in range(start_page, min(end_page, len(doc))):
        page = doc[i]
        pages_text.append(page.get_text())
        
    return pages_text

def get_pdf_page_count(pdf_path: str | Path) -> int:
    """Returns the total number of pages in the PDF."""
    with fitz.open(pdf_path) as doc:
        return len(doc)

def get_page_as_image(pdf_path: str | Path, page_num: int = 0) -> bytes:
    """
    Renders a specific PDF page as an image (for Gemini Vision).
    Returns the image data in bytes (PNG format).
    """
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better resolution
    return pix.tobytes("png")
