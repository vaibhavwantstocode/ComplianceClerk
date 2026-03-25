import os
import json
import time
import fitz
import sqlite3
import pandas as pd
from pathlib import Path

from config import SAMPLE_PDFS_DIR, OUTPUT_DIR, AUDIT_DB_PATH
from src.utils.pdf_utils import extract_text_from_pdf, get_pdf_page_count, get_page_as_image
from src.parsers.classifier import classify_document
from src.parsers.page_selector import get_lease_image_indices, get_na_image_indices
from src.extractors.lease_extractor_llm import process_lease_document_with_llm
from src.extractors.na_extractor import process_na_order_with_llm
from src.extractors.dnr_extractor import process_dnr_extraction
from src.extractors.lease_date_extractor import extract_lease_start_date
from src.utils.normalizer import combine_and_normalize, generate_match_key

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
            # Add caching layer to bypass free-tier rate limits!
            conn = sqlite3.connect(AUDIT_DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT parsed FROM audit_logs WHERE doc_id=? AND status='success' ORDER BY timestamp DESC LIMIT 1", (file.name,))
            row = cursor.fetchone()
            conn.close()
            
            if row and row[0]:
                print(f"Using cached DB parse for NA Order: {file.name}")
                data = json.loads(row[0])
            else:
                img_bytes = get_page_as_image(file, 0)
                data = process_na_order_with_llm(file.name, img_bytes)
                
            data['_filename'] = file.name
            extracted_na_data.append(data)
        except Exception as e:
            print(f"Error processing {file.name}: {e}")

    # 3. Extract Data from Lease Documents
    print("\n--- Processing Lease Documents ---")
    for file in lease_docs:
        try:
            print(f"Extracting Lease: {file.name}")
            # Check DB Cache
            conn = sqlite3.connect(AUDIT_DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT parsed FROM audit_logs WHERE doc_id=? AND status='success' ORDER BY timestamp DESC LIMIT 1", (file.name,))
            row = cursor.fetchone()
            conn.close()
            
            if row and row[0]:
                print(f"Using cached DB parse for Lease Doc: {file.name}")
                data = json.loads(row[0])
            else:
                doc = fitz.open(file)
                total_pages = len(doc)
                
                # 1. Deterministic DNR (Majority Vote) - directly via PDF path
                lease_doc_no = process_dnr_extraction(str(file))
                
                # 2. Qwen logic for Annexure and Regex for e-Challan
                indices = get_lease_image_indices(total_pages)
                lease_start = None
                
                page_imgs = {}
                # Extract images using fitz directly
                for i in indices:
                    img_bytes = get_page_as_image(file, i)
                    page_imgs[f"page_{i}"] = img_bytes
                    
                    # Try getting lease_start from front pages if not found yet
                    if not lease_start and i < 5:
                        from PIL import Image
                        import io
                        pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                        lease_start = extract_lease_start_date(file.name, pil_img)
                        
                # 3. Pass all to Qwen (It only selects the first one currently for Annexure)
                # But since Annexure is generally at the end, we should pass only the last few pages to Qwen
                annexure_imgs = {k: v for k, v in page_imgs.items() if int(k.split("_")[1]) > total_pages - 15}
                
                data = process_lease_document_with_llm(file.name, annexure_imgs)
                
                # Inject deterministic findings into the Lease data struct
                if lease_doc_no:
                    data['lease_doc_no'] = lease_doc_no
                if lease_start:
                    data['lease_start'] = lease_start
                
            data['_filename'] = file.name
            extracted_lease_data.append(data)
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
        
        na_key = generate_match_key(na_item.get('village'), na_item.get('survey_no'), na_item.get('district'))
        
        for lease_item in extracted_lease_data:
            lease_key = generate_match_key(lease_item.get('village'), lease_item.get('survey_no'), lease_item.get('district'))
            
            # Match strictly on Village + Survey No + District composite key
            if na_key == lease_key and na_key != "--":
                best_match = lease_item
                break
                
        if best_match:
            matched_records.append(combine_and_normalize(na_item, best_match))
        else:
            matched_records.append(combine_and_normalize(na_item, {}))

    # 5. Export to Excel
    if matched_records:
        df = pd.DataFrame(matched_records)
        # Required columns from prompt: doc_no, village, survey_no, area, date
        # Our updated dict natively matches the requested 8 columns exactly
        out_path = OUTPUT_DIR / "matched_records.xlsx"
        df.to_excel(out_path, index=False)
        print(f"\nSuccessfully generated Excel output at: {out_path}")
    else:
        print("\nNo records extracted to export.")

if __name__ == "__main__":
    process_all_documents()
