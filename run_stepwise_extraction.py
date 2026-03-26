import json
from pathlib import Path
import io
from PIL import Image

from config import SAMPLE_PDFS_DIR, OUTPUT_DIR
from src.utils.pdf_utils import extract_text_from_pdf, get_pdf_page_count, get_page_as_image
from src.parsers.classifier import classify_document
from src.parsers.page_selector import get_lease_image_indices
from src.extractors.na_extractor import process_na_order_with_llm
from src.extractors.lease_extractor_llm import process_lease_document_with_llm
from src.extractors.lease_date_extractor import extract_lease_start_date
from src.extractors.dnr_extractor import process_dnr_extraction


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
    data = clean_record(raw, ["village", "survey_no", "district", "area_na", "date", "na_order_no"])
    payload = {
        "file": pdf_file.name,
        "step": "NA_ORDER",
        "data": data,
    }
    save_json(na_dir / f"{pdf_file.stem}.na.json", payload)
    return payload


def run_lease_steps(pdf_file: Path, lease_dir: Path) -> dict:
    total_pages = get_pdf_page_count(pdf_file)

    # Step A: Annexure-I
    indices = get_lease_image_indices(total_pages)
    annexure_imgs = {}
    for i in indices:
        if i >= total_pages:
            continue
        if i >= max(0, total_pages - 15):
            annexure_imgs[f"page_{i}"] = get_page_as_image(pdf_file, i)

    annexure_raw = process_lease_document_with_llm(pdf_file.name, annexure_imgs)
    annexure_data = clean_record(annexure_raw, ["village", "survey_no", "district", "lease_area"])
    annexure_payload = {
        "file": pdf_file.name,
        "step": "LEASE_ANNEXURE",
        "data": annexure_data,
    }
    save_json(lease_dir / f"{pdf_file.stem}.annexure.json", annexure_payload)

    # Step B: Lease Start (e-Challan)
    lease_start = ""
    max_scan = min(total_pages, 8)
    for i in range(max_scan):
        page_bytes = get_page_as_image(pdf_file, i)
        pil_img = Image.open(io.BytesIO(page_bytes)).convert("RGB")
        candidate = extract_lease_start_date(pdf_file.name, pil_img)
        if candidate:
            lease_start = candidate
            break

    lease_start_payload = {
        "file": pdf_file.name,
        "step": "LEASE_START",
        "data": {
            "lease_start": lease_start,
        },
    }
    save_json(lease_dir / f"{pdf_file.stem}.lease_start.json", lease_start_payload)

    # Step C: DNR / Lease Doc Number
    lease_doc_no = process_dnr_extraction(str(pdf_file))
    dnr_payload = {
        "file": pdf_file.name,
        "step": "LEASE_DNR",
        "data": {
            "lease_doc_no": str(lease_doc_no).strip() if lease_doc_no else "",
        },
    }
    save_json(lease_dir / f"{pdf_file.stem}.dnr.json", dnr_payload)

    # Combined lease output from stepwise extraction
    merged_payload = {
        "file": pdf_file.name,
        "step": "LEASE_COMBINED",
        "data": {
            "village": annexure_data.get("village", ""),
            "survey_no": annexure_data.get("survey_no", ""),
            "district": annexure_data.get("district", ""),
            "lease_area": annexure_data.get("lease_area", ""),
            "lease_start": lease_start,
            "lease_doc_no": dnr_payload["data"]["lease_doc_no"],
        },
    }
    save_json(lease_dir / f"{pdf_file.stem}.combined.json", merged_payload)

    return {
        "annexure": annexure_payload,
        "lease_start": lease_start_payload,
        "dnr": dnr_payload,
        "combined": merged_payload,
    }


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
