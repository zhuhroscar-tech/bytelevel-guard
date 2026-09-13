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

A real, currently open bug in HuggingFace's `tokenizers` / `transformers`
([tokenizers#1996](https://github.com/huggingface/tokenizers/issues/1996))
causes the fast Rust decoder to truncate these remapped characters back to
their raw low byte when they appear literally inside an *added token*
string — so `'č'` silently decodes back out as `'\r'`. This has been
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

```bash
pip install bytelevel-guard
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
  against your specific vocabulary. Upstream may fix #1996 in a future
  `tokenizers` release, at which point the static scan becomes a
  conservative check with no false negatives it can no longer detect, but
  it will not itself tell you whether your installed version is patched.
  Install `tokenizers` as a dev dependency and consult
  `bytelevel_guard.roundtrip.roundtrip_check_added_tokens()` for a live,
  version-specific check.
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
