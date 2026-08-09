# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project aims to follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Added a dedicated HACS validation workflow for push and pull request checks on `main`.
- Added a repository security policy to support private vulnerability reporting.
- Added `mypy` and `pytest-cov` to pinned test dependencies.

### Changed
- Expanded CI to run Ruff lint, Ruff format check, mypy type checking, and pytest coverage reporting.
- Updated the open source readiness checklist to reflect completed CI, HACS, security, and governance setup.
- Refined coordinator and sensor typing to satisfy stricter static analysis in CI.

### Fixed
- Fixed coordinator lint and typing edge cases detected during CI hardening.
- Fixed a dependency pin conflict by aligning `pytest-cov` with the Home Assistant test stack.

## [1.0.5] - 2026-07-26

### Added
- First public release of SmartHass Entity Status.
- Entity availability monitoring with configurable suppression by Home Assistant label.
- Count and list sensors for unsuppressed and suppressed unavailable devices/entities.
- Service actions and refresh button for registry and polling operations.

### Changed
- Public project branding aligned to SmartHass Entity Status.
- CI and release automation prepared for tag-based publication.
