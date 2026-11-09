# Release Mechanism Code Walkthrough

## Overview
PR #46 introduces a GitHub App-based release mechanism that automates versioning, validation, tagging, and publishing of releases. It replaces the old PR-based release flow with a direct-push approach using GitHub App credentials.

**Key Innovation**: Uses a short-lived GitHub App token to push the release commit and tag, bypassing branch protection rules that normally block direct pushes.

---

## Architecture Overview

```
User Action: Trigger Release workflow
    ↓
[Prepare Job] - Protected by "release" environment
    ├─ Validates we're on main
    ├─ Freezes main commit SHA
    ├─ Determines next version (highest of manifest + published releases)
    ├─ Creates local commit that ONLY changes manifest.json
    ├─ Runs full validation (same as CI: ruff, mypy, pytest, HACS)
    ├─ Creates annotated git tag
    ├─ Pushes commit + tag with GitHub App token (bypasses branch protection)
    └─ Outputs: version, candidate commit SHA
         ↓
[Publish Job] - Conditional (skipped on dry-run)
    ├─ Verifies tag still points to the validated commit
    ├─ Creates GitHub release with auto-generated release notes
    └─ Publishes to GitHub releases (consumed by HACS)
```

---

## File Structure

### 1. `.github/workflows/release.yml` - Main Orchestration
The GitHub Actions workflow that triggers the entire release process.

**Key Inputs:**
```yaml
inputs:
  bump: [patch, minor, major]        # Version increment type
  version: string                     # Optional: explicit version override (X.Y.Z)
  dry-run: boolean                    # Validate without pushing
  recover-version: string             # Re-publish existing tag if publish failed
```

**Two Jobs:**

#### Job 1: `prepare` (Protected by `release` environment)
```yaml
environment: release                  # Requires manual approval + limited to main branch
permissions:
  contents: read                       # Read-only initially; token scoped later
```

**Steps in prepare job:**

1. **Check release context** (bash validation)
   ```bash
   # Ensures:
   # - Workflow runs only on main branch
   # - Only runs in the official NateGr/sh-hass-entity-status repo
   # - Can't specify both new version AND recover version
   ```

2. **Check out frozen main commit**
   ```yaml
   ref: ${{ github.sha }}             # Checkout the exact commit that triggered the workflow
   fetch-depth: 0                      # Full history (need all tags for version calculation)
   persist-credentials: false          # Don't use default GitHub token
   ```
   This is crucial: we freeze main at this exact commit, then validate against it. If main changes during validation, we abort.

3. **Set up Python**
   ```yaml
   python-version: '3.13'             # Must match requirements in release.py
   ```

4. **Freeze base commit**
   ```bash
   echo "sha=$(git rev-parse HEAD)" >> "$GITHUB_OUTPUT"
   ```
   Saves the exact main commit SHA to compare against later.

5. **Select version or recover existing tag**
   This is the intelligence step. Runs `scripts/release.py`:
   ```bash
   # Path 1: If recover-version specified → scripts/release.py recover --version X.Y.Z
   #   Finds existing tag and its commit for re-publication
   # Path 2: Otherwise → scripts/release.py prepare --bump {patch/minor/major}
   #   Calculates next version and creates release commit
   ```

6. **Create local release commit or check out recovery commit**
   ```bash
   if recover:
     git checkout --detach "$RECOVERY_COMMIT"      # Reuse existing release commit
   else:
     git config user.name "smarthass-release[bot]"
     git config user.email "smarthass-release[bot]@users.noreply.github.com"
     git add custom_components/sh_entity_status/manifest.json
     git commit -m "Release v$VERSION" -m "SmartHass-Release: $VERSION"
   ```
   **Constraint**: Commit must ONLY change `manifest.json` (enforced by verify_release_metadata)

7. **Validate exact release candidate**
   ```yaml
   uses: ./.github/actions/validate     # Runs: ruff, format, mypy, pytest, HACS
   ```
   This is the same validation CI uses. If it changes any file, the release fails (see next step).

8. **Verify candidate was not modified by validation**
   ```bash
   [[ "$(git rev-parse HEAD)" == "$CANDIDATE" ]] || exit 1   # SHA didn't change
   git diff --exit-code                                        # No working directory changes
   git diff --cached --exit-code                               # No staged changes
   ```
   This ensures the validation action didn't modify anything (it shouldn't, but verify).

9. **Create narrowly scoped App token**
   ```yaml
   if: ${{ !inputs.dry-run && inputs.recover-version == '' }}  # Only on real release, not recovery
   uses: actions/create-github-app-token@v3
   with:
     client-id: ${{ vars.RELEASE_APP_CLIENT_ID }}              # App credentials from environment
     private-key: ${{ secrets.RELEASE_APP_PRIVATE_KEY }}
     owner: ${{ github.repository_owner }}
     repositories: sh-hass-entity-status                       # Token scoped to ONLY this repo
     permission-contents: write                                # Only Contents: write permission
   ```
   This generates a short-lived token that can:
   - ✅ Push to this repo's main branch
   - ❌ Cannot access other repos
   - ❌ Cannot modify org settings
   - ❌ Cannot trigger other workflows

10. **Push validated commit and tag atomically**
    ```yaml
    if: ${{ !inputs.dry-run && inputs.recover-version == '' }}  # Skip on dry-run or recovery
    ```
    This is the critical step. Uses App token to push:
    ```bash
    # Verify main hasn't moved (catch race condition)
    [[ "$(git rev-parse origin/main)" == "$BASE_COMMIT" ]]
    
    # Verify candidate is built on frozen commit
    [[ "$(git rev-parse HEAD^)" == "$BASE_COMMIT" ]]
    
    # Verify only manifest.json changed
    [[ "$(git diff-tree --no-commit-id --name-only -r HEAD)" == "..." ]]
    
    # Create annotated tag (required for recovery flow)
    git tag -a "v$VERSION" "$CANDIDATE" -m "Release v$VERSION"
    
    # Push BOTH commit and tag in one atomic operation (--atomic)
    # Uses basic auth with App token (GitHub-specific requirement)
    git -c credential.helper= \
        -c "http.https://github.com/.extraheader=AUTHORIZATION: basic ..." \
        push --atomic origin "HEAD:refs/heads/main" "refs/tags/v$VERSION"
    ```
    **Why atomic?** If push partially fails (e.g., tag pushes but commit doesn't), we have an inconsistent state. `--atomic` prevents this.

11. **Report validated candidate**
    ```bash
    # Output to step summary (visible in workflow UI)
    echo "Version: v$VERSION"
    echo "Validated commit: $CANDIDATE"
    echo "Dry run: $DRY_RUN"
    ```
    Also sets step outputs for publish job to consume.

---

#### Job 2: `publish` (Conditional)
```yaml
needs: prepare                         # Depends on prepare job
if: ${{ !inputs.dry-run }}            # Skipped on dry-run
permissions:
  contents: write                      # Can create releases
```

**Steps:**

1. **Verify tag and publish release**
   ```bash
   # Verify tag still points to validated commit (catch manual push/delete)
   tag_object=$(gh api "repos/$GH_REPO/git/ref/tags/$tag" --jq '.object.sha')
   tag_commit=$(gh api "repos/$GH_REPO/git/tags/$tag_object" --jq '.object.sha')
   [[ "$tag_commit" == "$CANDIDATE" ]]
   
   # Check if release already exists
   if gh release view "$tag" > /dev/null; then
     # Verify it's not draft/prerelease (can't publish over those)
     if jq -e '.isDraft or .isPrerelease' > /dev/null; then
       exit 1  # Fail if conflict
     fi
   else
     # Create new release with auto-generated notes
     gh release create "$tag" \
       --verify-tag \
       --target "$CANDIDATE" \
       --title "$tag" \
       --generate-notes \
       --latest
   fi
   ```
   This is defensive: after the prepare job ran, someone could have manually pushed a conflicting tag or deleted ours. We verify before publishing.

---

### 2. `scripts/release.py` - Version Intelligence

This is the "brain" of the release system. It handles version calculations and validation.

**Core Functions:**

#### `parse_version(value: str) -> tuple[int, int, int]`
```python
# Validates format: "X.Y.Z" (no leading zeros, no 'v' prefix)
# Examples:
# - "1.2.3" ✅
# - "0.0.0" ✅
# - "v1.2.3" ❌ (v prefix not allowed)
# - "1.02.3" ❌ (leading zero not allowed)
# - "1.2.3rc1" ❌ (prerelease not allowed; use stable versions only)
```

#### `release_baseline(current: str, pages: list) -> str`
```python
# Determines the highest version that should be released next after
#
# Input:
#   - current: version in custom_components/sh_entity_status/manifest.json
#   - pages: paginated list of all GitHub releases (from API)
#
# Output:
#   - Maximum of:
#     1. manifest.json version
#     2. Highest published stable release (ignores drafts & pre-releases)
#
# Example:
#   - manifest says 1.2.0
#   - GitHub releases: [1.0.0, 1.1.0, 1.2.0, 1.2.1]
#   - Next stable version is 1.2.1, so baseline is 1.2.1
#   - User can bump to 1.2.2 (patch), 1.3.0 (minor), 2.0.0 (major)
```

#### `select_version(current: str, bump: str, override: str = "") -> str`
```python
# Calculate next version based on bump type or explicit override
#
# Inputs:
#   current: "1.2.3"
#   bump: "patch" | "minor" | "major"
#   override: optional explicit version "X.Y.Z"
#
# Logic:
#   - If override provided: validate it's > current, return it
#   - If bump == "patch": 1.2.3 → 1.2.4
#   - If bump == "minor": 1.2.3 → 1.3.0
#   - If bump == "major": 1.2.3 → 2.0.0
#
# Safety check: New version must be strictly greater than baseline
```

#### `prepare(root: Path, pages: list, bump: str, override: str) -> dict`
```python
# Main function called by release.yml to create release commit
#
# Process:
# 1. Load manifest.json
# 2. Calculate baseline from current manifest + GitHub releases
# 3. Compute next version (bump or override)
# 4. Verify version tag doesn't already exist (can't re-release)
# 5. Update manifest["version"] in JSON
# 6. Write back to manifest.json (git working directory, not committed yet)
# 7. Return {"version": "1.2.4"}
#
# Note: Does NOT commit. release.yml does that with specific message format.
```

#### `verify_release_metadata(previous: dict, candidate: dict, version: str)`
```python
# Validation function to ensure release commit is minimal & correct
#
# Checks:
# 1. candidate["version"] == requested version
# 2. version > previous["version"] (always increments)
# 3. Only field changed is "version" (nothing else in manifest touched)
#
# This ensures release commits are "clean" and predictable
```

#### `recover(root: Path, version: str) -> dict`
```python
# Re-publish an existing release if publish job failed
#
# Process:
# 1. Verify tag "v{version}" exists and is annotated (not lightweight)
# 2. Extract the commit that the tag points to
# 3. Verify commit is an ancestor of main (not orphaned)
# 4. Verify commit has exactly one parent (it's a release commit, not merge)
# 5. Verify commit message contains "SmartHass-Release: {version}" trailer
# 6. Verify commit changed only manifest.json
# 7. Verify version in manifest is correct
# 8. Return {"version": "1.2.4", "candidate": "<commit-sha>"}
#
# Why so many checks? Because if publish fails after push (e.g., network error),
# and we re-run the workflow, we want to make SURE we're re-publishing the right thing.
```

#### `main() -> None`
```python
# Entry point
# Parses command-line args and calls prepare() or recover()
# Outputs result as JSON to stdout AND to $GITHUB_OUTPUT file
```

---

### 3. `tests/test_release.py` - Release Logic Tests

Tests for `scripts/release.py` using pytest.

**Test Categories:**

1. **Version Parsing**
   ```python
   test_stable_version()           # "1.2.3" is valid
   test_invalid_version()          # "v1.2.3", "1.2", "01.2.3" are invalid
   ```

2. **Version Selection**
   ```python
   test_version_bumps()            # patch/minor/major increment correctly
   test_explicit_version()         # Can override with explicit version
   test_version_must_increase()    # New version must be > current
   ```

3. **Release Baseline**
   ```python
   test_release_baseline_from_manifest()
   test_release_baseline_ignores_prerelease()
   test_release_baseline_from_github_releases()
   ```

4. **Metadata Verification**
   ```python
   test_verify_release_metadata_detects_extra_changes()
   test_verify_release_metadata_rejects_downgrades()
   ```

5. **Recovery**
   ```python
   test_recover_from_tag()
   test_recover_requires_annotated_tag()
   test_recover_fails_if_version_mismatch()
   ```

---

## Workflow: Step-by-Step Example

### Scenario: Release v1.2.4 (patch bump from v1.2.3)

**Initial State:**
- `main` branch at commit `abc123`
- `manifest.json` has `"version": "1.2.3"`
- Latest GitHub release: `v1.2.3`

**User Triggers:**
```
Actions → Release → Run workflow
  bump: patch
  dry-run: false
```

**Execution:**

1. **prepare job starts**
   - Checks out commit `abc123`
   - Calls `scripts/release.py prepare --bump patch --releases <releases.json>`
     - Loads manifest (version 1.2.3)
     - Gets GitHub releases (highest: 1.2.3)
     - Calculates next: 1.2.3 + patch = 1.2.4
     - Verifies tag v1.2.4 doesn't exist ✓
     - Updates manifest to version 1.2.4
     - Writes manifest.json to disk
   - Creates commit:
     ```
     Release v1.2.4
     
     SmartHass-Release: 1.2.4
     ```
   - Runs `.github/actions/validate` (ruff, format, mypy, pytest, HACS)
   - Verifies commit SHA and git state unchanged
   - Creates GitHub App token (scoped to this repo, contents:write)
   - Pushes with App token:
     ```bash
     git tag -a v1.2.4 <commit> -m "Release v1.2.4"
     git push --atomic origin HEAD:main refs/tags/v1.2.4
     ```
   - Main now has new commit with manifest 1.2.4
   - Tag v1.2.4 points to that commit

2. **publish job starts** (depends on prepare)
   - Verifies tag v1.2.4 still points to expected commit
   - Checks if release v1.2.4 exists:
     - Doesn't exist, so create it
     - Calls `gh release create v1.2.4 --generate-notes`
   - GitHub generates release notes (commits since last tag)
   - Release is now live on GitHub
   - HACS can now see v1.2.4 and install it

**If dry-run=true:**
- Steps 1-8 execute (validation runs)
- Steps 9-10 skipped (no push)
- Step 11 shows what would be released
- Main branch unchanged ✓

**If push fails during step 9:**
- Tag exists but push didn't complete
- Commit didn't push
- Manifest on main still shows 1.2.3
- Next workflow run with `recover-version: 1.2.4` will re-do publish without re-validating

---

## Security Model

### Why GitHub App Token?

```
Scenario: Using GitHub OIDC Token (default GITHUB_TOKEN)

User creates PR on main (via branch protection)
PR gets approved and merged
Merge commit is created on main
  ↓
CI/CD runs... but
Merge commit can be pushed by: Bot, Approvers, Admins
Direct push to main by: Bot → BLOCKED (GITHUB_TOKEN can't bypass branch protection)

Problem: Release workflow can't push!
```

**Solution: GitHub App Token**

1. Create GitHub App (one-time, out of band)
2. Generate private key
3. Store credentials in repo environment secrets
4. Use `actions/create-github-app-token@v3` to generate short-lived token
5. Add app as "bypass actor" in branch protection ruleset
6. Now app can push to main, others still can't!

### What Can the App Token Do?

```
Permissions Granted to smarthass-chore-tracker-release app:
- Repository: Contents (Read & Write)
- Metadata: Read (implicit)
- Webhooks: Disabled

Token restrictions:
- Scoped to: sh-hass-entity-status repo ONLY
- Permissions: contents:write ONLY
- Lifetime: Short-lived (~1 hour)
- Bypass capability: Via ruleset bypass actor list

What it CAN do:
✅ Push commits to main
✅ Push tags
✅ Read repo contents
✅ Bypass branch protection (explicit bypass actor rule)

What it CANNOT do:
❌ Access other repos
❌ Modify org settings
❌ Create secrets/variables
❌ Trigger other workflows (no admin permission)
❌ Delete branches/tags (not granted)
```

### Threat Mitigations

| Threat | Mitigation |
|--------|-----------|
| Token leaked/stolen | Short-lived (~1 hour); rotated every use |
| Push to wrong repo | Token explicitly scoped to this repo |
| Bypass other rules | Only has contents:write; no admin power |
| Manual tampering | Atomic push; validates commit hash before publish |
| Race conditions | Freeze base commit; verify main didn't move |
| Malicious validation | Validate job is read-only; can't execute arbitrary code |

---

## Key Design Decisions

### 1. **Manifest-Only Commits**
- Release commit ONLY changes `custom_components/sh_entity_status/manifest.json`
- Version change is committed to git (not just in release notes)
- Makes releases reproducible and auditable
- Next time someone clones the repo, they can see version history

### 2. **Atomic Push**
```bash
git push --atomic origin "HEAD:refs/heads/main" "refs/tags/v$VERSION"
```
- If commit pushes but tag doesn't (or vice versa), entire push fails
- Prevents inconsistent state where tag exists but commit doesn't (or vice versa)

### 3. **Validation Before Push**
- Release validation uses same action as CI (`.github/actions/validate`)
- Ensures release candidate passed all checks
- No "fast-path" for releases; they must pass linting, testing, type-checking

### 4. **Environment Protection**
- `release` environment requires manual approval from repo owner
- Restricts deployment to `main` branch only
- Even if workflow is compromised, can't release to wrong branch

### 5. **Tag Verification**
- Publish job re-verifies tag points to expected commit
- Catches case where someone manually pushed a different tag with same name
- Defensive programming: never assume state hasn't changed

### 6. **Recovery Path**
- If publish fails after tag push, re-run with `recover-version`
- Doesn't re-validate or re-push commit/tag
- Just creates GitHub release pointing to existing tag
- Prevents double-pushing or double-tagging

---

## Integration with CI

### Before (Old Flow)
```
PR created → merged to main → auto-tag + auto-release
(Embedded in release PR merge flow)
```

### After (New Flow)
```
Code merged to main → all CI checks pass → manual Release workflow trigger
Release workflow: validate → push → publish
(Separate orchestration)
```

### Validation Consistency
- CI validation (`.github/actions/validate`): ruff, mypy, pytest, HACS
- Release validation (`.github/actions/validate`): SAME action, SAME checks
- Ensures release won't fail validation that passed in CI

---

## Next Steps in Release Setup

From `docs/release_setup.md`, remaining steps:

- ✅ Step 1-4: Done (GitHub App installed, environment created, credentials stored, bypass actor added)
- ⏳ Step 5: Verify credentials are in repo
- ⏳ Step 6: Verify bypass actor configured (done via API)
- ⏳ Step 7: Tag ruleset for `v*` tags (recommended, not required)
- ⏳ Step 8: Test dry-run release
- ⏳ Step 9: Real release or skip
- ⏳ Step 10: Clean up old config

---

## Summary

This release mechanism is:

1. **Automated**: User clicks "Run workflow" and release is complete
2. **Safe**: Multiple validation gates; atomic operations; recovery path
3. **Auditable**: All commits tagged and in git history; version in manifest
4. **Secure**: Short-lived token; scoped permissions; environment protection
5. **Minimal**: Only changes manifest version; no binary assets or archives
6. **Compatible**: Works with HACS installation (tags + release notes)

The code is production-ready and matches the proven pattern from sh_chore_tracker.
