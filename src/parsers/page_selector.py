import re

def get_lease_doc_pages(all_pages_text: list[str]) -> dict:
    """
    Identifies specific pages of interest within a LEASE_DOC.
    Returns a dictionary with the page text or None for each category.
    """
    result = {
        "echallan_text": "",
        "annexure_text": None,
        "all_text": all_pages_text
    }
    
    # E-Challan is typically the first 1-2 pages
    result["echallan_text"] = "\n".join(all_pages_text[:2])
    
    # Detect Annexure-I using regex \bannexure\s*-\s*i\b
    annexure_pattern = re.compile(r"\bannexure\s*-\s*i\b", re.IGNORECASE)
    for text in all_pages_text:
        if annexure_pattern.search(text):
            result["annexure_text"] = text
            break
            
    return result

def get_na_order_pages(all_pages_text: list[str]) -> str:
    """
    Identifies specific pages of interest within an NA_ORDER.
    For NA_ORDER, we only care about the very first page.
    """
    if not all_pages_text:
        return ""
    return all_pages_text[0]
