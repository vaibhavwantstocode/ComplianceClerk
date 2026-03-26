import json
import re
from pathlib import Path

import pandas as pd

from src.utils.normalizer import combine_and_normalize, generate_match_key


BASE_DIR = Path(__file__).parent
STEPWISE_DIR = BASE_DIR / "output" / "stepwise_json"
NA_DIR = STEPWISE_DIR / "na_orders"
LEASE_DIR = STEPWISE_DIR / "lease_docs"
OUTPUT_XLSX = BASE_DIR / "output" / "output.xlsx"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _collect_na_records() -> list[dict]:
    records = []
    for path in sorted(NA_DIR.glob("*.na.json")):
        payload = _load_json(path)
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        if isinstance(data, dict):
            records.append(data)
    return records


def _collect_lease_records() -> list[dict]:
    records = []
    for path in sorted(LEASE_DIR.glob("*.lease.json")):
        if path.name.endswith(".lease_paddle.json"):
            continue
        payload = _load_json(path)
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        if isinstance(data, dict):
            records.append(data)
    return records


def _extract_doc_year(lease_doc_no: str) -> str:
    text = (lease_doc_no or "").strip()
    m = re.search(r"/(\d{4})$", text)
    return m.group(1) if m else ""


def _normalize_date_with_doc_year(lease_start: str, lease_doc_no: str) -> str:
    # If Lease Start year mismatches doc year, force year from Lease Deed Doc No.
    doc_year = _extract_doc_year(lease_doc_no)
    if not doc_year:
        return (lease_start or "").strip()

    text = (lease_start or "").strip()
    m = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", text)
    if not m:
        return text

    day, month, date_year = m.groups()
    if date_year == doc_year:
        return f"{int(day):02d}/{int(month):02d}/{date_year}"

    return f"{int(day):02d}/{int(month):02d}/{doc_year}"


def _clean_area_value(raw: str):
    text = (raw or "").strip().replace(",", "")
    m = re.search(r"\d+(?:\.\d+)?", text)
    if not m:
        return ""
    value = m.group(0)
    if "." in value:
        try:
            f = float(value)
            if f.is_integer():
                return int(f)
            return f
        except ValueError:
            return value
    try:
        return int(value)
    except ValueError:
        return value


def _merge_records(na_records: list[dict], lease_records: list[dict]) -> list[dict]:
    lease_by_key = {}
    for lease in lease_records:
        key = generate_match_key(lease.get("village"), lease.get("survey_no"), lease.get("district"))
        if key != "--" and key not in lease_by_key:
            lease_by_key[key] = lease

    rows = []
    for idx, na in enumerate(na_records, start=1):
        key = generate_match_key(na.get("village"), na.get("survey_no"), na.get("district"))
        lease = lease_by_key.get(key, {})

        merged = combine_and_normalize(na, lease)
        lease_doc_no = merged.get("Lease Deed Doc. No.", "")
        lease_start = _normalize_date_with_doc_year(merged.get("Lease Start", ""), lease_doc_no)

        row = {
            "Sr.no.": idx,
            "Village ": merged.get("Village", ""),
            "Survey No.": merged.get("Survey No.", ""),
            "Area in NA Order": _clean_area_value(str(na.get("area_na", ""))),
            "Dated": merged.get("Dated", ""),
            "NA Order No.": merged.get("NA Order No.", ""),
            "Lease Deed Doc. No.": lease_doc_no,
            "Lease Area ": _clean_area_value(str(lease.get("lease_area", ""))),
            "Lease Start ": lease_start,
        }
        rows.append(row)

    return rows


def main() -> None:
    if not NA_DIR.exists() or not LEASE_DIR.exists():
        raise FileNotFoundError("Expected output/stepwise_json/na_orders and lease_docs to exist")

    na_records = _collect_na_records()
    lease_records = _collect_lease_records()
    rows = _merge_records(na_records, lease_records)

    OUTPUT_XLSX.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_excel(OUTPUT_XLSX, index=False)

    print(f"Merged {len(rows)} NA rows with {len(lease_records)} lease rows")
    print(f"Wrote: {OUTPUT_XLSX}")


if __name__ == "__main__":
    main()
