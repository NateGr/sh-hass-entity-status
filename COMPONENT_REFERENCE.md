# Release Mechanism: Component Reference

## The Three Key Files

### 1. `.github/workflows/release.yml` (165 lines)
**What it does**: Orchestrates the entire release process
**Two jobs**: 
- `prepare`: Validates and creates release commit/tag (protected by `release` environment)
- `publish`: Creates GitHub release (only if not dry-run)

**Key steps**:
1. Check we're on main branch + right repo
2. Freeze main commit SHA
3. Determine next version using scripts/release.py
4. Create release commit (only changes manifest.json)
5. Run full validation (same as CI)
6. Generate GitHub App token (short-lived, scoped to this repo)
7. Atomically push commit + tag using App token (bypasses branch protection)
8. Publish release with auto-generated notes

**Inputs**:
- `bump`: patch | minor | major (how to increment version)
- `version`: optional explicit version override (X.Y.Z format)
- `dry-run`: true | false (validate without pushing)
- `recover-version`: optional version to re-publish if publish failed

---

### 2. `scripts/release.py` (250 lines)
**What it does**: Version intelligence and release validation

**Main functions**:
- `parse_version()`: Validates version format (X.Y.Z, no 'v' prefix)
- `release_baseline()`: Finds highest version from manifest + GitHub releases
- `select_version()`: Calculates next version (patch/minor/major bump or explicit)
- `prepare()`: Creates release commit by updating manifest.json
- `verify_release_metadata()`: Validates release commit only changed version
- `recover()`: Re-locates existing release tag for re-publication

**Design principle**: Release commits must be "clean" - only manifest.json version changes, nothing else.

---

### 3. `tests/test_release.py` (100+ lines)
**What it does**: Unit tests for release logic

**Test coverage**:
- Version parsing (valid/invalid formats)
- Version selection (patch/minor/major bumps)
- Release baseline calculation
- Release metadata verification
- Recovery from existing tags

---

## The Release Flow Visualized

```
User Action
│
└─ Trigger "Release" workflow
   ├─ Inputs: bump type, optional version, dry-run flag
   │
   └─ Environment: "release" (manual approval + main-only)
      │
      ├─ PREPARE JOB
      │  ├─ Checkout main at exact commit SHA
      │  │
      │  ├─ Calculate next version
      │  │  ├─ Load manifest.json (current version)
      │  │  ├─ Query GitHub releases (all published versions)
      │  │  ├─ Pick highest (baseline)
      │  │  └─ Apply bump: baseline + patch/minor/major
      │  │
      │  ├─ Create release commit
      │  │  ├─ Update manifest.json with new version
      │  │  ├─ Git commit with trailer "SmartHass-Release: X.Y.Z"
      │  │  └─ Verify ONLY manifest.json changed
      │  │
      │  ├─ Full validation
      │  │  ├─ ruff (linting + formatting)
      │  │  ├─ mypy (type checking)
      │  │  ├─ pytest (tests + coverage)
      │  │  └─ HACS validation
      │  │
      │  ├─ Create GitHub App token
      │  │  ├─ Client ID: RELEASE_APP_CLIENT_ID (env variable)
      │  │  ├─ Private key: RELEASE_APP_PRIVATE_KEY (env secret)
      │  │  ├─ Scope: This repo only
      │  │  ├─ Permission: contents:write
      │  │  └─ Lifetime: ~1 hour
      │  │
      │  └─ Push (if not dry-run)
      │     ├─ Create annotated tag: git tag -a v$VERSION
      │     ├─ Verify main hasn't moved (no race condition)
      │     ├─ Atomic push: commit + tag together
      │     │  └─ Uses App token to bypass branch protection
      │     └─ Output: version, candidate commit SHA
      │
      └─ PUBLISH JOB (if not dry-run)
         ├─ Verify tag still points to expected commit
         │
         └─ Create GitHub release
            ├─ Check if release already exists
            ├─ If not, create with --generate-notes flag
            ├─ GitHub auto-generates notes from commits since last tag
            └─ Release is now visible to HACS and users
```

---

## Why This Design?

### Before (Old Release PR flow)
```
Developer: Merge release PR to main
GitHub: Auto-creates tag + release
Problem: Embedded in PR merge, hard to debug, hard to recover
```

### After (GitHub App flow)
```
Developer: Click "Release" workflow
Workflow: Validate → Push tag → Publish release
Problem: Can manually retry any step, recover from failures
```

### Key Innovation: GitHub App Token

```
Branch protection normally blocks direct pushes to main
     ↓
But release commits need to bypass protection
     ↓
GitHub App with "bypass actor" rule can push without PR
     ↓
App token is short-lived (~1 hour) for security
     ↓
Token is scoped to this repo only (isolation)
```

---

## Security: What the App Can Do

### Permissions Granted
- **Repository**: Contents (Read & Write)
- **Metadata**: Read (implicit)
- **Webhooks**: Disabled

### Token Capabilities
```
✅ Can:
  - Push commits to main
  - Push tags
  - Read repo contents
  - Bypass branch protection (via bypass actor rule)

❌ Cannot:
  - Access other repos
  - Modify secrets/variables
  - Trigger other workflows
  - Delete branches/tags
  - Access org settings
```

### Lifecycle
```
Workflow starts
  ↓
Generate short-lived App token (~1 hour lifetime)
  ↓
Use token to push release commit + tag
  ↓
Token expires (automatically revoked)
  ↓
Even if leaked, useless after 1 hour
```

---

## Critical Validations

### 1. Release Commit Validation
```
Must be exactly ONE commit
Must change ONLY manifest.json
Must increase version field
Must have "SmartHass-Release: X.Y.Z" trailer
```

### 2. Pre-Push Validations
```
✓ Running on main branch
✓ Running in correct repo
✓ No conflicts between new and recover versions
✓ Exact commit SHAs match (frozen main didn't move)
✓ Tag doesn't already exist (can't re-release with same tag)
✓ Validation action didn't modify any files
```

### 3. Post-Push Validations (publish job)
```
✓ Tag still points to validated commit (catch manual push)
✓ Release doesn't exist as draft/prerelease (catch conflicts)
✓ Generate and publish notes automatically
```

---

## Error Scenarios & Recovery

### Scenario 1: Validation Fails
```
Release workflow starts
  ↓
Validation fails (test, lint, type-check, HACS)
  ↓
Workflow stops (no push, no publish)
  ↓
Fix the issue, commit to main, try again
```
**Recovery**: Re-run workflow; no manual cleanup needed

### Scenario 2: Push Fails
```
Validation passes
  ↓
Token generated
  ↓
Push fails (network error, permission, etc.)
  ↓
Commit & tag NOT on origin
  ↓
Workflow fails
  ↓
Fix issue (usually env var or secret), try again
```
**Recovery**: Re-run workflow; local changes cleaned up automatically

### Scenario 3: Publish Fails (After Push Success)
```
Validation passes
  ↓
Push succeeds
  ↓
Commit on main ✓
  ↓
Tag on origin ✓
  ↓
Publish job starts
  ↓
Publish fails (permissions, GitHub API error, etc.)
  ↓
Tag exists BUT release not created
  ↓
Workflow fails
  ↓
Re-run workflow with recover-version input
```
**Recovery**: 
```
Workflow → Release → run workflow
  recover-version: 1.2.4
  (don't specify bump or version)
```
Workflow will:
1. Verify tag v1.2.4 exists and points to correct commit
2. Skip prepare job (already has the commit)
3. Run publish job to create GitHub release
4. No re-validation, no re-push

---

## Integration Checklist

- [x] CI workflow (`.github/workflows/ci.yml`) uses single validate job ✓
- [x] CI action (`.github/actions/validate/action.yml`) exists ✓
- [x] Release workflow added (`.github/workflows/release.yml`) ✓
- [x] Release script added (`scripts/release.py`) ✓
- [x] Release tests added (`tests/test_release.py`) ✓
- [x] Setup documentation added (`docs/release_setup.md`) ✓
- [ ] GitHub App installed on repo
- [ ] Release environment created with credentials
- [ ] Branch protection configured with bypass actor
- [ ] Tag ruleset configured (optional but recommended)
- [ ] Test dry-run release
- [ ] Test real release
- [ ] Remove old release configuration

---

## Command Reference

### Trigger Release Workflow

**Dry-run (test without pushing)**
```bash
gh workflow run release.yml \
  --ref main \
  -f bump=patch \
  -f dry-run=true
```

**Real Release (patch bump)**
```bash
gh workflow run release.yml \
  --ref main \
  -f bump=patch
```

**Real Release (explicit version)**
```bash
gh workflow run release.yml \
  --ref main \
  -f version=1.2.4
```

**Recover Failed Publish**
```bash
gh workflow run release.yml \
  --ref main \
  -f recover-version=1.2.4
```

### Monitor Release

```bash
# Watch workflow run
gh run watch

# View latest release
gh release view

# List all releases
gh release list
```

---

## Key Takeaways

1. **Release = Deterministic**: Same version selection logic, same validation, same push strategy every time
2. **Release = Auditable**: Every release commit in git history, version in manifest, tagged for all to see
3. **Release = Safe**: Multiple validation gates, atomic push, recovery path for failures
4. **Release = Minimal**: Only manifest changes, no binary artifacts, works with HACS tag-based install
5. **Release = Secure**: Short-lived token, scoped permissions, environment protection

The implementation follows GitHub best practices and matches the proven pattern from sh_chore_tracker.
