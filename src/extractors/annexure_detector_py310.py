import json
import re
import sys

import fitz
import numpy as np


def _collect_lines_from_legacy_ocr(result) -> list[str]:
    lines = []
    if result and isinstance(result, list) and result[0]:
        for row in result[0]:
            if len(row) >= 2 and isinstance(row[1], (list, tuple)) and row[1]:
                lines.append(str(row[1][0]))
    return lines


def _collect_lines_from_predict(result) -> list[str]:
    lines = []
    if not result:
        return lines

    for item in result:
        if isinstance(item, dict):
            rec_texts = item.get("rec_texts")
            if isinstance(rec_texts, list):
                lines.extend([str(x) for x in rec_texts if x])

    if not lines:
        # Last-resort parsing for unknown structures.
        text_blob = str(result)
        import re as _re
        for match in _re.findall(r"'rec_texts':\s*\[(.*?)\]", text_blob):
            for token in match.split(","):
                token = token.strip().strip("'\"")
                if token:
                    lines.append(token)
    return lines


def _run_ocr_lines(ocr, img) -> list[str]:
    try:
        return _collect_lines_from_legacy_ocr(ocr.ocr(img, cls=True))
    except TypeError:
        # PaddleOCR v3: use predict API
        return _collect_lines_from_predict(ocr.predict(img))


def _crop_top_quarter(img: np.ndarray) -> np.ndarray:
    height = img.shape[0]
    top = max(1, int(height * 0.25))
    return img[:top, :, :]


def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "error": "Missing pdf path argument."}))
        return 1

    pdf_path = sys.argv[1]

    try:
        from paddleocr import PaddleOCR
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"PaddleOCR import failed: {exc}"}))
        return 0

    pattern = re.compile(r"annexure\s*[-–]?\s*i", re.IGNORECASE)

    try:
        ocr = PaddleOCR(use_angle_cls=True, lang="en")
        with fitz.open(pdf_path) as doc:
            total = len(doc)
            start_idx = 29
            end_idx = 39

            if total <= start_idx:
                print(json.dumps({"ok": False, "annexure_page_index": -1, "error": "Document has fewer than 30 pages."}))
                return 0

            end_idx = min(end_idx, total - 1)

            for i in range(start_idx, end_idx + 1):
                page = doc[i]
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
                top_img = _crop_top_quarter(img)
                lines = _run_ocr_lines(ocr, top_img)

                text = " ".join(lines).lower()
                if pattern.search(text):
                    print(
                        json.dumps(
                            {
                                "ok": True,
                                "annexure_page_index": i,
                                "page_index": i,
                                "confidence": 1.0,
                                "method": "paddleocr_py310_top25_range30_40",
                            }
                        )
                    )
                    return 0

            print(json.dumps({"ok": False, "annexure_page_index": -1, "error": "Annexure-I not found in pages 30-40 top 25%."}))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "annexure_page_index": -1, "error": str(exc)}))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
