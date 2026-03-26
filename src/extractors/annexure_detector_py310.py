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

    pattern = re.compile(r"annexure\s*[-:]?\s*i\b", re.IGNORECASE)

    try:
        ocr = PaddleOCR(use_angle_cls=True, lang="en")
        with fitz.open(pdf_path) as doc:
            best = None
            for i, page in enumerate(doc):
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
                lines = _run_ocr_lines(ocr, img)

                text = " ".join(lines)
                if pattern.search(text):
                    score = sum(1 for line in lines if "annexure" in line.lower())
                    candidate = {
                        "ok": True,
                        "page_index": i,
                        "confidence": float(score if score > 0 else 1),
                        "method": "paddleocr_py310",
                    }
                    if not best or candidate["confidence"] > best["confidence"]:
                        best = candidate

            if best:
                print(json.dumps(best))
            else:
                print(json.dumps({"ok": False, "error": "Annexure-I not found by PaddleOCR."}))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
