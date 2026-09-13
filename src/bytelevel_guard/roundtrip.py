"""Optional live round-trip check against an installed HF tokenizer.

This is best-effort: if the `tokenizers` package is not installed, callers
get a clear "unavailable" result rather than a crash. When available, this
performs the real encode -> decode round trip (not just the static table
lookup in scan.py) so a positive result is empirical, not just predicted.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RoundtripCase:
    original: str
    decoded: str

    @property
    def matches(self) -> bool:
        return self.original == self.decoded


@dataclass
class RoundtripReport:
    available: bool
    backend: str | None = None
    cases: list[RoundtripCase] | None = None
    error: str | None = None

    @property
    def all_match(self) -> bool:
        if not self.cases:
            return True
        return all(c.matches for c in self.cases)


def _try_import_tokenizers():
    try:
        import tokenizers  # noqa: F401

        return tokenizers
    except ImportError:
        return None


def roundtrip_check_added_tokens(
    base_vocab_tokenizer_json: str, candidate_tokens: list[str]
) -> RoundtripReport:
    """Add candidate_tokens to a real Tokenizer loaded from a tokenizer.json
    and verify encode->decode returns the original string, using the actual
    installed `tokenizers` Rust backend (the one affected by #1996) rather
    than our own prediction.
    """
    tk_mod = _try_import_tokenizers()
    if tk_mod is None:
        return RoundtripReport(
            available=False,
            error="`tokenizers` package not installed; static scan only",
        )
    try:
        tok = tk_mod.Tokenizer.from_file(base_vocab_tokenizer_json)
        tok.add_tokens(candidate_tokens)
        cases = []
        for t in candidate_tokens:
            ids = tok.encode(t, add_special_tokens=False).ids
            decoded = tok.decode(ids, skip_special_tokens=False)
            cases.append(RoundtripCase(original=t, decoded=decoded))
        return RoundtripReport(
            available=True, backend=f"tokenizers=={tk_mod.__version__}", cases=cases
        )
    except Exception as exc:  # pragma: no cover - depends on external file/lib
        return RoundtripReport(available=True, error=str(exc))
