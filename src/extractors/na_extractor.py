import json
from src.audit.logger import log_llm_interaction
from src.extractors.openai_client import run_openai_with_retry
from src.model.schemas import NAOrderData

def process_na_order_with_llm(filename: str, page_image: bytes) -> dict:
    prompt = """You are extracting structured data from a government land document.

TASK:
Extract the following fields from this document:

- District
- Taluka
- Village
- Survey Number (including subdivision like 251/p2)
- Area in NA Order (total land area in sq.m)
- Date (order date)
- NA Order Number

INSTRUCTIONS:
- This is a government NA permission order
- The document may be in Gujarati
- All required fields are present on the FIRST PAGE
- Return district, taluka, and village in English (Latin script).
- For village: prefer exact English spelling if it appears anywhere on the page; otherwise transliterate Gujarati directly without changing word order.
- For village: read it from the main order paragraph near the pattern District -> Taluka -> Village (the segment with Gujarati label for village, e.g., "ગામ").
- If village appears as "રામપુરા મોટા", output exactly "Rampura Mota".
- Transliteration rule for village names ending with "પુર/પુરા": keep them as "pur/pura" (never "par").
- Keep qualifiers exactly when present (for example Mota/Nana).
- Keep survey_no, area_na, dated, and na_order_no exactly as written (do not alter numeric values).
- For na_order_no: extract ONLY from the top order heading line (labels like "હુકમ નં.", "Order No").
- Prefer the heading value (typically iORA/...) over any footer/reference/application numbers.
- Do NOT use reference/application/proposal/file numbers (for example old proposal numbers like BNA/... if they are not the final order number).
- Do not translate numbers incorrectly
- Do not guess missing values

OUTPUT FORMAT (STRICT JSON ONLY):
{
  "district": "",
  "taluka": "",
  "village": "",
  "survey_no": "",
  "area_na": "",
  "dated": "",
  "na_order_no": ""
}"""
    
    required_fields = ["district", "taluka", "village", "survey_no", "area_na", "dated", "na_order_no"]

    try:
        merged, primary_raw, retry_raw, unresolved = run_openai_with_retry(
            primary_prompt=prompt,
            image_bytes=page_image,
            required_fields=required_fields,
            retry_context=prompt,
        )

        validated_data = NAOrderData(**merged)

        log_llm_interaction(filename, "NA_ORDER", prompt, primary_raw, validated_data.model_dump(), "success")
        if retry_raw:
            log_llm_interaction(
                filename,
                "NA_ORDER_RETRY",
                prompt,
                retry_raw,
                {"resolved_fields": [f for f in required_fields if f not in unresolved], "unresolved_fields": unresolved},
                "success" if not unresolved else "partial",
            )

        return validated_data.model_dump()
        
    except Exception as e:
        log_llm_interaction(filename, "NA_ORDER", prompt, str(e), {}, "failed")
        return NAOrderData().model_dump()


