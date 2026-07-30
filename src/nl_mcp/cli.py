"""Command Line Interface for National Library of Korea Seoji OpenAPI tool."""

import argparse
import json
import sys
from typing import Any, Dict, List

from .client import NlSeojiClient
from .config import get_api_key
from .exporters import export_records
from .models import SeojiRecord


def cmd_status(args: argparse.Namespace) -> int:
    """Handle 'status' subcommand."""
    api_key = get_api_key()
    if not api_key:
        print("NL_API_KEY 상태: 미설정 (.env 파일 또는 환경변수를 확인하세요)", file=sys.stderr)
        return 1

    client = NlSeojiClient(api_key=api_key)
    try:
        res = client.search(kwd="도서관", page_num=1, page_size=1)
        print("국립중앙도서관 국가서지 OpenAPI 상태: 정상 (OK)")
        print(f"샘플 키워드('도서관') 총 검색 결과 수: {res.total:,}건")
        return 0
    except Exception as e:
        print(f"OpenAPI 상태 확인 중 오류 발생: {str(e)}", file=sys.stderr)
        return 1


def cmd_search(args: argparse.Namespace) -> int:
    """Handle 'search' subcommand."""
    client = NlSeojiClient()
    try:
        res = client.search(
            kwd=args.kwd,
            title=args.title,
            author=args.author,
            publisher=args.publisher,
            keyword=args.keyword,
            isbn=args.isbn,
            seoji_year=args.seoji_year,
            sort=args.sort,
            page_num=args.page,
            page_size=args.rows,
        )
    except Exception as e:
        print(f"검색 오류: {str(e)}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(res.to_dict(), ensure_ascii=False, indent=2))
        return 0

    print(f"총 {res.total:,}건 중 {len(res.records)}건 출력 (Page {res.page_num}):\n")
    for i, r in enumerate(res.records, start=1):
        author_str = f" / {r.author}" if r.author else ""
        pub_str = f" [{r.publisher}, {r.pub_year}]" if (r.publisher or r.pub_year) else ""
        print(f"[{i}] {r.title}{author_str}{pub_str}")
        if r.isbn:
            print(f"    ISBN: {r.isbn}")
        if r.detail_url:
            print(f"    URL: {r.detail_url}")
        print()
    return 0


def cmd_collect(args: argparse.Namespace) -> int:
    """Handle 'collect' subcommand."""
    client = NlSeojiClient()
    try:
        records = client.collect(
            kwd=args.kwd,
            title=args.title,
            author=args.author,
            publisher=args.publisher,
            keyword=args.keyword,
            isbn=args.isbn,
            seoji_year=args.seoji_year,
            sort=args.sort,
            max_records=args.max_records,
        )
    except Exception as e:
        print(f"수집 오류: {str(e)}", file=sys.stderr)
        return 1

    if not records:
        print("수집된 서지 데이터가 없습니다.", file=sys.stderr)
        return 1

    output_path = args.output
    saved = export_records(records, output_path=output_path, fmt=args.format)
    print(f"총 {len(records)}건의 서지 정보를 '{saved}' 파일에 내보냈습니다.")
    return 0


def cmd_server(args: argparse.Namespace) -> int:
    """Handle 'server' subcommand to run STDIO MCP server."""
    from .server import mcp
    mcp.run()
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build argument parser for CLI."""
    parser = argparse.ArgumentParser(
        prog="nl-mcp",
        description="National Library of Korea Seoji OpenAPI MCP Tool & CLI",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="사용 가능한 명령어")

    # status
    subparsers.add_parser("status", help="OpenAPI 키 설정 및 서버 통신 상태 확인")

    # search
    p_search = subparsers.add_parser("search", help="서지사항 일반/상세 검색")
    p_search.add_argument("--kwd", default="", help="일반 검색 키워드")
    p_search.add_argument("--title", default="", help="표제 검색")
    p_search.add_argument("--author", default="", help="저자 검색")
    p_search.add_argument("--publisher", default="", help="발행처 검색")
    p_search.add_argument("--keyword", default="", help="주제 키워드 검색")
    p_search.add_argument("--isbn", default="", help="ISBN/ISSN 검색")
    p_search.add_argument("--seoji-year", default="", help="수록연도 필터")
    p_search.add_argument("--sort", default="", help="정렬 옵션 (예: title_asc, pubyear_desc)")
    p_search.add_argument("--page", type=int, default=1, help="페이지 번호 (기본: 1)")
    p_search.add_argument("--rows", type=int, default=10, help="페이지당 출력 수 (기본: 10)")
    p_search.add_argument("--json", action="store_true", help="JSON 포맷으로 출력")

    # collect
    p_collect = subparsers.add_parser("collect", help="다중 페이지 대량 수집 및 파일 저장")
    p_collect.add_argument("--kwd", default="", help="일반 검색 키워드")
    p_collect.add_argument("--title", default="", help="표제 검색")
    p_collect.add_argument("--author", default="", help="저자 검색")
    p_collect.add_argument("--publisher", default="", help="발행처 검색")
    p_collect.add_argument("--keyword", default="", help="주제 키워드 검색")
    p_collect.add_argument("--isbn", default="", help="ISBN/ISSN 검색")
    p_collect.add_argument("--seoji-year", default="", help="수록연도 필터")
    p_collect.add_argument("--sort", default="", help="정렬 옵션")
    p_collect.add_argument("--max-records", type=int, default=50, help="최대 수집 건수 (기본: 50)")
    p_collect.add_argument("--format", default="", choices=["xlsx", "csv", "json", "sqlite", ""], help="출력 파일 형식")
    p_collect.add_argument("-o", "--output", required=True, help="저장할 로컬 파일 경로")

    # server
    subparsers.add_parser("server", help="MCP 프로토콜 STDIO 서버 실행")

    return parser


def main(argv: List[str] | None = None) -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.subcommand:
        parser.print_help()
        return 0

    if args.subcommand == "status":
        return cmd_status(args)
    elif args.subcommand == "search":
        return cmd_search(args)
    elif args.subcommand == "collect":
        return cmd_collect(args)
    elif args.subcommand == "server":
        return cmd_server(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
