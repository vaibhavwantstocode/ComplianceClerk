import re
from src.model.schemas import NAOrderData, LeaseDocData, CombinedRecord


def _extract_doc_year(lease_doc_no: str) -> str:
    text = (lease_doc_no or "").strip()
    m = re.search(r'/(\d{4})$', text)
    return m.group(1) if m else ""


def _align_lease_start_year(lease_start: str, lease_doc_no: str) -> str:
    """
    Align Lease Start year with Lease Deed Doc No year when mismatch occurs.
    Example: lease_doc_no=838/2025 and lease_start=28/05/2023 -> 28/05/2025
    """
    start = normalize_date(lease_start)
    if not start:
        return ""

    doc_year = _extract_doc_year(lease_doc_no)
    if not doc_year:
        return start

    m = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', start)
    if not m:
        return start

    day, month, year = m.groups()
    if year == doc_year:
        return f"{int(day):02d}/{int(month):02d}/{year}"

    return f"{int(day):02d}/{int(month):02d}/{doc_year}"

def normalize_date(date_str: str) -> str:
    """
    Normalizes date to DD/MM/YYYY.
    If already DD/MM/YYYY, returns as is.
    Handles DD-MM-YYYY, YYYY-MM-DD.
    """
    if not date_str or date_str.lower() == 'null':
        return ""
        
    date_str = date_str.strip()
    
    # Try different regex patterns to catch standard dates
    # e.g., 21-01-2026 or 21/01/2026
    m = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', date_str)
    if m:
        day, month, year = m.groups()
        return f"{int(day):02d}/{int(month):02d}/{year}"
        
    # e.g., 2026-01-21
    m = re.search(r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})', date_str)
    if m:
        year, month, day = m.groups()
        return f"{int(day):02d}/{int(month):02d}/{year}"
        
    return date_str

def normalize_area(area_str: str) -> str:
    """
    Extracts numerical area value, stripping units like 'sq.m.' or 'sqm'.
    """
    if not area_str or area_str.lower() == 'null':
        return ""
        
    # Extract just the float/integer part
    m = re.search(r'([\d\.]+)', area_str)
    if m:
        return m.group(1)
    return area_str.strip()
    
def normalize_survey_no(survey_str: str) -> str:
    """
    Survey Format: 251/p2 -> 251-p2
    """
    if not survey_str or survey_str.lower() == 'null':
        return ""
    
    val = survey_str.strip().lower()
    # Replace slashes with hyphens
    val = val.replace('/', '-')
    return val

def generate_match_key(village: str, survey: str, district: str) -> str:
    """
    Generates a normalized composite key: Village + Survey No + District
    """
    v = str(village).lower().replace(" ", "").strip() if village and village != 'null' else ""
    s = normalize_survey_no(str(survey))
    d = str(district).lower().replace(" ", "").strip() if district and district != 'null' else ""
    return f"{v}-{s}-{d}"

def combine_and_normalize(na_data: dict, lease_data: dict) -> dict:
    """
    Takes the raw dictionaries from both extractors,
    normalizes their fields, and returns a dictionary
    matching CombinedRecord schema.
    """
    # Safe fetch
    area_na = normalize_area(str(na_data.get('area_na', '')))
    lease_area = normalize_area(str(lease_data.get('lease_area', '')))

    na_date = normalize_date(str(na_data.get('dated', '')))
    lease_start = normalize_date(str(lease_data.get('lease_start', '')))

    # Use Lease Survey / Village if NA is empty, or vice-versa
    survey = normalize_survey_no(str(na_data.get('survey_no') or lease_data.get('survey_no') or ''))
    village = str(na_data.get('village') or lease_data.get('village') or '').strip()
    
    na_order_no = str(na_data.get('na_order_no', '')).strip()
    lease_doc_no = str(lease_data.get('lease_doc_no', '')).strip()
    lease_start = _align_lease_start_year(lease_start, lease_doc_no)

    return {
        "Village": village if village.lower() != 'null' else "",
        "Survey No.": survey,
        "Area in NA Order": area_na,
        "Dated": na_date,
        "NA Order No.": na_order_no if na_order_no.lower() != 'null' else "",
        "Lease Deed Doc. No.": lease_doc_no if lease_doc_no.lower() != 'null' else "", 
        "Lease Area": lease_area,
        "Lease Start": lease_start
    }
