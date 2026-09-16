# bytelevel-guard

Catch ByteLevel-BPE added-token decode corruption before it ships.

## The bug this catches

ByteLevel-BPE tokenizers (GPT-2, RoBERTa, and many Qwen / Mistral / LLaMA-
family vocabularies) remap raw bytes to printable Unicode characters so that
every byte value has a safe, single-character representation inside the
vocabulary. This is the well-known `bytes_to_unicode()` table from OpenAI's
original GPT-2 `encoder.py`. Bytes in the control-character ranges
(`0x00`-`0x20`, `0x7f`, `0x80`-`0xa0`) get remapped to codepoints starting at
`U+0100` — for example byte `0x0D` (carriage return) becomes `'č'` (`U+010D`).

A real bug in HuggingFace's `tokenizers` / `transformers`
([tokenizers#1996](https://github.com/huggingface/tokenizers/issues/1996))
causes the fast Rust decoder to truncate these remapped characters back to
their raw low byte when they appear literally inside an *added token*
string — so `'č'` silently decodes back out as `'\r'`. **The GitHub issue
itself is closed** (closed 2026-05-13 as "completed" after
[PR #1995](https://github.com/huggingface/tokenizers/pull/1995) merged),
but that PR did not make the fix automatic for the common `add_tokens(...)`
call path — it only added the *building blocks* (a `ByteLevel` normalizer)
that a caller must opt into manually. **Verified live on this host against
the currently-installed `tokenizers==0.23.2`** (released 2026-09-03, well
after the "fix" merged): plain `tokenizer.add_tokens(["kuća"])` followed by
encode→decode still returns `'ku\x07a'`, not `'kuća'` — the corruption
still reproduces by default. The maintainer's own suggested workaround
(pre-normalize each added token with `normalizers.ByteLevel().normalize_str`
and pass `normalized=True`) is not applied automatically by any current
`transformers`/`tokenizers` release, so most callers doing a plain
`add_tokens()` are still exposed. Do not read "issue closed" as "bug
fixed for default usage" — this tool's static scan and live round-trip
check both remain necessary. The original report was
confirmed by the reporter against GPT-2, Qwen3.5-9B-Base, Mistral's
Ministral-3-8B-Base, NVIDIA's Nemotron-3-Nano, and LiquidAI's LFM2.5-1.2B —
i.e. it is not a one-off, it reproduces across multiple current-generation
model tokenizers whenever a vocabulary is extended with a token containing
one of these specific characters (common in Balkan-language identifiers
like `č`, `ć`, `đ`, and potentially other scripts that touch this remap
range).

If you add custom tokens to a vocabulary — brand names, domain terms,
non-English identifiers — and one of them happens to contain a remapped
character, the round trip silently corrupts on decode. No exception, no
warning: just garbled text in production.

## What it does

- `bytelevel-guard check tokenizer.json` — scans a HuggingFace
  `tokenizer.json` (or bare `vocab.json`)'s `added_tokens` and vocab entries
  for any token containing an at-risk character, using an exact,
  independently-verified reimplementation of the GPT-2 byte-remap table.
- `bytelevel-guard check-strings "token1" "token2"` — scans ad-hoc strings,
  e.g. before you add them to a vocabulary.
- `bytelevel-guard explain` — prints the mechanism in full.
- If the `tokenizers` package is installed, the test suite also runs a real
  encode → decode round trip against the actual Rust backend (not just the
  static table) as the strongest tier of evidence — see
  `tests/test_roundtrip_live.py`.

## Install

Not yet published to PyPI. Install the latest GitHub Release wheel directly
(checksum-verified, CI-built):

```bash
pip install https://github.com/zhuhroscar-tech/bytelevel-guard/releases/latest/download/bytelevel_guard-0.1.0-py3-none-any.whl
```

Or from source:

```bash
git clone https://github.com/zhuhroscar-tech/bytelevel-guard.git
cd bytelevel-guard && pip install -e ".[dev]"
```

## Usage

```bash
$ bytelevel-guard check-strings "kuća" "hello_world"

ad-hoc strings
● 1 at-risk token(s) found out of 2 scanned
  source        <string>
  token         'kuća'
  char          'ć' (U+0107)
  decodes to    '\x07'
```

Exit code `0` = clean, `1` = at-risk token(s) found, `2` = input file not
found.

## Honest limitations

- This tool predicts corruption from the *static* character table — it is
  not a substitute for actually re-running your specific tokenizer version
  against your specific vocabulary. Issue #1996 is closed, but (as verified
  live against `tokenizers==0.23.2` on 2026-09-15) the default `add_tokens()`
  call path is still affected — closing the GitHub issue did not make the
  fix automatic. If a future `tokenizers` release ever does make the
  by-default fix land, the static scan becomes a conservative check with
  no false negatives it can no longer detect, but it will not itself tell
  you whether your installed version has changed. Install `tokenizers` as
  a dev dependency and consult
  `bytelevel_guard.roundtrip.roundtrip_check_added_tokens()` for a live,
  version-specific check — that check reports ground truth for whatever
  version is actually installed, regardless of upstream issue state.
- Only covers the *ByteLevel*-BPE byte-remap character set (the exact
  `U+0100`+ range from OpenAI's table). It does not detect unrelated
  tokenizer bugs (e.g. SentencePiece normalization issues, WordPiece
  offset bugs) — those are different bug classes with different root
  causes.
- Tested on macOS and Linux (Ubuntu) CI; no OS-specific code paths are used
  so no compatibility gap is expected, but only those two runners are
  actually verified in CI.

## License

MIT
