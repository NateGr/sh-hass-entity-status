# Release Mechanism & Setup Plan

## How releases work

Run **Actions → Release → Run workflow** on `main`. Inputs: `bump` (patch/minor/major), optional explicit `version`, `prerelease`, `dry-run`, and `recover-version`.

1. `prepare` job (protected by the `release` environment) freezes `main`, picks the next version (highest of `manifest.json` and published GitHub releases, via `scripts/release.py`), and creates a local commit that changes **only** `manifest.json` (`SmartHass-Release: X.Y.Z` trailer).
2. The exact candidate is validated with the shared `.github/actions/validate` action (readiness, ruff, format, mypy, pytest with at least 80% integration coverage, hassfest, and HACS for public repositories) — the same action CI uses.
3. A short-lived GitHub App token (`contents: write`, this repo only) atomically pushes the release commit to `main` and the annotated `vX.Y.Z` tag. It aborts if `main` moved during validation.
4. `publish` job verifies the tag still points at the validated commit and creates the GitHub release with generated notes.

If publishing fails after the tag exists, rerun with `recover-version` set (no bump); `scripts/release.py recover` re-verifies the tagged commit.

### Prereleases for testers

A **prerelease** is a test version, not a production release. Select `prerelease` when running the workflow. It uses the chosen bump or explicit stable target version and numbers candidates automatically: for example, `1.0.12rc1`, then `1.0.12rc2`. Leave `version` blank to use the bump, or enter a target such as `1.0.12` (not the `rc` suffix).

The workflow validates a separate candidate commit whose manifest contains the prerelease version, pushes only its annotated tag, and publishes a GitHub release marked as a prerelease. It does **not** update `main` or mark the prerelease as the latest stable release. Testers can enable the repository's **Pre-release** switch in HACS; the prerelease must be newer than the latest stable release to be offered. See [Home Assistant's prerelease guide](https://contributors.home-assistant.io/marketplace/guides/releases/#pre-releases). The next stable release still follows the normal version selection and publishing path.

Use `dry-run` to validate without pushing or publishing. If publishing fails after a prerelease tag is pushed, use `recover-version` with the full version, for example `1.0.12rc1`; the workflow determines the release type from the version and validates the tagged candidate again.

To test a change before merging, run **Actions → Release → Run workflow**, select the feature branch, and enable `dry-run`. Enable `prerelease` to test prerelease version selection, or leave it off to test stable version selection. The branch dry run creates and validates a local candidate using the same release script and validation action, but it does not use the protected release environment or its App credentials, push a commit or tag, or publish a release. The candidate is based on the selected branch, not `main`; the actual push, token, and publication paths are not tested. Non-dry runs and recovery remain restricted to `main`.

The readiness check verifies integration files, metadata, matching minimum Home Assistant versions, a pinned Home Assistant test plugin, and integration tests. Run `python scripts/release.py check` locally. Test with the pinned test dependencies; this plugin pin alone does not establish that the declared minimum Home Assistant version was tested. Private repositories may run dry runs, but production releases require public visibility and HACS validation.

Replaces: `publish.yml`, `tag_release_pr_merge.yml`, `hacs.yml` (folded into the validate action), and `release.sh`. No more release PRs or ZIP asset; HACS installs from the tag (`hacs.json` has no `zip_release`).

## GitHub setup and protections

Pushes made with `GITHUB_TOKEN` cannot bypass branch protection, so the release commit uses a GitHub App token. Verify the following repository settings separately from code changes:

1. Install the release App on `NateGr/sh-hass-entity-status` with repository **Contents: read and write** and required metadata access. Avoid broader administration or workflow permissions.
2. Restrict the `release` environment to `main`. The current environment has no required reviewer; add one only if a manual approval step is desired.
3. Store the App client ID as environment variable `RELEASE_APP_CLIENT_ID` and its private key as environment secret `RELEASE_APP_PRIVATE_KEY`. Never commit or share the private key.
4. Require the `Validate` CI check and pull requests for `main`; allow the App to bypass that PR ruleset so it can push validated release commits.
5. To align with the chore tracker, separately protect `main` from deletion and force pushes without an App bypass, and protect `v*` tags from updates and deletion. Allow release tag creation. Review existing rules and bypass actors before changing them so legitimate releases remain possible; rulesets are not modified by this repository.

Actions are pinned to commits for reviewability, but their wrappers may run mutable upstream container images. A dry run does not exercise App token creation, the production push, or publication. After a controlled release, verify the release/tag SHA and installation in HACS.
