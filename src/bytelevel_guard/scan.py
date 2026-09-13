"""Core scanning logic: vocab files, added_tokens, and raw string args."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from bytelevel_guard.bytelevel import scan_text_for_risky_chars


@dataclass
class Finding:
    source: str
    token_repr: str
    char: str
    char_codepoint: str
    corrupted_to: str
    index_in_token: int


@dataclass
class ScanResult:
    findings: list[Finding] = field(default_factory=list)
    tokens_scanned: int = 0
    sources_scanned: int = 0

    @property
    def is_clean(self) -> bool:
        return len(self.findings) == 0


def _corrupted_byte_repr(byte_value: int) -> str:
    """Render the byte the fast-decoder bug would actually emit.

    Mirrors the observed truncation: only the low byte survives, shown as
    the character it decodes to under latin-1 (matching the real-world
    '\\r', '\\x07', '\\x11' examples from tokenizers#1996).
    """
    ch = chr(byte_value)
    return repr(ch)


def scan_token_string(token: str, source: str = "<string>") -> list[Finding]:
    findings: list[Finding] = []
    for idx, ch, byte in scan_text_for_risky_chars(token):
        findings.append(
            Finding(
                source=source,
                token_repr=repr(token),
                char=ch,
                char_codepoint=f"U+{ord(ch):04X}",
                corrupted_to=_corrupted_byte_repr(byte),
                index_in_token=idx,
            )
        )
    return findings


def _iter_added_tokens_from_tokenizer_json(data: dict) -> list[str]:
    tokens = []
    for entry in data.get("added_tokens", []) or []:
        content = entry.get("content")
        if isinstance(content, str):
            tokens.append(content)
    model = data.get("model", {}) or {}
    vocab = model.get("vocab")
    if isinstance(vocab, dict):
        tokens.extend(k for k in vocab.keys() if isinstance(k, str))
    elif isinstance(vocab, list):
        for item in vocab:
            if isinstance(item, list) and item and isinstance(item[0], str):
                tokens.append(item[0])
            elif isinstance(item, str):
                tokens.append(item)
    return tokens


def scan_tokenizer_json_file(path: Path) -> ScanResult:
    """Scan a HuggingFace tokenizer.json (or vocab.json) for at-risk tokens.

    Only tokens that are explicitly listed as *added tokens* (or, more
    broadly, anything in the base vocab) are checked -- these are the
    surface where tokenizers#1996-class corruption manifests, since normal
    byte-level pre-tokenization output never contains a raw remapped
    character outside its expected position.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    result = ScanResult()

    if isinstance(data, dict) and ("added_tokens" in data or "model" in data):
        tokens = _iter_added_tokens_from_tokenizer_json(data)
    elif isinstance(data, dict):
        # bare vocab.json: {token: id, ...}
        tokens = [k for k in data.keys() if isinstance(k, str)]
    else:
        tokens = []

    result.tokens_scanned = len(tokens)
    result.sources_scanned = 1
    for tok in tokens:
        result.findings.extend(scan_token_string(tok, source=str(path)))
    return result


def scan_strings(strings: list[str]) -> ScanResult:
    result = ScanResult()
    result.tokens_scanned = len(strings)
    result.sources_scanned = 1
    for s in strings:
        result.findings.extend(scan_token_string(s))
    return result
