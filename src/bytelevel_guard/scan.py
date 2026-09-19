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
    """Return only the tokens added via added_tokens/add_tokens().

    This is deliberately narrower than "everything in the file": the
    tokenizers#1996 bug class is specific to tokens that bypass the normal
    ByteLevel pre-tokenizer encode step (added_tokens/add_tokens() calls).
    Tokens that are part of the base BPE vocabulary (model.vocab) arrived
    there *through* the correct byte-level encode pipeline and are
    expected, by design, to contain remapped characters -- e.g. the
    space-marker 'Ġ' (U+0120) appears in the majority of real GPT-2/
    RoBERTa/Qwen-family vocab entries. Including base vocab here would
    flag that completely normal encoding as an "at risk" finding on every
    real tokenizer, defeating the tool's own CI-gate use case.
    """
    tokens = []
    for entry in data.get("added_tokens", []) or []:
        content = entry.get("content")
        if isinstance(content, str):
            tokens.append(content)
    return tokens


class ScanInputError(ValueError):
    """Raised for any unusable input path: not a file, bad encoding, or
    invalid JSON. Callers (the CLI) turn this into a clean error message
    instead of letting the exception propagate as a raw traceback."""


def scan_tokenizer_json_file(path: Path) -> ScanResult:
    """Scan a HuggingFace tokenizer.json (or vocab.json) for at-risk tokens.

    Only tokens explicitly listed as *added tokens* are checked against a
    full tokenizer.json -- this is the surface where tokenizers#1996-class
    corruption manifests, since normal byte-level pre-tokenization output
    (the base model.vocab) never contains a raw remapped character outside
    its expected, correctly-encoded position. A bare vocab.json (no
    "added_tokens"/"model" keys, i.e. not a full tokenizer.json) has no way
    to distinguish added vs. base tokens, so every key is checked -- that
    is an explicit, narrower input shape used for ad-hoc vocab review, not
    the default tokenizer.json CI-gate workflow.

    Raises ScanInputError (never a raw OS/json/unicode exception) if the
    path is not a regular file, is not valid UTF-8, or is not valid JSON --
    a directory, a mistaken glob expansion, or a corrupted/binary file are
    all realistic accidental CLI inputs and must produce a clean CLI error
    rather than an unhandled traceback.
    """
    if not path.exists():
        raise FileNotFoundError(f"{path} does not exist")
    if not path.is_file():
        raise ScanInputError(f"{path} is not a file (directory or special file?)")
    try:
        raw = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ScanInputError(f"{path} could not be decoded as UTF-8: {exc}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ScanInputError(f"{path} is not valid JSON: {exc}") from exc
    result = ScanResult()

    if isinstance(data, dict) and ("added_tokens" in data or "model" in data):
        tokens = _iter_added_tokens_from_tokenizer_json(data)
    elif isinstance(data, dict):
        # bare vocab.json: {token: id, ...} -- no added/base distinction
        # exists in this shape, so check every key.
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
