import json
from src.audit.logger import log_llm_interaction
from src.extractors.openai_client import run_openai_with_retry
from src.model.schemas import LeaseDocData


def process_lease_document_with_llm(filename: str, annexure_page_image: bytes) -> dict:
    prompt = """You are extracting land details from an Annexure-I table in a lease document.

TASK:
Extract the following fields:

- District
- Taluka
- Village
- Survey Number
- Lease Area (in sq.m)
- Lease Deed Document Number
- Lease Start Date

DOCUMENT STRUCTURE:
This page contains:
1. A main table with columns:
   District | Taluka | Village | R.S. No (Old/New) | Area in SQM

2. A DNR stamp (top-right boxed structure):
   - Contains label "DNR"
   - Middle row: multiple numbers
   - Bottom row: year (e.g., 2026)

3. A date at the bottom of the page:
   - Format: Date: dd/mm/yyyy

FIELD DEFINITIONS:

1. District:
- Extract from the "District" column

2. Taluka:
- Extract from the "Taluka" column

3. Village:
- Extract from the "Village" column

4. Survey Number:
- Extract from "R.S. No → New" column
- Example: 251/P2 or 257

5. Lease Area:
- Extract from "Area in SQM" column
- Example: 4047

6. Lease Deed Document Number:
- Extract from DNR stamp (top-right)
- FIRST number in middle row = document number
- Bottom number = year
- Ignore other numbers (page counters)
- Format: <number>/<year>
- Example: 141/2026

7. Lease Start Date:
- Extract from bottom of page after "Date:"
- Format: DD/MM/YYYY

IMPORTANT INSTRUCTIONS:
- Use ONLY the main table (ignore boundary tables)
- Ignore "Four side Boundaries" table
- Do NOT use values like East, West, North, South
- Do NOT extract Old survey number
- Extract values exactly as written
- Do not guess

ROBUSTNESS:
- The DNR stamp may contain OCR noise
- Ensure correct pairing of document number and year
- Validate year is 4 digits (e.g., 2025, 2026)

OUTPUT FORMAT (STRICT JSON ONLY):
{
  "district": "",
  "taluka": "",
  "village": "",
  "survey_no": "",
  "lease_area": "",
  "lease_doc_no": "",
  "lease_start": ""
}"""

    if not annexure_page_image:
        return LeaseDocData().model_dump()

    required_fields = [
        "district",
        "taluka",
        "village",
        "survey_no",
        "lease_area",
        "lease_doc_no",
        "lease_start",
    ]

    try:
        merged, primary_raw, retry_raw, unresolved = run_openai_with_retry(
            primary_prompt=prompt,
            image_bytes=annexure_page_image,
            required_fields=required_fields,
            retry_context=prompt,
        )

        validated_data = LeaseDocData(**merged)
        log_llm_interaction(filename, "LEASE_DOC", prompt, primary_raw, validated_data.model_dump(), "success")
        if retry_raw:
            log_llm_interaction(
                filename,
                "LEASE_DOC_RETRY",
                prompt,
                retry_raw,
                {"resolved_fields": [f for f in required_fields if f not in unresolved], "unresolved_fields": unresolved},
                "success" if not unresolved else "partial",
            )

        return validated_data.model_dump()
        
    except Exception as e:
        log_llm_interaction(filename, "LEASE_DOC", prompt, str(e), {}, "failed")
        return LeaseDocData().model_dump()


