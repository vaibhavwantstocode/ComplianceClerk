def classify_document(first_page_text: str, num_pages: int) -> str:
    """
    Classifies a document primarily based on page count since
    most lease documents are scanned images without text layer.
    """
    text_lower = first_page_text.lower()
    
    if "challan" in text_lower or "lease deed" in text_lower:
        return "LEASE_DOC"
        
    if num_pages <= 5:
        return "NA_ORDER"
        
    # Fallback to LEASE_DOC for large scanned image PDFs
    if num_pages > 5:
        return "LEASE_DOC"
