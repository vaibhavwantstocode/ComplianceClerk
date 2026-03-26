import json
from pathlib import Path

from config import SAMPLE_PDFS_DIR, OUTPUT_DIR
from src.utils.pdf_utils import extract_text_from_pdf, get_pdf_page_count, get_page_as_image
from src.parsers.classifier import classify_document
from src.extractors.annexure_detector import detect_annexure_page
from src.extractors.na_extractor import process_na_order_with_llm
from src.extractors.lease_extractor_llm import process_lease_document_with_llm


def ensure_dirs() -> dict:
    base = OUTPUT_DIR / "stepwise_json"
    na_dir = base / "na_orders"
    lease_dir = base / "lease_docs"
    base.mkdir(parents=True, exist_ok=True)
    na_dir.mkdir(parents=True, exist_ok=True)
    lease_dir.mkdir(parents=True, exist_ok=True)
    return {"base": base, "na": na_dir, "lease": lease_dir}


def clean_record(data: dict, keys: list[str]) -> dict:
    out = {}
    for key in keys:
        value = data.get(key, "") if isinstance(data, dict) else ""
        out[key] = str(value).strip() if value is not None else ""
    return out


def save_json(path: Path, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def run_na_order(pdf_file: Path, na_dir: Path) -> dict:
    img_bytes = get_page_as_image(pdf_file, 0)
    raw = process_na_order_with_llm(pdf_file.name, img_bytes)
    data = clean_record(raw, ["district", "taluka", "village", "survey_no", "area_na", "dated", "na_order_no"])
    payload = {
        "file": pdf_file.name,
        "step": "NA_ORDER",
        "data": data,
    }
    save_json(na_dir / f"{pdf_file.stem}.na.json", payload)
    return payload


def run_lease_steps(pdf_file: Path, lease_dir: Path) -> dict:
    detect_meta = detect_annexure_page(str(pdf_file))
    annexure_page = int(detect_meta.get("page_index", 0))
    annexure_img = get_page_as_image(pdf_file, annexure_page)

    lease_raw = process_lease_document_with_llm(pdf_file.name, annexure_img)
    lease_data = clean_record(lease_raw, ["district", "taluka", "village", "survey_no", "lease_area", "lease_doc_no", "lease_start"])
    lease_payload = {
        "file": pdf_file.name,
        "step": "LEASE_DOC",
        "annexure_detection": detect_meta,
        "data": lease_data,
    }
    save_json(lease_dir / f"{pdf_file.stem}.lease.json", lease_payload)

    return lease_payload


def main() -> None:
    dirs = ensure_dirs()

    pdfs = sorted(SAMPLE_PDFS_DIR.glob("*.pdf"))
    na_results = []
    lease_results = []

    for pdf_file in pdfs:
        texts = extract_text_from_pdf(str(pdf_file))
        first_page_text = texts[0] if texts else ""
        num_pages = get_pdf_page_count(pdf_file)
        doc_type = classify_document(first_page_text, num_pages)

        if doc_type == "NA_ORDER":
            print(f"[NA_ORDER] {pdf_file.name}")
            na_results.append(run_na_order(pdf_file, dirs["na"]))
        elif doc_type == "LEASE_DOC":
            print(f"[LEASE_DOC] {pdf_file.name}")
            lease_results.append(run_lease_steps(pdf_file, dirs["lease"]))

    summary = {
        "na_count": len(na_results),
        "lease_count": len(lease_results),
        "output_dir": str(dirs["base"]),
    }
    save_json(dirs["base"] / "summary.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
