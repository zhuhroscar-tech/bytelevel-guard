[![English](https://img.shields.io/badge/English-555555?style=flat)](README.md) [![简体中文](https://img.shields.io/badge/简体中文-555555?style=flat)](README.zh-CN.md)

# bytelevel-guard

Check custom tokens for ByteLevel-BPE decode-corruption risks before extending a Hugging Face vocabulary. The CLI scans strings, `tokenizer.json`, or a bare `vocab.json` using the GPT-2 byte-to-Unicode remapping table.

## What it checks

- Finds remapped characters in added tokens and vocabulary entries.
- Reports each character, code point, source, and potential corrupted byte.
- Provides an explanation command and a Python helper for live round-trip checks.
- Returns nonzero exit codes for use in CI.

The motivating bug is [tokenizers#1996](https://github.com/huggingface/tokenizers/issues/1996): literal characters such as `ć` in added tokens can decode as control bytes. A closed upstream issue is not evidence that your installed tokenizer and token-addition path are unaffected.

## Install

Requires Python 3.9+. The static scanner has no third-party runtime dependencies. Install from source in a virtual environment:

```bash
git clone https://github.com/zhuhroscar-tech/bytelevel-guard.git
cd bytelevel-guard
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

The `dev` extra includes pytest and `tokenizers` for live-backend tests. A wheel is also available from [Releases](https://github.com/zhuhroscar-tech/bytelevel-guard/releases); verify it against that release's checksums before installing.

## Quick start

```bash
bytelevel-guard check-strings "kuća" "hello_world"
bytelevel-guard check tokenizer.json
bytelevel-guard explain
python -m pytest
```

Replace `tokenizer.json` with your own file. Exit codes: `0` means no risky characters found, `1` means findings, and `2` means an input path was not found (also used by argparse for invalid arguments).

## Honest limitations

This is a conservative static check, not proof of corruption. Base vocabularies legitimately contain byte-remapped characters; a finding does not establish that an added-token round trip fails. Test your actual vocabulary and installed backend with `bytelevel_guard.roundtrip.roundtrip_check_added_tokens()` and the [live tests](tests/test_roundtrip_live.py).

Coverage is limited to the ByteLevel byte-remap bug class, not SentencePiece normalization, WordPiece offsets, or general tokenizer correctness. The scanner does not modify or repair vocabularies.

## License

[MIT](LICENSE).
