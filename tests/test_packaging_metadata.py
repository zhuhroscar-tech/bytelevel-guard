"""Regression tests for current packaging license metadata."""
from __future__ import annotations

from pathlib import Path


def _pyproject_text() -> str:
    return (Path(__file__).resolve().parent.parent / "pyproject.toml").read_text()


def test_license_metadata_uses_spdx_string_and_license_files():
    text = _pyproject_text()

    assert 'license = "MIT"' in text
    assert 'license-files = ["LICENSE"]' in text
    assert "license = {" not in text


def test_deprecated_license_classifier_does_not_return():
    text = _pyproject_text()

    assert "License :: OSI Approved :: MIT License" not in text


def test_setuptools_floor_supports_spdx_license_metadata():
    text = _pyproject_text()

    assert 'requires = ["setuptools>=77", "wheel"]' in text


def test_project_urls_include_support_and_release_history_links():
    text = _pyproject_text()

    assert 'Homepage = "https://github.com/zhuhroscar-tech/bytelevel-guard"' in text
    assert 'Issues = "https://github.com/zhuhroscar-tech/bytelevel-guard/issues"' in text
    assert 'Changelog = "https://github.com/zhuhroscar-tech/bytelevel-guard/blob/main/CHANGELOG.md"' in text
