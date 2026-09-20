"""Unit tests for the graceful-degradation and dataclass logic in roundtrip.py.

These tests are environment-independent (they monkeypatch the tokenizers
import probe rather than relying on the package being absent/present), so
they close a real coverage gap: `test_roundtrip_live.py` only runs when
`tokenizers` IS installed, and CI's `[dev]` extra always installs it -- so
the "tokenizers not installed" degraded-result path (the exact behavior
this module's own docstring promises: "callers get a clear 'unavailable'
result rather than a crash") was never actually exercised in CI, and was
only accidentally covered on hosts that happen to lack tokenizers locally.
"""
from bytelevel_guard import roundtrip as rt


def test_try_import_tokenizers_returns_none_when_absent(monkeypatch):
    """Directly exercises the ImportError branch of the import probe."""
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "tokenizers":
            raise ImportError("simulated: tokenizers not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert rt._try_import_tokenizers() is None


def test_roundtrip_check_reports_unavailable_when_tokenizers_missing(monkeypatch):
    """The primary degraded-result contract: no crash, a clear unavailable
    report with an explanatory error and no cases, regardless of what path
    or token list is passed in."""
    monkeypatch.setattr(rt, "_try_import_tokenizers", lambda: None)

    report = rt.roundtrip_check_added_tokens("/nonexistent/tokenizer.json", ["kuca"])

    assert report.available is False
    assert report.cases is None
    assert report.backend is None
    assert report.error is not None
    assert "not installed" in report.error
    # all_match must still be safely True (no cases to contradict) so
    # callers combining this with the static scan don't get a false
    # "roundtrip failed" signal when the check simply couldn't run.
    assert report.all_match is True


def test_roundtrip_case_matches_property():
    assert rt.RoundtripCase(original="a", decoded="a").matches is True
    assert rt.RoundtripCase(original="a", decoded="b").matches is False


def test_roundtrip_report_all_match_with_no_cases():
    assert rt.RoundtripReport(available=True, cases=None).all_match is True
    assert rt.RoundtripReport(available=True, cases=[]).all_match is True


def test_roundtrip_report_all_match_mixed_cases():
    ok = rt.RoundtripCase(original="a", decoded="a")
    bad = rt.RoundtripCase(original="b", decoded="c")
    assert rt.RoundtripReport(available=True, cases=[ok]).all_match is True
    assert rt.RoundtripReport(available=True, cases=[ok, bad]).all_match is False


def test_roundtrip_check_success_path_builds_cases(monkeypatch):
    """Exercises the successful-import happy path (lines 60-70) using a
    lightweight fake tokenizers module, so this passes regardless of
    whether the real `tokenizers` package is installed on the runner."""

    class FakeEncoding:
        def __init__(self, ids):
            self.ids = ids

    class FakeTokenizer:
        def __init__(self):
            self.added = None
            self._by_id = {}

        def add_tokens(self, tokens):
            self.added = list(tokens)

        def encode(self, text, add_special_tokens=False):
            token_id = len(self._by_id)
            self._by_id[token_id] = text
            return FakeEncoding(ids=[token_id])

        def decode(self, ids, skip_special_tokens=False):
            # Simulate a clean round trip for this fake backend: decode
            # returns exactly what was encoded, by id lookup.
            return "".join(self._by_id[i] for i in ids)

    class FakeTokenizerClass:
        @staticmethod
        def from_file(path):
            assert path == "fake.json"
            return FakeTokenizer()

    class FakeTokenizersModule:
        __version__ = "0.0.0-fake"
        Tokenizer = FakeTokenizerClass

    monkeypatch.setattr(rt, "_try_import_tokenizers", lambda: FakeTokenizersModule())

    report = rt.roundtrip_check_added_tokens("fake.json", ["ab", "cde"])

    assert report.available is True
    assert report.backend == "tokenizers==0.0.0-fake"
    assert report.error is None
    assert report.cases is not None
    assert len(report.cases) == 2
    assert {c.original for c in report.cases} == {"ab", "cde"}
    # This fake backend deliberately round-trips cleanly.
    assert report.all_match is True
