import os
import json
import fitz
import pandas as pd
from pathlib import Path

from config import SAMPLE_PDFS_DIR, OUTPUT_DIR
from src.utils.pdf_utils import extract_text_from_pdf, get_pdf_page_count, get_page_as_image
from src.parsers.classifier import classify_document
from src.extractors.annexure_detector import detect_annexure_page
from src.extractors.lease_extractor_llm import process_lease_document_with_llm
from src.extractors.na_extractor import process_na_order_with_llm
from src.utils.normalizer import combine_and_normalize, generate_match_key


def _clean_value(value):
    if value is None:
        return ""
    sval = str(value).strip()
    return "" if sval.lower() == "null" else sval


def _save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

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

    stepwise_base = OUTPUT_DIR / "stepwise_json"
    stepwise_na_dir = stepwise_base / "na_orders"
    stepwise_lease_dir = stepwise_base / "lease_docs"

    # 2. Extract Data from NA Orders (Gemini call #1 per pair)
    print("\n--- Processing NA Orders ---")
    for file in na_orders:
        try:
            print(f"Extracting NA: {file.name}")
            img_bytes = get_page_as_image(file, 0)
            data = process_na_order_with_llm(file.name, img_bytes)
            data['_filename'] = file.name
            extracted_na_data.append(data)

            _save_json(
                stepwise_na_dir / f"{file.stem}.na.json",
                {"file": file.name, "step": "NA_ORDER", "data": {k: _clean_value(v) for k, v in data.items() if not k.startswith('_')}},
            )
        except Exception as e:
            print(f"Error processing {file.name}: {e}")

    # 3. Extract Data from Lease Documents (Gemini call #2 per pair)
    print("\n--- Processing Lease Documents ---")
    for file in lease_docs:
        try:
            print(f"Extracting Lease: {file.name}")
            detect_meta = detect_annexure_page(str(file))
            annexure_index = int(detect_meta.get("page_index", 0))

            img_bytes = get_page_as_image(file, annexure_index)
            data = process_lease_document_with_llm(file.name, img_bytes)

            data['_filename'] = file.name
            data['_annexure_page_index'] = annexure_index
            data['_annexure_detection_method'] = detect_meta.get("method", "")
            extracted_lease_data.append(data)

            _save_json(
                stepwise_lease_dir / f"{file.stem}.lease.json",
                {
                    "file": file.name,
                    "step": "LEASE_DOC",
                    "annexure_detection": detect_meta,
                    "data": {k: _clean_value(v) for k, v in data.items() if not k.startswith('_')},
                },
            )
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
        out_path = OUTPUT_DIR / "matched_records.xlsx"
        df.to_excel(out_path, index=False)
        print(f"\nSuccessfully generated Excel output at: {out_path}")
    else:
        print("\nNo records extracted to export.")

if __name__ == "__main__":
    process_all_documents()
