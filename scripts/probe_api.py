"""소장자료 검색 API **호출방식 실측 프로브**.

접속이 되는 곳에서 한 번 돌리면, 지금 ❓ 로 남아 있는 항목들이 한꺼번에 확정된다.
결과는 마크다운 표로 출력되므로 그대로 `docs/NL_API_GUIDE.md` 에 붙여 넣으면 된다.

    NL_API_KEY=... uv run python scripts/probe_api.py            # 전체
    NL_API_KEY=... uv run python scripts/probe_api.py --only A,G # 일부만

판정 원리: **기준 호출의 total 과 비교**한다.
  - 파라미터를 넣었더니 total 이 달라졌다 → 서버가 그 파라미터를 **해석했다**
  - total 이 그대로다 → **무시됐을 가능성이 높다**(값이 우연히 무의미했을 수도 있으니 참고용)
  - 오류가 났다 → 파라미터명은 알지만 값이 틀렸거나, 아예 거부된 것

⚠️ 공공 API 다. 기본 pageSize=1, 호출 간 0.5초 간격, 총 호출 수를 출력한다.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from nl_mcp.config import CATEGORIES, MAX_PAGE_SIZE, get_api_key  # noqa: E402
from nl_mcp.client import NlClient, NlError                        # noqa: E402

TERM = "교육불평등"          # 실측 total 63(도서). 상한에 안 걸리는 검색어
BIG_TERM = "교육복지"        # 실측 total 1,856(도서). 상한 판별용
CALLS = {"n": 0}


def raw(client: NlClient, **params) -> tuple[int | None, int, str]:
    """(total, 레코드 수, 비고) — 오류는 문자열로 돌려준다."""
    CALLS["n"] += 1
    try:
        total, recs, _env = client.search_page(**params)
        return total, len(recs), ""
    except NlError as e:
        return None, 0, str(e)[:110]
    finally:
        time.sleep(0.5)


def verdict(base: int | None, got: int | None, note: str) -> str:
    if note:
        return f"오류: {note}"
    if base is None or got is None:
        return "판정불가"
    if got == base:
        return f"total 동일({got:,}) → 무시된 듯"
    return f"total {base:,} → {got:,} → **해석됨**"


def section(title: str):
    print(f"\n## {title}\n")


def table(rows: list[tuple[str, str]], head=("시도", "결과")):
    print(f"| {head[0]} | {head[1]} |")
    print("|---|---|")
    for a, b in rows:
        print(f"| `{a}` | {b} |")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="실행할 절 (예: A,C,G)")
    args = ap.parse_args()
    only = {s.strip().upper() for s in args.only.split(",") if s.strip()}
    want = lambda s: (not only) or s in only  # noqa: E731

    if not get_api_key():
        print("NL_API_KEY 가 없습니다.", file=sys.stderr)
        return 1
    c = NlClient(throttle=0, timeout=30)

    print(f"# 소장자료 검색 API 프로브 결과\n\n검색어: `{TERM}` / `{BIG_TERM}`")

    base_total, _, note = raw(c, kwd=TERM, srch_target="title",
                              category="도서", page_num=1, page_size=1)
    print(f"\n기준 호출(`srchTarget=title&category=도서`) total = "
          f"{base_total if base_total is not None else '실패: ' + note}")
    if base_total is None:
        print("\n기준 호출이 실패해 이후 판정이 무의미합니다. 중단합니다.")
        return 1

    # ── A. srchTarget 값 ──────────────────────────────────────────────────────
    if want("A"):
        section("A. `srchTarget` 이 받는 값")
        rows = []
        for tgt in ["total", "title", "author", "publisher", "kwd", "keyword",
                    "isbn", "issn", "classNo", "callNo", "subject", "all", "",
                    "존재하지않는값"]:
            t, n, nt = raw(c, kwd=TERM, srch_target=tgt, category="도서",
                           page_num=1, page_size=1)
            rows.append((f"srchTarget={tgt or '(빈값)'}",
                         f"total={t if t is not None else '오류'} " +
                         (f"— {nt}" if nt else f"({'기준과 동일' if t == base_total else '다름'})")))
        table(rows)

    # ── B. 제목 일치 방식 (부분/전방/완전) ★ 사용자 질문 ──────────────────────
    if want("B"):
        section("B. 제목 일치 방식 — 부분일치 / 전방일치 / 완전일치")
        print("고급검색 UI 에는 세 가지가 있다. API 가 어떤 이름으로 노출하는지 확인한다.\n")
        rows = []
        # (B-1) srchTarget 값 자체에 인코딩하는 방식
        for tgt in ["title_exact", "titleExact", "title_front", "titleFront",
                    "title_part", "titlePart", "exactTitle", "frontTitle"]:
            t, n, nt = raw(c, kwd=TERM, srch_target=tgt, category="도서",
                           page_num=1, page_size=1)
            rows.append((f"srchTarget={tgt}", verdict(base_total, t, nt)))
        # (B-2) 별도 파라미터로 주는 방식
        for k, v in [("matchType", "exact"), ("matchType", "front"), ("matchType", "part"),
                     ("exactYn", "Y"), ("exactMatch", "true"), ("searchType", "exact"),
                     ("titleMatch", "exact"), ("opt", "exact")]:
            t, n, nt = raw(c, kwd=TERM, srch_target="title", category="도서",
                           page_num=1, page_size=1, **{k: v})
            rows.append((f"{k}={v}", verdict(base_total, t, nt)))
        # (B-3) 따옴표로 구문검색을 표현하는 방식
        for q in [f'"{TERM}"', f"'{TERM}'", f"={TERM}", f"^{TERM}"]:
            t, n, nt = raw(c, kwd=q, srch_target="title", category="도서",
                           page_num=1, page_size=1)
            rows.append((f"kwd={q}", verdict(base_total, t, nt)))
        table(rows)
        print("\n> 실측 참고: 현재 `srchTarget=title` 은 **토큰 매칭 + 적합도 순**으로 보인다. "
              "2026-08-11 수집분에서 결과의 40~83%가 제목에 검색어를 포함하지 않았다. "
              "완전일치가 지원된다면 이 오탐을 서버측에서 없앨 수 있다.")

    # ── C. category 값 ────────────────────────────────────────────────────────
    if want("C"):
        section("C. `category` 가 받는 값 (고급검색 UI 자료구분 13종)")
        rows = []
        no_cat, _, _ = raw(c, kwd=TERM, srch_target="title", page_num=1, page_size=1)
        rows.append(("(category 없음)", f"total={no_cat}"))
        for cat in CATEGORIES:
            t, n, nt = raw(c, kwd=TERM, srch_target="title", category=cat,
                           page_num=1, page_size=1)
            rows.append((f"category={cat}",
                         f"total={t if t is not None else '오류'}" + (f" — {nt}" if nt else "")))
        table(rows)
        print("\n> 각 값의 total 이 서로 다르고 합이 '전체'에 가까우면 자료구분 필터로 정상 동작하는 것이다.")

    # ── D. 발행년 서버측 범위 필터 ★ 500 상한 우회의 핵심 ─────────────────────
    if want("D"):
        section("D. 발행년 범위 — 서버측 필터인가 (500 상한 우회의 핵심)")
        print("고급검색 UI 에 '발행년 [    ] 년부터 [    ]' 가 있다. "
              "API 가 받는다면 연도 슬라이싱으로 500 상한을 우회할 수 있다.\n")
        rows = []
        CAND = [
            ("startPubYear", "endPubYear"), ("pubYearStart", "pubYearEnd"),
            ("fromPubYear", "toPubYear"), ("pubStartYear", "pubEndYear"),
            ("startYear", "endYear"), ("pubYearFrom", "pubYearTo"),
            ("sYear", "eYear"), ("year1", "year2"),
        ]
        for a, b in CAND:
            t, n, nt = raw(c, kwd=BIG_TERM, srch_target="title", category="도서",
                           page_num=1, page_size=1, **{a: "2020", b: "2020"})
            rows.append((f"{a}=2020&{b}=2020", verdict(None, t, nt) if nt else
                         (f"total={t:,} → **해석됨**(2020년만)" if t and t < 1856
                          else f"total={t} → 무시된 듯")))
        for single in ["pubYear", "pubyear", "year"]:
            t, n, nt = raw(c, kwd=BIG_TERM, srch_target="title", category="도서",
                           page_num=1, page_size=1, **{single: "2020"})
            rows.append((f"{single}=2020",
                         f"total={t} → " + ("**해석됨**" if t and t < 1856 else "무시된 듯")))
        table(rows)

    # ── E. 정렬 ───────────────────────────────────────────────────────────────
    if want("E"):
        section("E. `sort` — 정렬 (뒤집어서 반대쪽 500건을 받는 우회책의 전제)")
        rows = []
        for k in ["sort", "sortOrder", "order", "orderBy"]:
            for v in ["title_asc", "title_desc", "pubyear_asc", "pubyear_desc",
                      "PUBLISH_YEAR/DESC", "asc", "desc"]:
                t, n, nt = raw(c, kwd=TERM, srch_target="title", category="도서",
                               page_num=1, page_size=1, **{k: v})
                mark = "오류" if nt else ("total 유지(정렬만 바뀌었을 수 있음)"
                                         if t == base_total else f"total={t} 변화")
                rows.append((f"{k}={v}", mark + (f" — {nt}" if nt else "")))
        table(rows)
        print("\n> 정렬은 total 을 바꾸지 않으므로 **첫 레코드가 달라지는지**로 판단해야 한다. "
              "아래 F 절에서 첫 레코드 제목을 비교한다.")
        # 첫 레코드 비교
        print("\n첫 레코드 비교:")
        for v in ["", "title_asc", "title_desc", "pubyear_asc", "pubyear_desc"]:
            kw = {"sort": v} if v else {}
            CALLS["n"] += 1
            try:
                _t, recs, _ = c.search_page(kwd=TERM, srch_target="title", category="도서",
                                            page_num=1, page_size=1, **kw)
                print(f"  - sort={v or '(없음)':14} → {recs[0].title[:50] if recs else '(없음)'}")
            except NlError as e:
                print(f"  - sort={v or '(없음)':14} → 오류 {str(e)[:60]}")
            time.sleep(0.5)

    # ── F. 상세검색(불리언) 스킴 ──────────────────────────────────────────────
    if want("F"):
        section("F. 필드 간 AND/OR/NOT — 상세검색 스킴이 있는가")
        print("고급검색 UI 는 필드 3개를 AND/OR/NOT 으로 묶는다. "
              "자매 서비스(서지정보 API)는 `detailSearch=true&f1=&v1=&and1=` 스킴을 썼다.\n")
        rows = []
        t, n, nt = raw(c, kwd="", srch_target="title", category="도서", page_num=1, page_size=1,
                       detailSearch="true", f1="title", v1=TERM)
        rows.append(("detailSearch=true&f1=title&v1=…", verdict(base_total, t, nt)))
        t, n, nt = raw(c, kwd="", srch_target="title", category="도서", page_num=1, page_size=1,
                       detailSearch="true", f1="title", v1="교육", and1="AND",
                       f2="title", v2="불평등")
        rows.append(("detailSearch + f1 AND f2", verdict(base_total, t, nt)))
        for op in ["AND", "OR", "NOT"]:
            t, n, nt = raw(c, kwd=f"교육 {op} 불평등", srch_target="title", category="도서",
                           page_num=1, page_size=1)
            rows.append((f"kwd=교육 {op} 불평등", verdict(base_total, t, nt)))
        table(rows)

    # ── G. 500 상한의 기준 ★ 미해결 쟁점 ──────────────────────────────────────
    if want("G"):
        section("G. 500 상한 — 레코드 오프셋 기준인가, 페이지 수 기준인가")
        print(f"`{BIG_TERM}`(실측 total 1,856)으로 pageSize 를 바꿔 가며 **어디서 끊기는지** 본다.\n")
        print("| pageSize | 끊긴 지점 | 누적 회수 | 해석 |")
        print("|---:|---:|---:|---|")
        for size in (10, 50, 100):
            got, page, last_ok = 0, 1, 0
            while page <= 60:
                CALLS["n"] += 1
                try:
                    _t, recs, _ = c.search_page(kwd=BIG_TERM, srch_target="title",
                                                category="도서", page_num=page, page_size=size)
                except NlError as e:
                    print(f"| {size} | page {page} 오류 | {got} | {str(e)[:50]} |")
                    break
                time.sleep(0.5)
                if not recs:
                    interp = ("레코드 기준(500)" if abs(got - 500) <= size
                              else f"페이지 기준({page - 1}p)" if got < 500 else "기타")
                    print(f"| {size} | page {page} 에서 빈 응답 | {got} | {interp} |")
                    break
                got += len(recs)
                last_ok = page
                page += 1
            else:
                print(f"| {size} | 60p 까지 안 끊김 | {got} | 상한 없음? |")
        print("\n> `pageSize=10` 에서 **50건**에서 끊기면 페이지 수 기준(5페이지), "
              "**500건**까지 가면 레코드 오프셋 기준이다. "
              "현재 클라이언트는 레코드 기준으로 막아 두어 어느 쪽이든 안전하다.")

    # ── H. 오류 봉투 · 응답 원문 ──────────────────────────────────────────────
    if want("H"):
        section("H. 오류 응답 봉투 · 원문 마크업")
        bad = NlClient(api_key="INVALID-KEY-PROBE", throttle=0, timeout=30)
        CALLS["n"] += 1
        try:
            body = bad._call({"srchTarget": "title", "kwd": TERM, "pageNum": 1, "pageSize": 1})
            print("잘못된 키 응답 원문(앞 600자):\n```\n" + body[:600] + "\n```")
        except NlError as e:
            print(f"잘못된 키 → NlError: {e}")
        time.sleep(0.5)

        CALLS["n"] += 1
        body = c._call({"srchTarget": "title", "kwd": TERM, "category": "도서",
                        "pageNum": 1, "pageSize": 2})
        print("\n정상 응답 원문(앞 1200자) — **하이라이트 마크업 실제 형태 확인용**:\n```json")
        print(body[:1200])
        print("```")
        try:
            d = json.loads(body)
            print(f"\n최상위 키: {list(d)}")
            if d.get("result"):
                print(f"레코드 키({len(d['result'][0])}개): {list(d['result'][0])}")
        except Exception:
            pass

    print(f"\n---\n총 HTTP 호출 {CALLS['n']}회.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
