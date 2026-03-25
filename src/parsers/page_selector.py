import re

def get_lease_doc_pages(all_pages_text: list[str]) -> dict:
    # Used for text-based fallback, but primarily we use image indices now
    return {}

def get_lease_image_indices(total_pages: int) -> list[int]:
    """
    Since Lease Documents are scanned images without text, we send a subset 
    of pages to Gemini to find eChallan (start), DNR stamp, and Annexure-I.
    We grab the first 3 pages and the last 15 pages to cover these areas.
    """
    indices = [0, 1, 2]
    # Add the last 15 pages, avoiding duplicates
    last_pages = list(range(max(3, total_pages - 15), total_pages))
    return sorted(list(set(indices + last_pages)))

def get_na_image_indices(total_pages: int) -> list[int]:
    """
    NA Orders typically contain relevant data on the first few pages, 
    but they are short (1-3 pages usually). We just send all pages.
    """
    return list(range(total_pages))

def get_na_order_pages(all_pages_text: list[str]) -> str:
    """
    Fallback for text-based processing.
    """
    if not all_pages_text:
        return ""
    return "\n".join(all_pages_text)
