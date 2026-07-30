"""Export functions for saving harvested bibliographic records to local files."""

import csv
import json
import sqlite3
from typing import List

import openpyxl

from .models import SeojiRecord

_FIELDS = [
    "control_no",
    "title",
    "author",
    "publisher",
    "pub_year",
    "seoji_year",
    "category",
    "isbn",
    "doc_yn",
    "page_info",
    "detail_url",
    "source",
]


def export_xlsx(records: List[SeojiRecord], output_path: str) -> str:
    """Export records to Excel (.xlsx) file."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "SeojiRecords"

    ws.append(_FIELDS)
    for r in records:
        d = r.to_dict()
        ws.append([d.get(f, "") for f in _FIELDS])

    wb.save(output_path)
    return output_path


def export_csv(records: List[SeojiRecord], output_path: str) -> str:
    """Export records to UTF-8 CSV (.csv) file."""
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for r in records:
            writer.writerow(r.to_dict())
    return output_path


def export_json(records: List[SeojiRecord], output_path: str) -> str:
    """Export records to JSON (.json) file."""
    data = [r.to_dict() for r in records]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return output_path


def export_sqlite(
    records: List[SeojiRecord],
    output_path: str,
    table_name: str = "seoji_records",
) -> str:
    """Export records to SQLite database (.sqlite/.db) file."""
    conn = sqlite3.connect(output_path)
    cur = conn.cursor()

    columns_def = ", ".join(f"{f} TEXT" for f in _FIELDS)
    cur.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_def})")

    placeholders = ", ".join("?" for _ in _FIELDS)
    insert_sql = f"INSERT INTO {table_name} ({', '.join(_FIELDS)}) VALUES ({placeholders})"

    rows = []
    for r in records:
        d = r.to_dict()
        rows.append(tuple(str(d.get(f, "")) for f in _FIELDS))

    cur.executemany(insert_sql, rows)
    conn.commit()
    conn.close()
    return output_path


def export_records(
    records: List[SeojiRecord],
    output_path: str,
    fmt: str = "",
) -> str:
    """Export records to output_path using specified format or file extension."""
    if not fmt:
        if output_path.endswith(".xlsx"):
            fmt = "xlsx"
        elif output_path.endswith(".csv"):
            fmt = "csv"
        elif output_path.endswith(".sqlite") or output_path.endswith(".db"):
            fmt = "sqlite"
        else:
            fmt = "json"

    fmt = fmt.lower().strip()
    if fmt == "xlsx":
        return export_xlsx(records, output_path)
    elif fmt == "csv":
        return export_csv(records, output_path)
    elif fmt in ("sqlite", "db", "sqlite3"):
        return export_sqlite(records, output_path)
    else:
        return export_json(records, output_path)
