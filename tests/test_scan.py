import json

import pytest

from bytelevel_guard.scan import (
    scan_strings,
    scan_token_string,
    scan_tokenizer_json_file,
)


def test_scan_token_string_flags_risky_token():
    findings = scan_token_string("kuća")
    assert len(findings) == 1
    assert findings[0].char == "ć"
    assert findings[0].corrupted_to == repr("\x07")


def test_scan_token_string_clean_token_has_no_findings():
    assert scan_token_string("hello") == []


def test_scan_strings_aggregates_across_multiple_inputs():
    result = scan_strings(["hello", "kuća", "world", "međa"])
    assert result.tokens_scanned == 4
    assert len(result.findings) == 2
    assert not result.is_clean


def test_scan_strings_all_clean():
    result = scan_strings(["hello", "world"])
    assert result.is_clean
    assert result.tokens_scanned == 2


def test_scan_tokenizer_json_added_tokens(tmp_path):
    data = {
        "added_tokens": [
            {"id": 50257, "content": "kuća", "special": False},
            {"id": 50258, "content": "clean_token", "special": False},
        ],
        "model": {"vocab": {"hello": 1, "world": 2}},
    }
    path = tmp_path / "tokenizer.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    result = scan_tokenizer_json_file(path)
    assert result.tokens_scanned == 4  # 2 added_tokens + 2 vocab entries
    assert len(result.findings) == 1
    assert result.findings[0].token_repr == repr("kuća")
    assert result.findings[0].source == str(path)


def test_scan_tokenizer_json_bare_vocab_file(tmp_path):
    data = {"hello": 0, "kuća": 1, "clean": 2}
    path = tmp_path / "vocab.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    result = scan_tokenizer_json_file(path)
    assert result.tokens_scanned == 3
    assert len(result.findings) == 1


def test_scan_tokenizer_json_vocab_as_list_pairs(tmp_path):
    data = {
        "added_tokens": [],
        "model": {"vocab": [["hello", 0], ["kuća", 1]]},
    }
    path = tmp_path / "tokenizer.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    result = scan_tokenizer_json_file(path)
    assert result.tokens_scanned == 2
    assert len(result.findings) == 1


def test_scan_tokenizer_json_missing_file_raises(tmp_path):
    path = tmp_path / "does_not_exist.json"
    with pytest.raises(FileNotFoundError):
        scan_tokenizer_json_file(path)


def test_scan_tokenizer_json_empty_added_tokens_and_vocab(tmp_path):
    data = {"added_tokens": [], "model": {"vocab": {}}}
    path = tmp_path / "tokenizer.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = scan_tokenizer_json_file(path)
    assert result.tokens_scanned == 0
    assert result.is_clean
