"""Canonical GPT-2 / RoBERTa byte<->unicode remap table.

This is the exact mapping introduced in OpenAI's original GPT-2 encoder.py
(`bytes_to_unicode()`), which every ByteLevel-BPE tokenizer (GPT-2, GPT-Neo,
RoBERTa, Qwen, LLaMA-BPE variants, Mistral, etc.) is built on. Bytes that are
not "nice" printable ASCII (control characters 0x00-0x20, DEL 0x7f, and the
0x80-0xA0 Latin-1 control/NBSP range) are remapped to a visually distinct
codepoint range starting at U+0100, so that every byte value has a printable,
round-trippable single-character representation in the token vocabulary.

Reference: https://github.com/openai/gpt-2/blob/master/src/encoder.py
"""
from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=1)
def bytes_to_unicode() -> dict[int, str]:
    """Reproduce OpenAI's bytes_to_unicode() byte->char table exactly."""
    bs = (
        list(range(ord("!"), ord("~") + 1))
        + list(range(ord("\xa1"), ord("\xac") + 1))
        + list(range(ord("\xae"), ord("\xff") + 1))
    )
    cs = bs[:]
    n = 0
    for b in range(2**8):
        if b not in bs:
            bs.append(b)
            cs.append(2**8 + n)
            n += 1
    return dict(zip(bs, (chr(c) for c in cs)))


@lru_cache(maxsize=1)
def unicode_to_bytes() -> dict[str, int]:
    return {v: k for k, v in bytes_to_unicode().items()}


@lru_cache(maxsize=1)
def remapped_char_to_byte() -> dict[str, int]:
    """Only the subset of the table where char codepoint != original byte.

    These are exactly the characters at risk: any of them appearing literally
    inside an *added token* string (as opposed to arriving through the normal
    byte-level pre-tokenizer pipeline) is the precondition for the
    truncate-to-low-byte corruption documented in
    https://github.com/huggingface/tokenizers/issues/1996 (fast ByteLevel
    decoder applying what is effectively `& 0xFF` to added-token codepoints,
    e.g. U+010D 'č' -> 0x0D '\\r').
    """
    b2u = bytes_to_unicode()
    return {ch: b for b, ch in b2u.items() if ord(ch) != b}


def scan_text_for_risky_chars(text: str) -> list[tuple[int, str, int]]:
    """Return (index, char, original_byte) for each remapped char in text."""
    table = remapped_char_to_byte()
    hits = []
    for i, ch in enumerate(text):
        if ch in table:
            hits.append((i, ch, table[ch]))
    return hits
