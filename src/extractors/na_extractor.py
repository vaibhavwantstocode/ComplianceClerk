import json
from src.audit.logger import log_llm_interaction
from src.extractors.qwen_client import run_qwen_with_retry
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
- Extract exact values as written
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
        merged, primary_raw, retry_raw, unresolved = run_qwen_with_retry(
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


