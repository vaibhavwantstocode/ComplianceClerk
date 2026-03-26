import json
from pathlib import Path

from config import OUTPUT_DIR, SAMPLE_PDFS_DIR
from src.extractors.lease_extractor_paddle import process_lease_document_with_paddle
from src.parsers.classifier import classify_document
from src.utils.pdf_utils import extract_text_from_pdf, get_pdf_page_count


def save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def main() -> None:
    out_dir = OUTPUT_DIR / "stepwise_json" / "lease_docs"
    out_dir.mkdir(parents=True, exist_ok=True)

    lease_pdfs = []
    for pdf_file in sorted(SAMPLE_PDFS_DIR.glob("*.pdf")):
        texts = extract_text_from_pdf(str(pdf_file))
        first = texts[0] if texts else ""
        pages = get_pdf_page_count(pdf_file)
        if classify_document(first, pages) == "LEASE_DOC":
            lease_pdfs.append(pdf_file)

    for pdf_file in lease_pdfs:
        print(f"[LEASE_PADDLE] {pdf_file.name}")
        payload = process_lease_document_with_paddle(str(pdf_file))
        save_json(
            out_dir / f"{pdf_file.stem}.lease_paddle.json",
            {
                "file": pdf_file.name,
                "step": "LEASE_PADDLE_EXTRACTION",
                "annexure_page_index": payload.get("annexure_page_index", -1),
                "ok": payload.get("ok", False),
                "error": payload.get("error", ""),
                "data": payload.get("data", {}),
            },
        )


if __name__ == "__main__":
    main()
