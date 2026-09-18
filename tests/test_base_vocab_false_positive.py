"""Regression test for the base-vocabulary false-positive gap.

bytelevel-guard's documented CI-gate use case is `check tokenizer.json`
returning exit 0 for a clean vocabulary and exit 1 only for genuine
added-token corruption risk (see README "Returns nonzero exit codes for
use in CI"). But the underlying bug class (tokenizers#1996) only affects
tokens added via add_tokens()/added_tokens -- literal characters that
bypass the normal ByteLevel ENCODE step. Tokens that are already part of
the base BPE vocabulary (model.vocab) arrived there *through* the correct
byte-level encode/decode pipeline and are expected, by design, to contain
remapped characters like the space marker 'Ġ' (U+0120) in the vast
majority of real-world entries -- that is not a corruption risk, it is
how ByteLevel-BPE works.

Before this fix, scan_tokenizer_json_file() flattened added_tokens and
model.vocab into one list and scored every hit as an actionable "at
risk" finding, so ANY real GPT-2/RoBERTa/Qwen-family tokenizer.json --
even one with zero added_tokens and therefore zero actual corruption
risk -- would report dozens of false-positive findings and exit 1,
making the tool's core documented workflow non-functional against real
vocabularies.
"""
import json

from bytelevel_guard.scan import scan_tokenizer_json_file


def test_clean_tokenizer_with_zero_added_tokens_is_reported_clean(tmp_path):
    """A tokenizer.json with NO added_tokens has zero actual corruption
    risk (the bug class requires a literal remapped char in an added
    token), even though its base vocab legitimately contains the
    space-marker character 'Ġ' (U+0120, the remap of byte 0x20) in most
    entries -- completely normal ByteLevel-BPE encoding, not a finding.
    """
    data = {
        "added_tokens": [],
        "model": {
            "vocab": {
                "Ġthe": 1,
                "Ġand": 2,
                "Ġof": 3,
                "Ġto": 4,
                "Ġin": 5,
                "hello": 6,
                "world": 7,
            }
        },
    }
    path = tmp_path / "tokenizer.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    result = scan_tokenizer_json_file(path)

    assert result.is_clean, (
        f"expected is_clean=True (0 added_tokens -> 0 real risk) but got "
        f"{len(result.findings)} false-positive finding(s) from normal "
        f"base-vocab byte-remap markers: "
        f"{[f.token_repr for f in result.findings]}"
    )
