"""Unit tests for nl_mcp exporters."""

import json
import os
import sqlite3
from nl_mcp.exporters import export_csv, export_json, export_records, export_sqlite, export_xlsx


def test_export_xlsx(tmp_path, sample_records):
    out = os.path.join(tmp_path, "test.xlsx")
    saved = export_xlsx(sample_records, out)
    assert os.path.exists(saved)
    assert os.path.getsize(saved) > 0


def test_export_csv(tmp_path, sample_records):
    out = os.path.join(tmp_path, "test.csv")
    saved = export_csv(sample_records, out)
    assert os.path.exists(saved)
    with open(saved, "r", encoding="utf-8-sig") as f:
        lines = f.readlines()
    assert len(lines) == 3  # header + 2 records


def test_export_json(tmp_path, sample_records):
    out = os.path.join(tmp_path, "test.json")
    saved = export_json(sample_records, out)
    assert os.path.exists(saved)
    with open(saved, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data) == 2
    assert data[0]["control_no"] == "3197221"


def test_export_sqlite(tmp_path, sample_records):
    out = os.path.join(tmp_path, "test.db")
    saved = export_sqlite(sample_records, out)
    assert os.path.exists(saved)

    conn = sqlite3.connect(saved)
    cur = conn.cursor()
    cur.execute("SELECT control_no, title FROM seoji_records")
    rows = cur.fetchall()
    conn.close()

    assert len(rows) == 2
    assert rows[0][0] == "3197221"


def test_export_records_auto(tmp_path, sample_records):
    out_xlsx = os.path.join(tmp_path, "auto.xlsx")
    assert export_records(sample_records, out_xlsx).endswith(".xlsx")
    out_sqlite = os.path.join(tmp_path, "auto.sqlite")
    assert export_records(sample_records, out_sqlite).endswith(".sqlite")
