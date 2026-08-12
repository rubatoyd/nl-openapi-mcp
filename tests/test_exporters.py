"""내보내기 — 4개 형식 왕복 및 raw 보존."""
import csv
import json
import sqlite3

import pytest
import samples

from nl_mcp.exporters import export
from nl_mcp.models import COLUMNS
from nl_mcp.parser import parse_holding


@pytest.fixture
def records():
    return [parse_holding(s) for s in samples.ALL_SAMPLES]


def test_네가지_형식_전부_생성된다(records, tmp_path):
    from pathlib import Path

    paths = export(records, ["xlsx", "csv", "json", "sqlite"], str(tmp_path), "t")
    assert len(paths) == 4
    assert {Path(p).suffix for p in paths} == {".xlsx", ".csv", ".json", ".sqlite"}
    for p in paths:
        assert Path(p).exists() and Path(p).stat().st_size > 0


def test_json_은_raw_원본을_보존한다(records, tmp_path):
    p = export(records, ["json"], str(tmp_path), "t")[0]
    data = json.loads(open(p, encoding="utf-8").read())
    assert len(data) == len(records)
    assert len(data[0]["raw"]) == 24            # 원본 24개 필드 그대로
    assert data[0]["raw"]["titleInfo"]


def test_csv_는_엑셀호환_BOM_과_전체컬럼(records, tmp_path):
    p = export(records, ["csv"], str(tmp_path), "t")[0]
    assert open(p, "rb").read(3) == b"\xef\xbb\xbf"
    rows = list(csv.DictReader(open(p, encoding="utf-8-sig")))
    assert len(rows) == len(records)
    assert list(rows[0]) == COLUMNS


def test_sqlite_재실행시_누적되지_않는다(records, tmp_path):
    p = export(records, ["sqlite"], str(tmp_path), "t")[0]
    export(records, ["sqlite"], str(tmp_path), "t")      # 같은 이름으로 재실행
    con = sqlite3.connect(p)
    try:
        assert con.execute("SELECT COUNT(*) FROM holdings").fetchone()[0] == len(records)
    finally:
        con.close()


def test_db_확장자_별칭과_대문자_형식명(records, tmp_path):
    assert export(records, ["DB"], str(tmp_path), "t")[0].endswith(".sqlite")
    assert export(records, ["JSON"], str(tmp_path), "t2")[0].endswith(".json")


def test_모르는_형식은_거부한다(records, tmp_path):
    with pytest.raises(ValueError, match="지원하지 않는"):
        export(records, ["parquet"], str(tmp_path), "t")
