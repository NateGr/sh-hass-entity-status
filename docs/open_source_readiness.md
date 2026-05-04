# Open Source Readiness — SmartHass Entity Status

This document is a complete, prioritised task list for making this repository publicly open source, along with guidance on how to maintain, build, and operate it long-term — including CI/CD pipelines and pull-request processes.

---

## Table of Contents

1. [Repository Housekeeping](#1-repository-housekeeping)
2. [GitHub Repository Settings](#2-github-repository-settings)
3. [Community Health Files](#3-community-health-files)
4. [CI/CD Pipelines](#4-cicd-pipelines)
5. [Pull Request Process](#5-pull-request-process)
6. [Release Workflow](#6-release-workflow)
7. [Build and Test Locally](#7-build-and-test-locally)
8. [Ongoing Maintenance](#8-ongoing-maintenance)
9. [HACS Submission](#9-hacs-submission)
10. [Summary Checklist](#10-summary-checklist)

---

## 1. Repository Housekeeping

These files must exist before the repo goes public. They signal a healthy, welcoming project to potential contributors and users.

### 1.1 Add a LICENSE file

- **Action:** Create a `LICENSE` file in the root of the repository.
- **Recommended licence:** MIT — it is the most permissive and widely accepted choice for Home Assistant custom integrations.
- **How:** Copy the [MIT licence template](https://choosealicense.com/licenses/mit/), replace `[year]` and `[fullname]` with the current year and your name/organisation.
- **Why it matters:** Without a licence, the code is legally "all rights reserved" even if publicly visible. A licence is required before accepting any contributions.

### 1.2 Add a SECURITY policy

- **Action:** Create `.github/SECURITY.md`.
- **Contents to include:**
  - Supported versions (which versions receive security fixes).
  - Instructions for reporting a vulnerability privately (e.g. via GitHub's [private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing/privately-reporting-a-security-vulnerability) feature, or a dedicated email).
  - Expected response time (e.g. "we aim to respond within 72 hours").
- **Why it matters:** GitHub displays a "Report a vulnerability" button on the Security tab once this file is present. It keeps vulnerability reports out of public issues.

### 1.3 Add a CODE_OF_CONDUCT

- **Action:** Create `.github/CODE_OF_CONDUCT.md`.
- **Recommended standard:** [Contributor Covenant v2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/) — industry standard, widely recognised.
- **Why it matters:** Sets behavioural expectations and makes the project welcoming to all contributors.

### 1.4 Expand CONTRIBUTING guide

- **Action:** Create `.github/CONTRIBUTING.md` (moves the brief section in `README.md` to its own dedicated file and expands it).
- **Contents to include:**
  - How to set up a local development environment (Python version, virtual env, `pip install -r requirements_test.txt`).
  - How to run the test suite (`python -m pytest tests/ -v`).
  - Coding style guide (see linting section in CI below).
  - How to submit a bug report (link to issue template).
  - How to propose a new feature (link to feature request template).
  - PR checklist: tests pass, new behaviour has tests, `ruff` linting passes, `manifest.json` version not bumped manually.
  - Commit message convention (e.g. [Conventional Commits](https://www.conventionalcommits.org/)).

### 1.5 Add GitHub Issue Templates

- **Action:** Create `.github/ISSUE_TEMPLATE/` directory with the following templates:
  - `bug_report.yml` — structured bug report: HA version, integration version, steps to reproduce, expected vs actual behaviour, logs.
  - `feature_request.yml` — structured feature request: problem statement, proposed solution, alternatives considered.
  - `config.yml` — disables blank issues and adds a link to documentation.
- **Why it matters:** Structured templates dramatically reduce back-and-forth when triaging issues.

### 1.6 Add a Pull Request Template

- **Action:** Create `.github/pull_request_template.md`.
- **Contents to include:**
  - Summary of changes.
  - Related issue number (`Closes #NNN`).
  - Checklist: tests added/updated, linting passes, documentation updated if applicable, `manifest.json` version not bumped.
- **Why it matters:** Ensures every PR has the minimum context needed to review it efficiently.

### 1.7 Update `.gitignore`

- **Action:** Extend the existing `.gitignore` to also ignore:
  - `.env`, `.env.*` (prevent accidental secret commits)
  - `.mypy_cache/`
  - `.ruff_cache/`
  - `htmlcov/` (coverage HTML reports)
  - `.coverage`
  - `*.log`

### 1.8 Pin Python and dependency versions

- **Action:** Create a `pyproject.toml` (or extend `requirements_test.txt`) that pins test dependency versions (e.g. `pytest==8.x.x`, `pytest-homeassistant-custom-component==x.y.z`).
- **Why it matters:** Unpinned dependencies cause CI to break randomly when upstream packages release breaking changes.

---

## 2. GitHub Repository Settings

Configure these settings in **Settings** on the GitHub repository page before going public.

### 2.1 Branch Protection on `main`

Go to **Settings → Branches → Add branch protection rule** for `main`:

| Setting | Value |
|---|---|
| Require a pull request before merging | ✅ Enabled |
| Required approvals | 1 (can be 0 if solo maintainer, but 1 recommended) |
| Dismiss stale pull request approvals when new commits are pushed | ✅ Enabled |
| Require status checks to pass before merging | ✅ Enabled |
| Required status checks | `CI / test` (see CI section), `CI / lint` |
| Require branches to be up to date before merging | ✅ Enabled |
| Do not allow bypassing the above settings | ✅ Recommended even for admins |
| Restrict who can push to matching branches | ✅ Only you / your org team |

### 2.2 Repository topics and description

- Add relevant GitHub topics: `home-assistant`, `hacs`, `custom-component`, `python`, `iot`.
- Write a clear one-line repository description visible on the repo homepage.

### 2.3 Enable GitHub Discussions

- **Settings → General → Features → Discussions**: Enable.
- Create discussion categories: `Announcements`, `Q&A`, `Ideas`, `Show and Tell`.
- This gives users a place to ask questions without cluttering the issue tracker.

### 2.4 Dependabot

- **Action:** Create `.github/dependabot.yml`:
  ```yaml
  version: 2
  updates:
    - package-ecosystem: "pip"
      directory: "/"
      schedule:
        interval: "weekly"
    - package-ecosystem: "github-actions"
      directory: "/"
      schedule:
        interval: "weekly"
  ```
- **Why it matters:** Keeps test dependencies and GitHub Actions up to date automatically, including security patches.

### 2.5 GitHub Security Features

Enable in **Settings → Security**:
- **Dependency graph** — required for Dependabot.
- **Dependabot alerts** — notifies you of vulnerable dependencies.
- **Dependabot security updates** — auto-creates PRs for security fixes.
- **Secret scanning** — detects accidentally committed credentials.

---

## 3. Community Health Files

GitHub surfaces a community profile score at **Insights → Community Standards**. Completing all items below maximises that score and signals project maturity.

| File | Location | Status |
|---|---|---|
| `README.md` | root | ✅ Exists — review for completeness |
| `LICENSE` | root | ❌ Must add |
| `CODE_OF_CONDUCT.md` | `.github/` | ❌ Must add |
| `CONTRIBUTING.md` | `.github/` | ❌ Must add |
| `SECURITY.md` | `.github/` | ❌ Must add |
| Issue templates | `.github/ISSUE_TEMPLATE/` | ❌ Must add |
| PR template | `.github/pull_request_template.md` | ❌ Must add |

---

## 4. CI/CD Pipelines

Create a `.github/workflows/` directory. Below are the recommended GitHub Actions workflows.

### 4.1 CI Workflow (Test + Lint on every push and PR)

**File:** `.github/workflows/ci.yml`

**Triggers:** `push` to any branch, `pull_request` targeting `main`.

**Jobs:**

#### `lint` job
1. Check out the code.
2. Set up Python (e.g. `3.12`).
3. Install `ruff`.
4. Run `ruff check .` — fails the build on lint errors.
5. Run `ruff format --check .` — fails the build on formatting violations.

**Why `ruff`:** It is the standard HA ecosystem linter, extremely fast, and covers both `flake8`-style checks and `isort` formatting in one tool.

#### `type-check` job
1. Check out the code.
2. Set up Python.
3. Install `mypy` and stubs.
4. Run `mypy custom_components/sh_entity_status/ --ignore-missing-imports`.

#### `test` job
1. Check out the code.
2. Set up Python (matrix across `3.12` and `3.13` to future-proof against HA's Python upgrades).
3. Install dependencies: `pip install -r requirements_test.txt`.
4. Run `python -m pytest tests/ -v --cov=custom_components/sh_entity_status --cov-report=xml`.
5. Upload coverage report as an artifact (optional: send to Codecov).

**Outcome:** Every PR is blocked from merging if any of these checks fail.

### 4.2 Release Workflow (Automated on Git Tag)

**File:** `.github/workflows/release.yml`

**Trigger:** `push` of a tag matching `v*.*.*`.

**Jobs:**

1. Check out the code.
2. Extract version from the tag (`${GITHUB_REF_NAME#v}`).
3. Update `manifest.json` `version` field using `jq` (replaces the manual step in `release.sh`).
4. Commit the manifest change back to the branch (or include it as a release artefact without committing, depending on preference).
5. Build the integration zip: `zip -r sh_entity_status.zip custom_components/sh_entity_status/`.
6. Create a GitHub Release using the `softprops/action-gh-release` action, attaching the zip.
7. Post a release note summary (optionally generated from `CHANGELOG.md` if one is maintained).

**Note:** This automates and replaces the current `release.sh` script. The manual script can remain as a local convenience but the CI pipeline should be the canonical release mechanism.

### 4.3 HACS Validation Workflow

**File:** `.github/workflows/hacs.yml`

**Trigger:** `push` to `main` and `pull_request` targeting `main`.

**Job:**
- Uses the official `hacs/action` action to validate `hacs.json`, `manifest.json`, and overall HACS compatibility.
- This is required if you want the integration to be listed in the official HACS default repository.

```yaml
- uses: hacs/action@main
  with:
    category: integration
```

### 4.4 Stale Issue / PR Management

**File:** `.github/workflows/stale.yml`

**Trigger:** `schedule` (runs daily via cron).

**Job:**
- Uses `actions/stale` to:
  - Mark issues inactive for 60 days as `stale`.
  - Close stale issues after a further 14 days without activity.
  - Exempt issues labelled `pinned` or `security`.
  - Apply a gentle comment when marking stale.

---

## 5. Pull Request Process

Once branch protection and CI are in place, establish a clear PR lifecycle.

### 5.1 PR Lifecycle

```
Fork / branch  →  Develop  →  Open PR  →  CI checks  →  Review  →  Merge  →  Release
```

1. **Branch naming convention:** `feature/<short-description>`, `fix/<short-description>`, `docs/<short-description>`, `chore/<short-description>`.
2. **Draft PRs:** Encourage contributors to open a draft PR early for visibility and early feedback before the work is complete.
3. **CI must pass:** All three jobs (`lint`, `type-check`, `test`) must be green before a PR is eligible for review.
4. **Review:** At least one approving review required (from you, or a designated maintainer). Use GitHub's review tools — line comments, suggestions, request changes.
5. **Merge strategy:** Use **Squash and merge** for feature/fix PRs (keeps `main` history clean with one commit per PR). Use **Merge commit** for release PRs (preserves the tag relationship). Configure this in **Settings → General → Pull Requests**.
6. **Commit message on squash:** Use the PR title, which should follow Conventional Commits: `feat: add time-based suppression`, `fix: handle missing area gracefully`, `docs: update contributing guide`.

### 5.2 Labelling PRs and Issues

Create and consistently apply labels:

| Label | Description |
|---|---|
| `bug` | Confirmed defect |
| `enhancement` | New feature or improvement |
| `documentation` | Documentation-only change |
| `good first issue` | Suitable entry point for new contributors |
| `help wanted` | Maintainer is seeking community help |
| `question` | Not a bug or feature — a support question |
| `wontfix` | Intentionally not going to be addressed |
| `dependencies` | Dependency update (Dependabot) |
| `stale` | Automatically applied by the stale workflow |

### 5.3 Issue Triage

Aim to triage (label + respond) new issues within 48–72 hours. A brief acknowledgement comment maintains community trust even if a fix is weeks away.

---

## 6. Release Workflow

### 6.1 Versioning

- Follow [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH`.
  - **MAJOR**: breaking changes to sensors, services, or config options.
  - **MINOR**: new features that are backward-compatible.
  - **PATCH**: bug fixes and internal improvements.

### 6.2 CHANGELOG

- **Action:** Create `CHANGELOG.md` in the root.
- Follow the [Keep a Changelog](https://keepachangelog.com/) format.
- Add an `[Unreleased]` section at the top; when releasing, rename it to `[x.y.z] - YYYY-MM-DD`.
- Update the changelog as part of every PR that changes user-facing behaviour.

### 6.3 Release Steps (after CI automation is in place)

1. Update `CHANGELOG.md` — move `[Unreleased]` items under the new version heading.
2. Commit to `main`: `git commit -m "chore: prepare release vX.Y.Z"`.
3. Push a version tag: `git tag vX.Y.Z && git push origin vX.Y.Z`.
4. The `release.yml` workflow fires automatically:
   - Updates `manifest.json` with the new version.
   - Builds and attaches the zip.
   - Creates the GitHub Release.
5. HACS users receive the update automatically once the release is published.
6. Announce in GitHub Discussions if desired.

### 6.4 What to do with `release.sh`

- Keep it as a local fallback convenience script for offline use.
- Document it as "local only" in its header comment — the canonical release flow is via the CI pipeline.
- Long term, it can be retired once the team is comfortable with the automated workflow.

---

## 7. Build and Test Locally

### 7.1 Prerequisites

- Python 3.12 or 3.13
- `git`
- `jq` (for the `release.sh` script only)

### 7.2 Development Setup

```bash
# Clone your fork
git clone https://github.com/<your-fork>/sh-hass-entity-status.git
cd sh-hass-entity-status

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install test and lint dependencies
pip install -r requirements_test.txt
pip install ruff mypy
```

### 7.3 Run Tests

```bash
python -m pytest tests/ -v
```

With coverage:

```bash
python -m pytest tests/ -v --cov=custom_components/sh_entity_status --cov-report=term-missing
```

### 7.4 Run Linting

```bash
ruff check .
ruff format --check .
```

Auto-fix:

```bash
ruff check --fix .
ruff format .
```

### 7.5 Type Checking

```bash
mypy custom_components/sh_entity_status/ --ignore-missing-imports
```

### 7.6 Install in Home Assistant for Manual Testing

1. Copy `custom_components/sh_entity_status/` into your HA config's `custom_components/` directory.
2. Restart Home Assistant.
3. Add the integration via **Settings → Devices & Services → Add Integration → SmartHass Entity Status**.

---

## 8. Ongoing Maintenance

### 8.1 Dependency and HA Version Updates

- **Dependabot** (configured in §2.4) will open PRs automatically for `requirements_test.txt` upgrades.
- When a new Home Assistant release comes out:
  - Update the `homeassistant` minimum version in `manifest.json` and `hacs.json` only if new HA APIs are required.
  - Run the full test suite against the new HA version by bumping `pytest-homeassistant-custom-component` in `requirements_test.txt`.
  - Document any breaking API changes in `CHANGELOG.md`.

### 8.2 Test Coverage

- Aim to keep test coverage above **80%** for `coordinator.py` (the core logic).
- Enforce a minimum coverage threshold in CI by adding `--cov-fail-under=80` to the pytest command.
- Add regression tests for every bug fix — include the test in the same PR as the fix.

### 8.3 Issue Backlog

- Review the backlog in `docs/requirements_backlog.md` at regular intervals (e.g. quarterly).
- Label backlog items as GitHub issues with appropriate priority labels so the community can contribute.
- Transfer `good first issue` items to GitHub Issues to attract contributors.

### 8.4 Security

- Review and action Dependabot security alerts promptly (within 7 days for high/critical).
- Respond to private vulnerability reports within 72 hours (even if only to acknowledge receipt).
- When a security fix is released, publish a GitHub Security Advisory so users are notified.

### 8.5 Documentation

- Keep `README.md` accurate after every user-facing change.
- The `docs/` directory already contains architecture and developer specs — keep them updated alongside code changes.
- Consider adding a `docs/troubleshooting.md` for common problems and their solutions as the user base grows.

---

## 9. HACS Submission

Once the above items are complete, the integration can be submitted to the official HACS default repository.

### 9.1 Prerequisites for HACS Default Listing

HACS has a strict set of requirements — the full list is at [hacs.xyz/docs/publish/integration](https://hacs.xyz/docs/publish/integration). Key requirements include:

- [ ] Repository is public.
- [ ] `hacs.json` is present and valid.
- [ ] `manifest.json` includes `documentation`, `issue_tracker`, and `codeowners`.
- [ ] At least one published GitHub Release with a version tag (`v*.*.*`).
- [ ] A `README.md` with installation and configuration instructions.
- [ ] All HACS validation checks pass (use the `hacs/action` CI workflow from §4.3).
- [ ] The integration follows HA naming conventions (no duplicate domains, correct `iot_class`).

### 9.2 Submission Steps

1. Fork [hacs/default](https://github.com/hacs/default).
2. Add your repository URL to the appropriate JSON file (e.g. `integration`).
3. Open a PR — the HACS team will review it against their criteria.
4. Address any feedback and await approval.

---

## 10. Summary Checklist

Use this as your go-to task list. Items are ordered roughly by priority.

### Immediate (before making repo public)

- [ ] Add `LICENSE` (MIT recommended) to the repository root.
- [ ] Create `.github/SECURITY.md` with vulnerability reporting instructions.
- [ ] Create `.github/CODE_OF_CONDUCT.md` (Contributor Covenant v2.1).
- [ ] Create `.github/CONTRIBUTING.md` with local setup, test, and lint instructions.
- [ ] Create `.github/ISSUE_TEMPLATE/bug_report.yml`.
- [ ] Create `.github/ISSUE_TEMPLATE/feature_request.yml`.
- [ ] Create `.github/ISSUE_TEMPLATE/config.yml`.
- [ ] Create `.github/pull_request_template.md`.
- [ ] Extend `.gitignore` (`.env`, `.mypy_cache`, `.ruff_cache`, `htmlcov`, `.coverage`).

### Before First External Contribution

- [ ] Enable branch protection on `main` (require PR + CI checks).
- [ ] Create `.github/workflows/ci.yml` (lint + type-check + test jobs).
- [ ] Create `.github/workflows/hacs.yml` (HACS validation).
- [ ] Create `.github/dependabot.yml`.
- [ ] Enable GitHub Security features (Dependabot alerts, secret scanning).
- [ ] Add repository topics and description.
- [ ] Enable GitHub Discussions.

### Before First Public Release

- [ ] Create `CHANGELOG.md` and populate with changes from v1.0.0 to present.
- [ ] Create `.github/workflows/release.yml` (automated release on tag push).
- [ ] Verify `hacs.json` passes HACS validation workflow.
- [ ] Create a test coverage minimum threshold in the CI workflow.

### Ongoing

- [ ] Pin test dependency versions.
- [ ] Create `.github/workflows/stale.yml`.
- [ ] Add GitHub issue labels.
- [ ] Transfer backlog items to GitHub Issues with labels.
- [ ] Submit to HACS default repository once all prerequisites are met.
