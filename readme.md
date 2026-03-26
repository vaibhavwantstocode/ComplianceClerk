# ComplianceClerk

ComplianceClerk processes land records from mixed PDF sets and generates matched output between:

- NA permission orders (short PDFs)
- Lease deed bundles (long PDFs with Annexure content)

The pipeline combines deterministic page selection with OpenAI vision extraction, then performs strict matching and exports normalized output.

## What The Pipeline Does

1. Scans PDFs from `data/sample_pdfs`.
2. Classifies each file as `NA_ORDER` or `LEASE_DOC`.
3. For NA orders:
- Uses only page 1.
- Sends page image to OpenAI (`gpt-4o`) with a strict JSON prompt.
4. For lease documents:
- Detects Annexure page deterministically using PaddleOCR (Python 3.10 subprocess).
- Sends only detected Annexure page to OpenAI with strict JSON prompt.
5. Validates extracted payloads via Pydantic schemas.
6. Logs prompt/response/parsed results to SQLite audit database.
7. Performs strict matching and exports Excel.

## Key Design Choices

- Deterministic page routing first, LLM extraction second.
- Two-call architecture for matched pairs:
  - NA page 1 extraction
  - Lease Annexure page extraction
- Field-level retry when required fields are missing.
- Fallback to empty-string fields instead of null values.
- Lease date guardrail: when `Lease Start` year mismatches the year in `Lease Deed Doc. No.` (value after `/`), the pipeline keeps day/month and corrects the year from `Lease Deed Doc. No.`.

## Current Provider Configuration

- Provider: OpenAI Chat Completions API
- Model default: `gpt-4o`
- Config is read from `.env` automatically at startup.

Required environment variable in `.env`:

```env
OPENAI_API_KEY=your_api_key_here
```

Optional overrides:

```env
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_VISION_MODEL=gpt-4o
ANNEXURE_PY310_COMMAND=py -3.10
```

## Folder Structure

```text
ComplianceClerk/
├─ config.py
├─ process_docs.py
├─ run_na_only.py
├─ readme.md
├─ data/
│  └─ sample_pdfs/
├─ output/
│  ├─ matched_records.xlsx
│  └─ stepwise_json/
│     ├─ na_orders/
│     └─ lease_docs/
├─ src/
│  ├─ audit/
│  │  └─ logger.py
│  ├─ extractors/
│  │  ├─ openai_client.py
│  │  ├─ na_extractor.py
│  │  ├─ lease_extractor_llm.py
│  │  ├─ annexure_detector.py
│  │  └─ annexure_detector_py310.py
│  ├─ model/
│  │  └─ schemas.py
│  ├─ parsers/
│  │  └─ classifier.py
│  └─ utils/
│     ├─ normalizer.py
│     └─ pdf_utils.py
└─ audit.db
```

## How To Run

### 1. Install dependencies

Use your project virtual environment and install required packages used by the repository.

### 2. Prepare input PDFs

Place files in `data/sample_pdfs/`.

### 3. Configure API key

Create or update `.env` in project root with `OPENAI_API_KEY`.

### 4. Run full pipeline

```bash
python process_docs.py
```

Outputs:

- `output/matched_records.xlsx`
- `output/stepwise_json/na_orders/*.json`
- `output/stepwise_json/lease_docs/*.json`

### 4b. Build merged Excel directly from stepwise JSON

If you need a direct merge from generated JSON files:

```bash
python merge_stepwise_json_to_excel.py
```

Output:

- `output/output.xlsx`

### 5. Run NA-only refresh

Use this when you only want to regenerate NA extraction JSON after prompt refinement.

```bash
python run_na_only.py
```

## Audit Logging

Audit records are written to `audit.db` table `audit_logs` with:

- `doc_id`
- `step`
- `prompt`
- `response`
- `parsed`
- `status`
- `timestamp`

This makes extraction decisions traceable and easy to debug.

## Notes

- `.env` is ignored by git for secret safety.
- `output/` is ignored by git by design.
- NA prompt currently enforces English village output and heading-based NA order number extraction.
