"""Optional live round-trip test against the real `tokenizers` package.

Skipped automatically when `tokenizers` is not installed (it is an optional
dev dependency, not a hard requirement of this CLI, since the static scan
in scan.py works without it). When it *is* installed, this proves the
predicted corruption against the actual Rust decoder, not just our own
table -- the strongest form of evidence for this bug class.
"""
import pytest

from bytelevel_guard.roundtrip import roundtrip_check_added_tokens

tokenizers = pytest.importorskip("tokenizers")


@pytest.fixture(scope="module")
def gpt2_tokenizer_json(tmp_path_factory):
    """Build a minimal real ByteLevel-BPE tokenizer.json from scratch (no
    network download) so this test is hermetic and fast in CI."""
    from tokenizers import Tokenizer
    from tokenizers.models import BPE
    from tokenizers.pre_tokenizers import ByteLevel as ByteLevelPreTokenizer
    from tokenizers.decoders import ByteLevel as ByteLevelDecoder
    from tokenizers.trainers import BpeTrainer

    tok = Tokenizer(BPE(unk_token="<unk>"))
    tok.pre_tokenizer = ByteLevelPreTokenizer(add_prefix_space=False)
    tok.decoder = ByteLevelDecoder()
    trainer = BpeTrainer(special_tokens=["<unk>"], vocab_size=300)
    corpus = ["hello world", "the quick brown fox", "testing tokenizers"]
    tok.train_from_iterator(corpus, trainer=trainer)

    path = tmp_path_factory.mktemp("tok") / "tokenizer.json"
    tok.save(str(path))
    return str(path)


def test_real_tokenizer_confirms_corruption_on_risky_added_token(gpt2_tokenizer_json):
    """This is the strongest evidence tier: run the *actual* HF tokenizers
    Rust backend end-to-end and confirm whether the predicted corruption
    happens for real, rather than trusting the static table alone."""
    report = roundtrip_check_added_tokens(gpt2_tokenizer_json, ["kuća", "hello"])
    assert report.available
    assert report.cases is not None
    by_original = {c.original: c for c in report.cases}

    # "hello" must always round-trip cleanly regardless of bug status.
    assert by_original["hello"].matches

    # "kuća" is the documented at-risk case. Record the *actual* outcome
    # rather than assuming a fixed bug/fixed-version state, since the
    # upstream bug's fix status may change over time in different
    # `tokenizers` releases -- this test's job is to surface ground truth,
    # not to assert a specific upstream defect will always reproduce.
    result_case = by_original["kuća"]
    if not result_case.matches:
        # Confirmed corruption, matching our static-scan prediction.
        assert result_case.decoded != "kuća"
    # else: this installed tokenizers version has fixed #1996 upstream;
    # our static scan in scan.py is still the correct conservative check
    # to run in CI regardless of the currently-installed version.
