import json
import subprocess
import sys

import pytest


def run_cli(*args, cwd=None):
    return subprocess.run(
        [sys.executable, "-m", "bytelevel_guard.cli", *args],
        capture_output=True,
        text=True,
        cwd=cwd,
    )


def test_cli_version():
    result = run_cli("--version")
    assert result.returncode == 0
    assert "bytelevel-guard" in result.stdout


def test_cli_explain():
    result = run_cli("explain")
    assert result.returncode == 0
    assert "tokenizers#1996" in result.stdout or "1996" in result.stdout


def test_cli_check_strings_clean():
    result = run_cli("--no-color", "check-strings", "hello", "world")
    assert result.returncode == 0
    assert "clean" in result.stdout


def test_cli_check_strings_at_risk():
    result = run_cli("--no-color", "check-strings", "kuća", "hello")
    assert result.returncode == 1
    assert "at-risk" in result.stdout
    assert "kuća" in result.stdout


def test_cli_check_file_at_risk(tmp_path):
    data = {"added_tokens": [{"content": "kuća"}], "model": {"vocab": {}}}
    path = tmp_path / "tokenizer.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    result = run_cli("--no-color", "check", str(path))
    assert result.returncode == 1
    assert "kuća" in result.stdout


def test_cli_check_file_clean(tmp_path):
    data = {"added_tokens": [{"content": "hello"}], "model": {"vocab": {}}}
    path = tmp_path / "tokenizer.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    result = run_cli("--no-color", "check", str(path))
    assert result.returncode == 0


def test_cli_check_missing_file():
    result = run_cli("--no-color", "check", "/nonexistent/path/tokenizer.json")
    assert result.returncode == 2
    assert "not found" in result.stdout


def test_cli_no_command_errors():
    result = run_cli()
    assert result.returncode != 0
