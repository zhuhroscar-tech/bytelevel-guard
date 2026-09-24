# Changelog

All notable changes to `bytelevel-guard` are documented here.

## v0.1.5 — 2026-09-24

- Added this changelog so source checkouts expose release history without requiring GitHub UI access.
- Linked release history from both English and Chinese READMEs.
- Added repository-contract tests for required files, release/download links, changelog coverage, CI, CodeQL, and release artifacts.

## v0.1.4 — 2026-09-24

- Modernized packaging license metadata to the current SPDX format.
- Added `license-files` metadata and removed the deprecated MIT license classifier.
- Added regression coverage to keep packaging metadata current.

## v0.1.3 — 2026-09-23

- Added a real terminal screenshot of example CLI output to both English and Chinese READMEs.
- Kept this as a documentation-only release.

## v0.1.2 — 2026-09-19

- Fixed `check <path>` so directories, non-UTF-8 files, and malformed JSON now report clean CLI errors instead of unhandled Python tracebacks.
- Preserved exit code `2` for invalid/uncheckable inputs and worst-exit-code aggregation across multiple paths.
- Added regression tests for the CLI input-error paths.

## v0.1.1 — 2026-09-18

- Fixed a base-vocabulary false-positive scan bug where `tokenizer.json` checks scanned normal ByteLevel-BPE `model.vocab` entries.
- Limited `tokenizer.json` scanning to `added_tokens`, the actual surface for the tokenizers#1996 bug class.
- Kept bare `vocab.json` scanning exhaustive because that format has no added/base-token distinction.

## v0.1.0 — 2026-09-13

- Initial release of `bytelevel-guard`.
- Added the ByteLevel-BPE risky-character scanner, `check`, `check-strings`, and `explain` CLI commands.
- Added optional live round-trip verification against the `tokenizers` Rust backend, tests, CI, and packaged wheel/sdist artifacts.
