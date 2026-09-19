import json

import pytest

from bytelevel_guard.cli import main


def test_cli_version(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])
    assert exc_info.value.code == 0
    assert "bytelevel-guard" in capsys.readouterr().out


def test_cli_explain(capsys):
    rc = main(["explain"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "tokenizers#1996" in out or "1996" in out


def test_cli_check_strings_clean(capsys):
    rc = main(["--no-color", "check-strings", "hello", "world"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "clean" in out


def test_cli_check_strings_at_risk(capsys):
    rc = main(["--no-color", "check-strings", "kuća", "hello"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "at-risk" in out
    assert "kuća" in out


def test_cli_check_file_at_risk(tmp_path, capsys):
    data = {"added_tokens": [{"content": "kuća"}], "model": {"vocab": {}}}
    path = tmp_path / "tokenizer.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    rc = main(["--no-color", "check", str(path)])
    out = capsys.readouterr().out
    assert rc == 1
    assert "kuća" in out


def test_cli_check_file_clean(tmp_path, capsys):
    data = {"added_tokens": [{"content": "hello"}], "model": {"vocab": {}}}
    path = tmp_path / "tokenizer.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    rc = main(["--no-color", "check", str(path)])
    assert rc == 0


def test_cli_check_missing_file(capsys):
    rc = main(["--no-color", "check", "/nonexistent/path/tokenizer.json"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "not found" in out


def test_cli_check_directory_path_reports_clean_error(tmp_path, capsys):
    # Regression: passing a directory (e.g. from a shell glob or a
    # mistaken `check .`) must not crash with an unhandled
    # IsADirectoryError traceback -- it should report a clean CLI error
    # and move on, like the existing missing-file case does.
    rc = main(["--no-color", "check", str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 2
    assert "Traceback" not in out
    assert "not a file" in out or "directory" in out


def test_cli_check_invalid_json_reports_clean_error(tmp_path, capsys):
    # Regression: a malformed/non-JSON file must not crash with an
    # unhandled json.JSONDecodeError traceback.
    bad = tmp_path / "broken.json"
    bad.write_text("not json{{{", encoding="utf-8")

    rc = main(["--no-color", "check", str(bad)])
    out = capsys.readouterr().out
    assert rc == 2
    assert "Traceback" not in out
    assert "invalid JSON" in out or "not valid JSON" in out


def test_cli_check_non_utf8_file_reports_clean_error(tmp_path, capsys):
    # Regression: a file that is not valid UTF-8 must not crash with an
    # unhandled UnicodeDecodeError traceback.
    bad = tmp_path / "binary.json"
    bad.write_bytes(b"\xff\xfe\x00\x01garbage")

    rc = main(["--no-color", "check", str(bad)])
    out = capsys.readouterr().out
    assert rc == 2
    assert "Traceback" not in out
    assert "decode" in out or "UTF-8" in out or "utf-8" in out


def test_cli_check_multiple_paths_worst_code_includes_read_error(tmp_path, capsys):
    # A read/parse error on one path must still combine correctly with a
    # genuine at-risk finding on another path via the existing max()
    # exit-code aggregation (2 not-found/error > 1 at-risk > 0 clean).
    risky = tmp_path / "risky.json"
    risky.write_text(
        json.dumps({"added_tokens": [{"content": "kuća"}], "model": {"vocab": {}}}),
        encoding="utf-8",
    )
    bad = tmp_path / "broken.json"
    bad.write_text("not json{{{", encoding="utf-8")

    rc = main(["--no-color", "check", str(risky), str(bad)])
    out = capsys.readouterr().out
    assert rc == 2
    assert "kuća" in out
    assert "Traceback" not in out


def test_cli_check_multiple_paths_takes_worst_exit_code(tmp_path, capsys):
    # Regression: _cmd_check must return the *max* exit code across all
    # paths (0 clean < 1 at-risk < 2 not-found), not just the last path's
    # result -- this exercises the exit_code = max(exit_code, rc) branch
    # with a clean file processed before a risky one.
    clean = tmp_path / "clean.json"
    clean.write_text(
        json.dumps({"added_tokens": [{"content": "hello"}], "model": {"vocab": {}}}),
        encoding="utf-8",
    )
    risky = tmp_path / "risky.json"
    risky.write_text(
        json.dumps({"added_tokens": [{"content": "kuća"}], "model": {"vocab": {}}}),
        encoding="utf-8",
    )

    rc = main(["--no-color", "check", str(clean), str(risky)])
    out = capsys.readouterr().out
    assert rc == 1
    assert "kuća" in out


def test_cli_no_command_errors():
    with pytest.raises(SystemExit) as exc_info:
        main([])
    assert exc_info.value.code != 0


def test_cli_no_color_flag_suppresses_ansi(capsys):
    rc = main(["--no-color", "check-strings", "kuća"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "\033[" not in out


def test_cli_color_forced_via_env_emits_ansi(monkeypatch, capsys):
    monkeypatch.setenv("FORCE_COLOR", "1")
    rc = main(["check-strings", "kuća"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "\033[" in out
