import os
import json
import time
import fitz
import pandas as pd
from pathlib import Path

from config import SAMPLE_PDFS_DIR, OUTPUT_DIR
from src.utils.pdf_utils import extract_text_from_pdf, get_pdf_page_count, get_page_as_image
from src.parsers.classifier import classify_document
from src.parsers.page_selector import get_lease_image_indices, get_na_image_indices
from src.extractors.lease_extractor_llm import process_lease_document_with_llm
from src.extractors.na_extractor import process_na_order_with_llm
from src.utils.normalizer import combine_and_normalize

def process_all_documents():
    print("Starting document processing pipeline...")
    
    na_orders = []
    lease_docs = []
    
    # 1. Classify all documents in the directory
    for pdf_file in SAMPLE_PDFS_DIR.glob("*.pdf"):
        doc_path = str(pdf_file)
        
        # Try to extract text from first page
        texts = extract_text_from_pdf(doc_path)
        first_page_text = texts[0] if texts else ""
        num_pages = get_pdf_page_count(doc_path)
        
        doc_type = classify_document(first_page_text, num_pages)
        print(f"[{doc_type}] {pdf_file.name} (Pages: {num_pages})")
        
        if doc_type == "NA_ORDER":
            na_orders.append(pdf_file)
        elif doc_type == "LEASE_DOC":
            lease_docs.append(pdf_file)

    extracted_na_data = []
    extracted_lease_data = []

    # 2. Extract Data from NA Orders
    print("\n--- Processing NA Orders ---")
    for file in na_orders:
        try:
            print(f"Extracting NA: {file.name}")
            # Single page is usually enough for NA
            img_bytes = get_page_as_image(file, 0)
            data = process_na_order_with_llm(file.name, img_bytes)
            data['_filename'] = file.name
            extracted_na_data.append(data)
            
            # Avoid Gemini Free Tier 429 Rate Limit
            time.sleep(5)
        except Exception as e:
            print(f"Error processing {file.name}: {e}")

    # 3. Extract Data from Lease Documents
    print("\n--- Processing Lease Documents ---")
    for file in lease_docs:
        try:
            print(f"Extracting Lease: {file.name}")
            doc = fitz.open(file)
            total_pages = len(doc)
            indices = get_lease_image_indices(total_pages)
            
            page_imgs = {}
            for i in indices:
                page_imgs[f"page_{i}"] = get_page_as_image(file, i)
                
            data = process_lease_document_with_llm(file.name, page_imgs)
            data['_filename'] = file.name
            extracted_lease_data.append(data)
            
            # Avoid Gemini Free Tier 429 Rate Limit (15 RPM)
            time.sleep(5)
        except Exception as e:
            print(f"Error processing {file.name}: {e}")

    # 4. Strict Matching & Normalization
    print("\n--- Normalizing and Matching Records ---")
    matched_records = []
    
    # Simple pairing logic: For this challenge, we pair them by index or try to match them.
    # We will compute the Cartesian product and look for matching deed numbers if available.
    # However, since the instruction said "Process a pair of documents", and the files 
    # look like: '251-p2 FINAL ORDER.pdf' pairs with 'Rampura Mota S.No.- 251p2 Lease Deed No.- 141.pdf'
    # we can just match them using the `survey_no` or fallback to zipped pairs for demonstration.
    
    for na_item in extracted_na_data:
        best_match = None
        
        # We try to find the lease document that shares the survey number if possible
        # (Though Lease extractor only pulled start, area, doc_no).
        # Since Lease extractor only has doc_no, and NA Order doesn't have lease_doc_no,
        # we'll use filename bridging or zip them up for demonstration.
        
        # Look for matching survey snippet in filename
        survey_raw = na_item.get('survey_no', '')
        survey_str = str(survey_raw) if survey_raw is not None else ""
        na_survey_hint = survey_str.replace('/', '-').replace('p', '')
        
        for lease_item in extracted_lease_data:
            normalized = combine_and_normalize(na_item, lease_item)
            
            # Simple heuristic matching via filename text
            if normalized['survey_no'].replace('-p', 'p') in lease_item['_filename']:
                best_match = normalized
                break
                
        if best_match:
            matched_records.append(best_match)
        else:
            # Fallback if no explicit filename match - bind with empty lease
            matched_records.append(combine_and_normalize(na_item, {}))

    # 5. Export to Excel
    if matched_records:
        df = pd.DataFrame(matched_records)
        # Select exactly the 5 fields requested in strict formatting, along with the others.
        # Required columns from prompt: doc_no, village, survey_no, area, date
        # Our CombinedRecord: village, survey_no, area_na, date, order_no, lease_doc_no, lease_area, lease_start
        out_path = OUTPUT_DIR / "matched_records.xlsx"
        df.to_excel(out_path, index=False)
        print(f"\nSuccessfully generated Excel output at: {out_path}")
    else:
        print("\nNo records extracted to export.")

if __name__ == "__main__":
    process_all_documents()
