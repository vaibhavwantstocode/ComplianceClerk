import json
from pathlib import Path

from config import OUTPUT_DIR, SAMPLE_PDFS_DIR
from src.parsers.classifier import classify_document
from src.utils.pdf_utils import extract_text_from_pdf, get_pdf_page_count, get_page_as_image
from src.extractors.na_extractor import process_na_order_with_llm


def _clean_value(value):
    if value is None:
        return ""
    sval = str(value).strip()
    return "" if sval.lower() == "null" else sval


def _save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def run_na_only() -> None:
    print("Starting NA-only extraction...")
    stepwise_na_dir = OUTPUT_DIR / "stepwise_json" / "na_orders"

    na_files = []
    for pdf_file in SAMPLE_PDFS_DIR.glob("*.pdf"):
        texts = extract_text_from_pdf(str(pdf_file))
        first_page_text = texts[0] if texts else ""
        num_pages = get_pdf_page_count(str(pdf_file))
        doc_type = classify_document(first_page_text, num_pages)
        if doc_type == "NA_ORDER":
            na_files.append(pdf_file)

    for file in na_files:
        print(f"Extracting NA: {file.name}")
        img_bytes = get_page_as_image(file, 0)
        data = process_na_order_with_llm(file.name, img_bytes)
        _save_json(
            stepwise_na_dir / f"{file.stem}.na.json",
            {
                "file": file.name,
                "step": "NA_ORDER",
                "data": {k: _clean_value(v) for k, v in data.items() if not k.startswith("_")},
            },
        )

    print("NA-only extraction complete.")


if __name__ == "__main__":
    run_na_only()
