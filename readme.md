# 🧾 Land Document Linking Pipeline (End-to-End)

## 🎯 Objective
Process a pair of documents:
* **Lease Deed + e-Challan (40–50 pages)**
* **NA Permission Order (2 pages, Gujarati)**

Extract required fields and generate a structured **Excel output** with strict matching.

---

## 🔥 STEP 0: INPUT
```text
Input: Two PDFs (unordered)
- One large document → Lease + e-Challan
- One small document → NA Order
```

---

## 🧠 STEP 1: DOCUMENT CLASSIFICATION
### Goal
Classify each PDF into `LEASE_DOC` or `NA_ORDER` using a header-based heuristic.

### Rules
```python
def classify_doc(text, num_pages):
    if 'challan' in text.lower() or 'lease deed' in text.lower():
        return 'LEASE_DOC'
    if num_pages <= 5:
        return 'NA_ORDER'
    return 'UNKNOWN'
```

---

## 🔍 STEP 2: PAGE IDENTIFICATION
### 📄 LEASE_DOC
1. **e-Challan Pages (Page 1–2):** Used for **Lease Start**
2. **Annexure-I Page:** Used for **Lease Area + matching fields**. Detected using regex `\bannexure\s*-\s*i\b`
3. **All Pages:** Used for **DNR stamp extraction (Doc No)**

### 📄 NA_ORDER
* Use **Page 1 only** (Contains all required fields).

---

## 📊 STEP 3: FIELD EXTRACTION & 🤖 STEP 6: LLM INTEGRATION

### 📄 FROM NA_ORDER (via Gemini 3 Flash Vision API)
Instead of traditional OCR (Tesseract), Page 1 is converted to an image and passed directly to Gemini 3 Flash.
* **Fields:** Village, Survey No. (with subdivision), Area in NA Order, Dated, NA Order No., District, Taluka.

### 📄 FROM LEASE_DOC (Deterministic/Regex)
* **Lease Start:** e-Challan pages `r'printed on[:\s]*([\d/:-]+)'`
* **Lease Area:** Annexure-I table `Area (SQM)`
* **Doc No:** Multi-page DNR stamp extraction with majority voting.

---

## 🔧 STEP 4: NORMALIZATION & 🔗 STEP 5: STRICT MATCHING
* **Survey Format:** `251/p2` → `251-p2`
* **Text:** Lowercase, remove punctuation, trim spaces.
* **Dates:** Convert to DD/MM/YYYY.
* **Strict Match Rule:** District + Taluka + Village + Survey + Subdivision MUST all match between the two documents.

---

## 🛡️ STEP 7: SCHEMA VALIDATION & 🧾 STEP 8: AUDIT LOG
* **Validation:** Enforce output strictly via Pydantic (parse → validate → retry → fallback null).
* **Audit Trail:** Every single LLM prompt, image reference, and response is logged atomically to a local SQLite database for debugging.

---

## 📄 STEP 9: XLSX OUTPUT
Structured 8-column Excel output generated via `pandas`.
