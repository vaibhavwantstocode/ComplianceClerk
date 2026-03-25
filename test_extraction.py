import os
from pathlib import Path
import json

from config import SAMPLE_PDFS_DIR
from src.utils.pdf_utils import extract_text_from_pdf, get_pdf_page_count, get_page_as_image
from src.parsers.classifier import classify_document
from src.extractors.lease_extractor_llm import process_lease_document_with_llm
from src.extractors.na_extractor import process_na_order_with_llm
from src.utils.normalizer import combine_and_normalize

def test_extractors():
    print("--- Testing Extractor Pipeline ---")
    
    # Files to test (one Lease Deed, one NA Order)
    lease_file = SAMPLE_PDFS_DIR / "Rampura Mota S.No.- 251p2 Lease Deed No.- 141.pdf"
    na_file = SAMPLE_PDFS_DIR / "251-p2 FINAL ORDER.pdf"
    
    # 1. Test LEASE_DOC extraction
    print(f"\nTesting LEASE_DOC: {lease_file.name}")
    # Render required pages as images (e.g. Page 1 for eChallan/start date, Page 5 for Annexure, Page 1 for DNR)
    # *Note: For actual pipeline we will define logic to find the Annexure page dynamically, 
    # but for testing the LLM vision we will just send first few pages.
    try:
        lease_images = {
            "echallan": get_page_as_image(lease_file, 0),  # e-Challan page
            "annexure": get_page_as_image(lease_file, 14), # Annexure page (hardcoded index for this specific test doc if known, otherwise we just pass a few)
            "dnr": get_page_as_image(lease_file, 0)       # DNR stamp page
        }
        
        lease_data = process_lease_document_with_llm(lease_file.name, lease_images)
        print("Lease Data Extracted:")
        print(json.dumps(lease_data, indent=2))
        
    except Exception as e:
        print(f"Failed Lease test: {e}")

    # 2. Test NA_ORDER extraction
    print(f"\nTesting NA_ORDER: {na_file.name}")
    try:
        na_image = get_page_as_image(na_file, 0) # Page 1
        na_data = process_na_order_with_llm(na_file.name, na_image)
        print("NA Order Data Extracted:")
        print(json.dumps(na_data, indent=2))
        
        # 3. Test Normalization
        print("\n--- Testing Normalization ---")
        combined = combine_and_normalize(na_data, lease_data)
        print("Normalized Combined Record:")
        print(json.dumps(combined, indent=2))
        
    except Exception as e:
         print(f"Failed NA Order test: {e}")

if __name__ == "__main__":
    test_extractors()
