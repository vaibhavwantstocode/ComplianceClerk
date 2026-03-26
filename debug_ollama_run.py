import io
import json
from pathlib import Path
from src.utils.pdf_utils import get_page_as_image
import ollama

pdf = Path('data/sample_pdfs/251-p2 FINAL ORDER.pdf')
img = get_page_as_image(pdf, 0)

prompt = """Read this page and return JSON with keys village,survey_no,district,area_na,date,na_order_no."""

resp = ollama.chat(
    model='qwen3-vl:4b',
    messages=[{
        'role': 'user',
        'content': prompt,
        'images': [img],
    }],
    format='json',
    think=False,
    options={'temperature': 0.0}
)
print('RESP_REPR', repr(resp))
print('CONTENT_REPR', repr(resp.message.content))
