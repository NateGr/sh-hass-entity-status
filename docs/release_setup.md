# Release Mechanism & Setup Plan

## How releases work

Run **Actions → Release → Run workflow** on `main`. Inputs: `bump` (patch/minor/major), optional explicit `version`, `prerelease`, `dry-run`, and `recover-version`.

1. `prepare` job (protected by the `release` environment) freezes `main`, picks the next version (highest of `manifest.json` and published GitHub releases, via `scripts/release.py`), and creates a local commit that changes **only** `manifest.json` (`SmartHass-Release: X.Y.Z` trailer).
2. The exact candidate is validated with the shared `.github/actions/validate` action (ruff, format, mypy, pytest + coverage, HACS) — the same action CI uses.
3. A short-lived GitHub App token (`contents: write`, this repo only) atomically pushes the release commit to `main` and the annotated `vX.Y.Z` tag. It aborts if `main` moved during validation.
4. `publish` job verifies the tag still points at the validated commit and creates the GitHub release with generated notes.

If publishing fails after the tag exists, rerun with `recover-version` set (no bump); `scripts/release.py recover` re-verifies the tagged commit.

### Prereleases for testers

A **prerelease** is a test version, not a production release. Select `prerelease` when running the workflow. It uses the chosen bump or explicit stable target version and numbers candidates automatically: for example, `1.0.12rc1`, then `1.0.12rc2`. Leave `version` blank to use the bump, or enter a target such as `1.0.12` (not the `rc` suffix).

The workflow validates a separate candidate commit whose manifest contains the prerelease version, pushes only its annotated tag, and publishes a GitHub release marked as a prerelease. It does **not** update `main` or mark the prerelease as the latest stable release. Testers can enable the repository's **Pre-release** switch in HACS; the prerelease must be newer than the latest stable release to be offered. See [Home Assistant's prerelease guide](https://contributors.home-assistant.io/marketplace/guides/releases/#pre-releases). The next stable release still follows the normal version selection and publishing path.

Use `dry-run` to validate without pushing or publishing. If publishing fails after a prerelease tag is pushed, use `recover-version` with the full version, for example `1.0.12rc1`; the workflow determines the release type from the version and validates the tagged candidate again.

To test a change before merging, run **Actions → Release → Run workflow**, select the feature branch, and enable `dry-run`. Enable `prerelease` to test prerelease version selection, or leave it off to test stable version selection. The branch dry run creates and validates a local candidate using the same release script and validation action, but it does not use the protected release environment or its App credentials, push a commit or tag, or publish a release. The candidate is based on the selected branch, not `main`; the actual push, token, and publication paths are not tested. Non-dry runs and recovery remain restricted to `main`.

Replaces: `publish.yml`, `tag_release_pr_merge.yml`, `hacs.yml` (folded into the validate action), and `release.sh`. No more release PRs or ZIP asset; HACS installs from the tag (`hacs.json` has no `zip_release`).

## Manual implementation plan (cannot be automated from code)

Pushes made with `GITHUB_TOKEN` can't bypass branch protection, so the release commit is pushed with a GitHub App token. You said you'd like to reuse your existing GitHub App — that works; steps:

1. **Reuse the existing App** (or create one named e.g. `smarthass-release`). Under *Permissions → Repository*, grant only **Contents: Read & write** (Metadata read is implicit). Disable webhooks.
2. **Install** the App on `NateGr/sh-hass-entity-status` (Only select repositories).
3. **Generate a private key** (App settings → Private keys) and note the **Client ID** (starts with `Iv…`).
4. **Create the `release` environment**: Settings → Environments → New → `release`. Add yourself as a required reviewer; restrict deployment branches to `main`.
5. **Store credentials in that environment**: variable `RELEASE_APP_CLIENT_ID`, secret `RELEASE_APP_PRIVATE_KEY` (full PEM). Delete the downloaded key file afterwards.
6. **Branch protection / ruleset for `main`**: keep PRs + required status check `Validate`, and add the App as a **bypass actor** (rulesets → Bypass list → the App) so it may push the release commit directly. Without this the push fails.
7. **Tag ruleset** (optional, recommended): restrict creation of `v*` tags to the App/admins and block deletion/updates.
8. Merge this PR, then trigger **Release** with `dry-run: true` first to check validation, then a real run.
9. Remove obsolete config: any `release/v*` branch rules, auto-merge settings used by the old release PR flow, and delete stale `release/*` branches.
10. If the existing App is also used elsewhere, consider whether the private key is already stored in other repos; a repo-specific key/secret is not required but environment-scoped secrets are advised.

Note: the workflow needs `vars.RELEASE_APP_CLIENT_ID`; if your App tooling only offers the numeric App ID, replace `client-id` with `app-id` in `release.yml`.
