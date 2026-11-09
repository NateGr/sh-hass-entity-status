# Release Mechanism Setup - Execution Log

**Date**: November 8, 2026  
**Repository**: NateGr/sh-hass-entity-status  
**Purpose**: Document the manual GitHub infrastructure setup required for the GitHub App token release workflow

---

## Step 1: Install GitHub App on Repository ✅

**GitHub UI Path**: Settings → Integrations → GitHub Apps

**Action**: Added `sh-hass-entity-status` to the GitHub App's "Only select repositories" list

**GitHub App Details**:
- **App Name**: `smarthass-chore-tracker-release`
- **App ID**: `5510609`
- **Client ID**: `Iv23linSd4TWdZ65EdkP`
- **Permissions**: Contents (Read & write), Metadata (Read - implicit)

**Result**: App is now installed on the repository and can be used for authenticated API calls.

---

## Step 2: Create Release Environment ✅

**GitHub UI Path**: Settings → Deployments → Environments → New environment

**Environment Name**: `release`

**Configuration**:
- **Deployment branches**: Restricted to `main` only (via branch rule)
- **Environment reviewers**: (Optional) Can be configured if approval is desired

**Result**: `release` environment created and ready to store secrets and variables.

---

## Step 3: Add Environment Credentials ✅

**GitHub UI Path**: Settings → Environments → `release` (edit)

### 3a. Environment Variable

**Name**: `RELEASE_APP_CLIENT_ID`  
**Value**: `Iv23linSd4TWdZ65EdkP`  
**Scope**: Non-sensitive (public-facing client ID)

**Result**: Variable added to `release` environment.

### 3b. Environment Secret

**Name**: `RELEASE_APP_PRIVATE_KEY`  
**Value**: Full RSA private key in PEM format (multi-line)
```
-----BEGIN RSA PRIVATE KEY-----
[full 1679-byte key content]
-----END RSA PRIVATE KEY-----
```
**Source**: Downloaded from GitHub App settings → Key pairs → Private keys section  
**File Retrieved From**: `C:\Users\natha\Downloads\smarthass-chore-tracker-release.2026-11-08.private-key.pem`  
**Scope**: Sensitive (stored as encrypted environment secret)

**Result**: Secret added to `release` environment. GitHub does not display private keys after creation, so this download was critical.

---

## Step 4: Configure Branch Protection with Bypass Actor ✅

**GitHub UI Path**: Settings → Code, planning, and automation → Rulesets → "Main branch protection"

### 4a. Identified Existing Ruleset

**Ruleset Name**: `Main branch protection`  
**Status**: `Active`  
**Target Branches**: `main` (default targeting pattern)

**Existing Rules** (already configured):
- ✅ Require a pull request before merging
- ✅ Require status checks to pass (specifically the `Validate` check)
- ✅ Block force pushes
- ✅ Restrict deletions (checked)

### 4b. Added Bypass Actor

**Bypass List Section**: Opened "Add bypass" dialog

**Actor Selected**: `smarthass-chore-tracker-release` (GitHub App)
- **Actor Type**: Apps → NateGr
- **Bypass Mode**: "Always allow"

**Purpose**: Allows the GitHub App to:
- Bypass the "Require a pull request" check
- Bypass the "Require status checks to pass" check
- Bypass the "Restrict deletions" check
- Push the release commit directly to `main`
- Create and push the release tag without being blocked

**Result**: Ruleset saved. "Ruleset updated" confirmation received.

---

## Summary of Values & Configurations

| Step | Item | Value/Configuration |
|------|------|-------------------|
| 1 | GitHub App | `smarthass-chore-tracker-release` |
| 1 | App ID | `5510609` |
| 1 | Client ID | `Iv23linSd4TWdZ65EdkP` |
| 2 | Environment Name | `release` |
| 2 | Deployment Branch Restriction | `main` only |
| 3a | Variable Name | `RELEASE_APP_CLIENT_ID` |
| 3a | Variable Value | `Iv23linSd4TWdZ65EdkP` |
| 3b | Secret Name | `RELEASE_APP_PRIVATE_KEY` |
| 3b | Secret Value | [Full RSA private key in PEM format] |
| 4 | Ruleset Name | `Main branch protection` |
| 4 | Target Branch | `main` |
| 4 | Bypass Actor | `smarthass-chore-tracker-release` |
| 4 | Bypass Mode | Always allow |

---

## Next Steps (Not Yet Executed)

The following steps remain for completing the release mechanism:

1. **Review PR #46** - Examine the workflow files, scripts, tests, and documentation
2. **Merge PR #46 to main** - Integrate the release mechanism code
3. **Test dry-run release** - Execute `Release` workflow with `dry-run: true`
4. **Execute real release** (optional) - Run actual release if testing passes
5. **Remove obsolete config** - Delete old `release/*` branches and auto-merge settings
6. **Consider key management** - If the app is used in other repos, evaluate centralized key storage

---

## Important Notes

- **Private Key Security**: The private key file should be deleted from the Downloads folder after setup to prevent accidental exposure
- **No Manual Save Required**: GitHub Rulesets auto-save changes; the "Save changes" button at the bottom confirmed the bypass actor was persisted
- **Reusable App**: The `smarthass-chore-tracker-release` app is shared with `sh-chore-tracker` repo; the private key should be the same across repos that use the same app instance
- **Future Refactoring**: The plan mentions potentially extracting common release patterns into a private `sh-release-tools` package later
