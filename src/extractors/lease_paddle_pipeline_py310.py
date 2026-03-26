import json
import re
import sys
from typing import Any

import fitz
import numpy as np
from PIL import Image
from pdf2image import convert_from_path
from paddleocr import PaddleOCR, PPStructure


def pdf_to_images(pdf_path: str):
    try:
        return convert_from_path(pdf_path, dpi=220)
    except Exception:
        pages = []
        with fitz.open(pdf_path) as doc:
            for page in doc:
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                mode = "RGB" if pix.n >= 3 else "L"
                img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
                pages.append(img)
        return pages


def _to_cv(image) -> np.ndarray:
    arr = np.array(image)
    if arr.ndim == 2:
        arr = np.stack([arr, arr, arr], axis=-1)
    return arr


def find_annexure_page(images) -> int:
    ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
    pattern = re.compile(r"annexure\s*[-–]?\s*(?:i|1)", re.IGNORECASE)

    start_page = 31
    end_page = 38
    total = len(images)
    start_idx = max(0, start_page - 1)
    end_idx = min(total - 1, end_page - 1)

    if start_idx > end_idx:
        return -1

    for idx in range(start_idx, end_idx + 1):
        img = _to_cv(images[idx])
        h = img.shape[0]
        top = max(1, int(h * 0.25))
        crop = img[:top, :, :]
        result = ocr.ocr(crop, cls=True)

        lines = []
        if result and isinstance(result, list) and result[0]:
            for row in result[0]:
                if len(row) >= 2 and isinstance(row[1], (list, tuple)) and row[1]:
                    lines.append(str(row[1][0]))

        text = " ".join(lines).lower()
        if "annexure" in text or pattern.search(text):
            return idx

    return -1


def extract_table(image) -> dict[str, Any]:
    table_engine = PPStructure(layout=True, table=True, ocr=True, show_log=False)
    cv_img = _to_cv(image)
    result = table_engine(cv_img)

    html_blobs = []
    text_blobs = []
    for block in result:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "table":
            html = block.get("res", {}).get("html", "") if isinstance(block.get("res"), dict) else ""
            if html:
                html_blobs.append(html)
        block_text = block.get("res", {}).get("text", "") if isinstance(block.get("res"), dict) else ""
        if block_text:
            text_blobs.append(str(block_text))

    return {
        "raw": result,
        "html": "\n".join(html_blobs),
        "text": "\n".join(text_blobs),
    }


def _extract_from_table_like_text(text: str) -> dict[str, str]:
    out = {
        "village": "",
        "survey_no": "",
        "district": "",
        "taluka": "",
        "area": "",
        "lease_deed_no": "",
        "date": "",
    }

    lines = [ln.strip() for ln in re.split(r"\r?\n", text or "") if ln.strip()]

    # Try header-driven row parsing first
    joined = "\n".join(lines)

    # Survey number with optional subdivision
    m = re.search(r"\b(\d{1,4}\s*[/-]?\s*[a-z]{0,2}\s*\d{0,2})\b", joined, re.IGNORECASE)
    if m:
        out["survey_no"] = m.group(1)

    # Area in sqm
    m = re.search(r"\b(\d{2,7}(?:\.\d{1,2})?)\b\s*(?:sq\.?\s*m|sqm|sq\.m\.?|ચો\.?મી\.?)", joined, re.IGNORECASE)
    if m:
        out["area"] = m.group(1)

    # Lease deed no from DNR-like pattern
    m = re.search(r"\b(\d{2,5})\s*/\s*(20\d{2})\b", joined)
    if m:
        out["lease_deed_no"] = f"{m.group(1)}/{m.group(2)}"

    # Date
    m = re.search(r"\b(\d{2}[/-]\d{2}[/-]\d{4})\b", joined)
    if m:
        out["date"] = m.group(1)

    # Column-like labels
    for ln in lines:
        low = ln.lower()
        if not out["district"] and "district" in low:
            out["district"] = re.sub(r"(?i).*district\s*[:\-]?\s*", "", ln).strip()
        if not out["taluka"] and ("taluka" in low or "tehsil" in low):
            out["taluka"] = re.sub(r"(?i).*(taluka|tehsil)\s*[:\-]?\s*", "", ln).strip()
        if not out["village"] and "village" in low:
            out["village"] = re.sub(r"(?i).*village\s*[:\-]?\s*", "", ln).strip()

    return out


def _extract_from_full_ocr_text(image) -> dict[str, str]:
    ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
    cv_img = _to_cv(image)
    result = ocr.ocr(cv_img, cls=True)
    lines = []
    if result and isinstance(result, list) and result[0]:
        for row in result[0]:
            if len(row) >= 2 and isinstance(row[1], (list, tuple)) and row[1]:
                lines.append(str(row[1][0]))
    text = "\n".join(lines)
    return _extract_from_table_like_text(text)


def normalize(data: dict[str, str]) -> dict[str, str]:
    def clean(v: str) -> str:
        if v is None:
            return ""
        s = str(v).strip()
        return "" if s.lower() == "null" else s

    out = {k: clean(v) for k, v in data.items()}

    # survey_no normalization, e.g. "251 p2" -> "251/p2"
    s = out.get("survey_no", "")
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"^(\d+)([a-z]\d+)$", r"\1/\2", s, flags=re.IGNORECASE)
    s = s.replace("-", "/") if re.match(r"^\d+-[a-z]\d+$", s, flags=re.IGNORECASE) else s
    out["survey_no"] = s

    # numeric area only
    am = re.search(r"(\d+(?:\.\d+)?)", out.get("area", ""))
    out["area"] = am.group(1) if am else out.get("area", "")

    # remove noisy separators in text fields
    for key in ["village", "district", "taluka"]:
        out[key] = re.sub(r"\s+", " ", out.get(key, "")).strip(" :-|,")

    return out


def parse_fields(table_payload: dict[str, Any], image) -> dict[str, str]:
    from_table = _extract_from_table_like_text("\n".join([table_payload.get("html", ""), table_payload.get("text", "")]))

    # fallback from full-page OCR if missing critical values
    critical = ["village", "survey_no", "area", "lease_deed_no", "date"]
    if any(not from_table.get(k, "").strip() for k in critical):
        fallback = _extract_from_full_ocr_text(image)
        merged = dict(from_table)
        for key, val in fallback.items():
            if not merged.get(key):
                merged[key] = val
        return normalize(merged)

    return normalize(from_table)


def extract_lease_pdf(pdf_path: str) -> dict[str, Any]:
    images = pdf_to_images(pdf_path)
    annexure_idx = find_annexure_page(images)

    result = {
        "village": "",
        "survey_no": "",
        "district": "",
        "taluka": "",
        "area": "",
        "lease_deed_no": "",
        "date": "",
    }

    if annexure_idx < 0:
        return {
            "ok": False,
            "annexure_page_index": -1,
            "data": result,
            "error": "Annexure-I not found in pages 31-38 top 25%.",
        }

    page_img = images[annexure_idx]
    table_payload = extract_table(page_img)
    result = parse_fields(table_payload, page_img)

    return {
        "ok": True,
        "annexure_page_index": annexure_idx + 1,
        "data": result,
    }


def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "error": "Missing pdf path"}))
        return 1

    pdf_path = sys.argv[1]
    try:
        payload = extract_lease_pdf(pdf_path)
        print(json.dumps(payload, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc), "data": {
            "village": "",
            "survey_no": "",
            "district": "",
            "taluka": "",
            "area": "",
            "lease_deed_no": "",
            "date": "",
        }}))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
