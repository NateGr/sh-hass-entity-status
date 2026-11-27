# Release Mechanism & Setup Plan

## How releases work

Run **Actions → Release → Run workflow** on `main`. Inputs: `bump` (patch/minor/major), optional explicit `version`, `prerelease`, `dry-run`, and `recover-version`.

1. `prepare` job (protected by the `release` environment) freezes `main`, picks the next version (highest of `manifest.json` and published GitHub releases, via `scripts/release.py`), and creates a local commit that changes **only** `manifest.json` (`SmartHass-Release: X.Y.Z` trailer).
2. The exact candidate is validated with the shared `.github/actions/validate` action (readiness, ruff, format, mypy, tests against minimum and latest fixture-supported Home Assistant, at least 80% integration coverage in each, hassfest, and HACS for public repositories) — the same action CI uses.
3. A short-lived GitHub App token (`contents: write`, this repo only) atomically pushes the release commit to `main` and the annotated `vX.Y.Z` tag. It aborts if `main` moved during validation.
4. `publish` job verifies the tag still points at the validated commit and creates the GitHub release with generated notes.

If publishing fails after the tag exists, rerun with `recover-version` set (no bump); `scripts/release.py recover` re-verifies the tagged commit.

### Prereleases for testers

A **prerelease** is a test version, not a production release. Select `prerelease` when running the workflow. It uses the chosen bump or explicit stable target version and numbers candidates automatically: for example, `1.0.12rc1`, then `1.0.12rc2`. Leave `version` blank to use the bump, or enter a target such as `1.0.12` (not the `rc` suffix).

The workflow validates a separate candidate commit whose manifest contains the prerelease version, pushes only its annotated tag, and publishes a GitHub release marked as a prerelease. It does **not** update `main` or mark the prerelease as the latest stable release. Testers can enable the repository's **Pre-release** switch in HACS; the prerelease must be newer than the latest stable release to be offered. See [Home Assistant's prerelease guide](https://contributors.home-assistant.io/marketplace/guides/releases/#pre-releases). The next stable release still follows the normal version selection and publishing path.

Use `dry-run` to validate without pushing or publishing. If publishing fails after a prerelease tag is pushed, use `recover-version` with the full version, for example `1.0.12rc1`; the workflow determines the release type from the version and validates the tagged candidate again.

To test a change before merging, run **Actions → Release → Run workflow**, select the feature branch, and enable `dry-run`. Enable `prerelease` to test prerelease version selection, or leave it off to test stable version selection. The branch dry run creates and validates a local candidate using the same release script and validation action, but it does not use the protected release environment or its App credentials, push a commit or tag, or publish a release. The candidate is based on the selected branch, not `main`; the actual push, token, and publication paths are not tested. Non-dry runs and recovery remain restricted to `main`.

The readiness check verifies integration files, metadata, the minimum Home Assistant version in `hacs.json`, a `homeassistant` pin in `requirements_test.txt` that equals that minimum, and integration tests. Readiness is enabled by `tool.smarthass.integration-ready = true` in `pyproject.toml`; releases run `python scripts/release.py check --require-integration`. Run `python scripts/release.py check` locally. Private repositories may run dry runs, but production releases require public visibility and HACS validation.

### Home Assistant compatibility

The minimum environment (`requirements_test.txt`, plugin `0.13.363`) tests the declared minimum, Home Assistant `2026.9.0`. The latest environment (`requirements/latest/requirements.txt`, plugin `0.13.375`) tests Home Assistant `2026.10.4`, the newest stable version supported by the plugin at the time of this change. Both use Python `3.14.2`, run the full suite and enforce 80% integration-only coverage. Validation checks the installed Home Assistant version against `hacs.json`, so changing the declared minimum without updating its fixture stack fails.

Dependabot checks the latest fixture plugin weekly and proposes updates to its separate requirements file. Review its pinned Home Assistant and Python versions, update the validation and release Python versions if required, and merge only after both suites pass. The minimum stack is excluded from automatic updates; update its plugin, pytest, pytest-asyncio, pytest-cov, and pytest-socket together only when intentionally changing the minimum. Ruff and mypy remain automatically updated.

CI also runs weekly and compares the newest stable Home Assistant release on PyPI, the Home Assistant version pinned by the newest fixture plugin, and the configured latest plugin. The update-check job fails visibly if the fixture plugin lags Home Assistant, if a plugin update has not been applied, or if metadata cannot be verified. Such a failure is a compatibility gap, not evidence that the integration is broken; the two pinned test jobs still run. At the time of this change, Home Assistant `2026.11.3` is newer than the fixture-supported `2026.10.4` and is **not** tested. Check the scheduled run logs and Dependabot PRs; GitHub notification settings determine how failures reach maintainers.

Replaces: `publish.yml`, `tag_release_pr_merge.yml`, `hacs.yml` (folded into the validate action), and `release.sh`. No more release PRs or ZIP asset; HACS installs from the tag (`hacs.json` has no `zip_release`).

## GitHub setup and protections

Pushes made with `GITHUB_TOKEN` cannot bypass branch protection, so the release commit uses a GitHub App token. Verify the following repository settings separately from code changes:

1. Install the release App on `NateGr/sh-hass-entity-status` with repository **Contents: read and write** and required metadata access. Avoid broader administration or workflow permissions.
2. Restrict the `release` environment to `main`. The current environment has no required reviewer; add one only if a manual approval step is desired.
3. Store the App client ID as environment variable `RELEASE_APP_CLIENT_ID` and its private key as environment secret `RELEASE_APP_PRIVATE_KEY`. Never commit or share the private key.
4. Require the `Validate` CI check and pull requests for `main`; allow the App to bypass that PR ruleset so it can push validated release commits.
5. To align with the chore tracker, separately protect `main` from deletion and force pushes without an App bypass, and protect `v*` tags from updates and deletion. Allow release tag creation. Review existing rules and bypass actors before changing them so legitimate releases remain possible; rulesets are not modified by this repository.

Actions are pinned to commits for reviewability, but their wrappers may run mutable upstream container images. A dry run does not exercise App token creation, the production push, or publication. After a controlled release, verify the release/tag SHA and installation in HACS.
