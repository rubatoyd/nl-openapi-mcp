"""국립중앙도서관 소장자료 검색 CLI — status / search / collect."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .client import NlClient, NlError
from .config import API_RECORD_CAP, get_api_key, redact


def _err(msg: str) -> int:
    print(msg, file=sys.stderr)
    return 1


def cmd_status(args) -> int:
    key = get_api_key()
    print(f"NL_API_KEY: {'설정됨 ' + redact(key) if key else '미설정'}")
    if not key:
        return _err("인증키가 없습니다 — .env 또는 환경변수 NL_API_KEY 를 설정하세요.")
    try:
        total, recs, _ = NlClient().search_page("도서관", page_num=1, page_size=1)
    except NlError as e:
        return _err(f"연결 실패: {e}")
    print("소장자료 검색 API: 정상")
    print(f"  시범 검색('도서관') total = {total:,}건 / 반환 {len(recs)}건")
    print(f"  ※ 이 API 는 한 검색식당 {API_RECORD_CAP}건이 상한입니다(오류코드 012).")
    return 0


def cmd_search(args) -> int:
    if not get_api_key():
        return _err("NL_API_KEY 미설정.")
    try:
        total, recs, _ = NlClient().search_page(
            args.kwd, srch_target=args.target, category=args.category,
            page_num=args.page, page_size=args.rows)
    except NlError as e:
        return _err(f"검색 오류: {e}")
    if args.json:
        print(json.dumps({"total": total, "count": len(recs),
                          "records": [r.to_row() for r in recs]},
                         ensure_ascii=False, indent=2))
        return 0
    print(f"총 {total:,}건 중 {len(recs)}건 (page {args.page})")
    if total > API_RECORD_CAP:
        print(f"⚠️ total 이 API 상한 {API_RECORD_CAP}건을 넘습니다 — 전건 수집 불가. "
              f"검색식을 쪼개세요.\n")
    for i, r in enumerate(recs, 1):
        print(f"[{i}] {r.title}")
        if r.authors:
            print(f"    저자: {r.authors}")
        print(f"    발행: {r.pub_info}  ({r.pub_year or '연도미상'})")
        meta = [x for x in (r.isbn and f"ISBN {r.isbn}", r.call_no and f"청구 {r.call_no}",
                            r.kdc_name, r.place_info) if x]
        if meta:
            print(f"    {' | '.join(meta)}")
        if r.has_fulltext():
            print(f"    원문: {r.doc_type}  {r.lic_text}")
        print()
    return 0


def cmd_collect(args) -> int:
    if not get_api_key():
        return _err("NL_API_KEY 미설정.")
    terms = args.terms or ([args.kwd] if args.kwd else [])
    if not terms:
        return _err("검색어가 없습니다 — --kwd 또는 --terms 를 주세요.")
    max_records = args.max
    if (args.auto_partition or args.sort_depth) and max_records <= API_RECORD_CAP:
        # MCP 도구와 같은 처리 — 상한 이하면 분할해도 담을 자리가 없다
        print(f"※ 상한 우회 옵션이 켜져 최대 수집 건수를 {max_records} → "
              f"{API_RECORD_CAP * 12} 로 올립니다.")
        max_records = API_RECORD_CAP * 12
    try:
        recs, meta = NlClient().search_terms_meta(
            terms, srch_target=args.target, category=args.category,
            year_from=args.year_from, year_to=args.year_to,
            contains=args.contains, max_records=max_records,
            auto_partition=args.auto_partition,
            partition_depth=max(1, min(args.partition_depth, 3)),
            sort_depth=max(0, min(args.sort_depth, 5)),
            **({"exact": True} if args.exact else {}))
    except NlError as e:
        return _err(f"수집 오류: {e}")

    print(f"수집 {len(recs)}건 (검색어 {len(terms)}개 합집합)")
    for a in meta["axes"]:
        flag = "  ⚠️상한" if a["cap_hit"] else ""
        print(f"  - {a['term']}: total {a['total']:,} / 회수 {a['fetched']:,} / 신규 {a['new']:,}{flag}")
    if meta.get("warning"):
        print(f"\n{meta['warning']}\n")

    from .exporters import export
    fmts = args.format or ["xlsx", "csv", "json"]
    base = args.out or str(Path.home() / "nl-output")
    for p in export(recs, fmts, base, args.name or f"nl_{terms[0]}"):
        print(f"  저장: {p}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="nl-mcp", description="국립중앙도서관 소장자료 검색 수집기")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="인증키·연결 점검").set_defaults(func=cmd_status)

    s = sub.add_parser("search", help="소장자료 검색")
    s.add_argument("kwd", help="검색어")
    s.add_argument("--target", default="title", help="검색 대상 필드 (기본 title)")
    s.add_argument("--category", default=None, help="자료 유형 필터 (예: 도서)")
    s.add_argument("--rows", type=int, default=20, help="반환 건수 (최대 100)")
    s.add_argument("--page", type=int, default=1, help="페이지 번호")
    s.add_argument("--json", action="store_true", help="JSON 출력")
    s.set_defaults(func=cmd_search)

    c = sub.add_parser("collect", help="다중 검색어 합집합 수집 → 파일 저장")
    c.add_argument("--kwd", default=None, help="단일 검색어")
    c.add_argument("--terms", nargs="+", default=None, help="변형어 목록 (합집합)")
    c.add_argument("--target", default="title", help="검색 대상 필드 (기본 title)")
    c.add_argument("--category", default=None, help="자료 유형 필터 (예: 도서)")
    c.add_argument("--year-from", type=int, default=None, dest="year_from")
    c.add_argument("--year-to", type=int, default=None, dest="year_to")
    c.add_argument("--contains", nargs="+", default=None, help="결과 부분일치 후처리 필터")
    c.add_argument("--max", type=int, default=500, help="최대 수집 건수")
    c.add_argument("--auto-partition", action="store_true", dest="auto_partition",
                   help="500 상한을 서버측 축(자료구분→관리기관→이용조건)으로 재귀 분할해 우회 "
                        "(실측 회복 7%%→67%%). 호출 수가 는다")
    c.add_argument("--partition-depth", type=int, default=2, dest="partition_depth",
                   help="분할 깊이 1~3 (기본 2). 깊을수록 많이 받지만 호출도 는다")
    c.add_argument("--sort-depth", type=int, default=0, dest="sort_depth",
                   help="정렬 뒤집기 0~5 (기본 0=끄기). 같은 검색식을 정렬 순서만 바꿔 다시 훑는다. "
                        "asc/desc 교집합이 0이라 분할보다 훨씬 싸다 (실측 1,856건 → 7요청 94%%)")
    c.add_argument("--exact", action="store_true",
                   help="큰따옴표 구문검색. ⚠️ 재현율 손실이 커(평균 47%%) 코퍼스 수집에는 부적합")
    c.add_argument("--format", nargs="+", default=None,
                   help="출력 형식 (xlsx csv json sqlite)")
    c.add_argument("--out", default=None, help="출력 디렉터리")
    c.add_argument("--name", default=None, help="출력 파일명(확장자 제외)")
    c.set_defaults(func=cmd_collect)
    return p


def main() -> None:
    args = build_parser().parse_args()
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
