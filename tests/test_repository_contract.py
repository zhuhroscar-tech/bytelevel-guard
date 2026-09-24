"""Repository-level contract tests for release and project hygiene."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"
README = ROOT / "README.md"
README_ZH = ROOT / "README.zh-CN.md"
CHANGELOG = ROOT / "CHANGELOG.md"
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
CODEQL_WORKFLOW = ROOT / ".github" / "workflows" / "codeql.yml"

_VERSION_RE = re.compile(r'^version\s*=\s*"([^"]+)"', re.MULTILINE)


def _project_version() -> str:
    match = _VERSION_RE.search(PYPROJECT.read_text(encoding="utf-8"))
    assert match, "pyproject.toml must define [project].version"
    return match.group(1)


def test_required_project_files_exist():
    required = [
        README,
        README_ZH,
        CHANGELOG,
        ROOT / "LICENSE",
        PYPROJECT,
        CI_WORKFLOW,
        CODEQL_WORKFLOW,
    ]

    missing = [path.relative_to(ROOT).as_posix() for path in required if not path.is_file()]

    assert missing == []


def test_readmes_link_release_history_license_and_downloads():
    for path in (README, README_ZH):
        text = path.read_text(encoding="utf-8")

        assert "CHANGELOG.md" in text
        assert "LICENSE" in text or "License" in text or "许可证" in text
        assert "https://github.com/zhuhroscar-tech/bytelevel-guard/releases" in text
        assert "SHA256SUMS.txt" in text


def test_changelog_documents_current_version_and_prior_bugfixes():
    changelog = CHANGELOG.read_text(encoding="utf-8")
    version = _project_version()

    assert f"## v{version}" in changelog
    assert "## v0.1.4" in changelog
    assert "SPDX" in changelog
    assert "## v0.1.2" in changelog
    assert "malformed JSON" in changelog
    assert "## v0.1.1" in changelog
    assert "base-vocabulary false-positive" in changelog


def test_ci_exercises_tests_build_and_release_artifacts():
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")

    assert "python -m pytest" in workflow
    assert "python -m build" in workflow
    assert "bytelevel-guard --version" in workflow
    assert "sha256sum" in workflow
    assert "actions/upload-artifact" in workflow
    assert "dist/" in workflow


def test_codeql_workflow_analyzes_python():
    workflow = CODEQL_WORKFLOW.read_text(encoding="utf-8")

    assert "github/codeql-action/init" in workflow
    assert "languages: python" in workflow
