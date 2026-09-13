"""bytelevel-guard CLI.

Usage:
  bytelevel-guard check <tokenizer.json|vocab.json> ...
  bytelevel-guard check-strings "token one" "token two" ...
  bytelevel-guard explain
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from bytelevel_guard import __version__
from bytelevel_guard.scan import ScanResult, scan_strings, scan_tokenizer_json_file
from bytelevel_guard.style import (
    print_fields,
    resolve_style,
    section,
    status_headline,
)

_EXPLANATION = """\
ByteLevel-BPE tokenizers (GPT-2, RoBERTa, many Qwen/Mistral/LLaMA-family
vocabs) map raw bytes to printable Unicode characters so every byte has a
safe single-character representation in the vocabulary. Bytes in the
control-character ranges (0x00-0x20, 0x7f, 0x80-0xa0) get remapped to
codepoints starting at U+0100 (e.g. byte 0x0D -> 'č' U+010D).

A real, currently-unresolved bug in HuggingFace's `tokenizers`/`transformers`
(github.com/huggingface/tokenizers/issues/1996, confirmed against GPT-2,
Qwen3.5, Mistral-Ministral-3, NVIDIA Nemotron-3, and LiquidAI LFM2.5) causes
the fast Rust decoder to truncate these remapped characters back to their
low byte when they appear literally inside an *added token* string -- e.g.
'č' (U+010D) decodes back out as '\\r' (0x0D), silently corrupting any
identifier, brand name, or non-Latin-script token that happens to contain
one of these characters after custom vocabulary extension.

bytelevel-guard scans a tokenizer.json / vocab.json (or ad-hoc strings) for
any token containing one of these at-risk characters, so the corruption can
be caught in CI before a vocabulary extension ships, rather than surfacing
as silent garbled output in production.
"""


def _print_result(style, result: ScanResult, label: str) -> int:
    section(label)
    if result.is_clean:
        print(status_headline(style, "ok", f"clean -- {result.tokens_scanned} tokens scanned, 0 at risk"))
        return 0
    print(
        status_headline(
            style,
            "fail",
            f"{len(result.findings)} at-risk token(s) found out of {result.tokens_scanned} scanned",
        )
    )
    for f in result.findings:
        print_fields(
            [
                ("source", f.source),
                ("token", f.token_repr),
                ("char", f"{f.char!r} ({f.char_codepoint})"),
                ("decodes to", f.corrupted_to),
            ]
        )
        print()
    return 1


def _cmd_check(args, style) -> int:
    exit_code = 0
    for path_str in args.paths:
        path = Path(path_str)
        if not path.exists():
            print(status_headline(style, "fail", f"not found: {path}"))
            exit_code = 2
            continue
        result = scan_tokenizer_json_file(path)
        rc = _print_result(style, result, str(path))
        exit_code = max(exit_code, rc)
    return exit_code


def _cmd_check_strings(args, style) -> int:
    result = scan_strings(args.strings)
    return _print_result(style, result, "ad-hoc strings")


def _cmd_explain(args, style) -> int:
    print(_EXPLANATION)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bytelevel-guard",
        description="Detect ByteLevel-BPE added-token decode corruption (tokenizers#1996 bug class).",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI color output.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="Scan tokenizer.json/vocab.json file(s).")
    p_check.add_argument("paths", nargs="+", help="Path(s) to tokenizer.json or vocab.json.")
    p_check.set_defaults(func=_cmd_check)

    p_strings = sub.add_parser("check-strings", help="Scan ad-hoc token strings.")
    p_strings.add_argument("strings", nargs="+", help="Token strings to scan.")
    p_strings.set_defaults(func=_cmd_check_strings)

    p_explain = sub.add_parser("explain", help="Print an explanation of the bug class this tool detects.")
    p_explain.set_defaults(func=_cmd_explain)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    style = resolve_style(no_color_flag=args.no_color)
    return args.func(args, style)


if __name__ == "__main__":
    sys.exit(main())
