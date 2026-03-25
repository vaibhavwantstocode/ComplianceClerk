def classify_document(first_page_text: str, num_pages: int) -> str:
    """
    Classifies a document based on its first page text and total page count.
    Returns 'LEASE_DOC', 'NA_ORDER', or 'UNKNOWN'.
    """
    text_lower = first_page_text.lower()
    
    if "challan" in text_lower or "lease deed" in text_lower:
        return "LEASE_DOC"
        
    if num_pages <= 5:
        return "NA_ORDER"
        
    return "UNKNOWN"
