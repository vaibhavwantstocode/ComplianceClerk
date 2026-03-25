import re
from src.model.schemas import NAOrderData, LeaseDocData, CombinedRecord

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

def combine_and_normalize(na_data: dict, lease_data: dict) -> dict:
    """
    Takes the raw dictionaries from both extractors,
    normalizes their fields, and returns a dictionary 
    matching CombinedRecord schema.
    """
    # Safe fetch
    area_na = normalize_area(str(na_data.get('area_na', '')))
    lease_area = normalize_area(str(lease_data.get('lease_area', '')))
    
    na_date = normalize_date(str(na_data.get('date', '')))
    lease_start = normalize_date(str(lease_data.get('lease_start', '')))
    
    survey = normalize_survey_no(str(na_data.get('survey_no', '')))
    
    village = str(na_data.get('village', '')).strip()
    order_no = str(na_data.get('order_no', '')).strip()
    lease_doc_no = str(lease_data.get('lease_doc_no', '')).strip()
    
    return {
        "village": village if village.lower() != 'null' else "",
        "survey_no": survey,
        "area_na": area_na,
        "date": na_date,
        "order_no": order_no if order_no.lower() != 'null' else "",
        "lease_doc_no": lease_doc_no if lease_doc_no.lower() != 'null' else "",
        "lease_area": lease_area,
        "lease_start": lease_start
    }
