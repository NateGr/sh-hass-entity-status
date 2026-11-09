# PR #46 CI Status Issue - Analysis & Solution

**Date**: November 8, 2026  
**Repository**: NateGr/sh-hass-entity-status  
**PR**: #46 - "ci: replace release PR flow with App-token release workflow"

---

## Current Status

**PR Cannot Merge** ❌ - Pending required status checks

### GitHub Shows:
- ⚠️ **"Some checks haven't completed yet"**
  - 2 expected, 1 successful checks
  
### Pending (Waiting for status):
- 🟡 **lint** — Expected — Waiting for status to be reported — **Required**
- 🟡 **test** — Expected — Waiting for status to be reported — **Required**

### Successful:
- ✅ **CI / Validate (pull_request)** — Successful in 1m

---

## Root Cause

### What GitHub Expects:
The repository has a **branch protection ruleset** (Main branch protection) that requires specific status checks:
1. `lint` (as a separate check)
2. `test` (as a separate check)
3. Other checks (like `Validate`)

### What the Workflow Provides:
The `.github/workflows/ci.yml` file defines:
- **Single job**: `validate`
- **Job output**: Reports as `CI / Validate (pull_request)` check only

### What's Inside the Validate Job:
The validate job runs `.github/actions/validate` which includes:
- ✅ **Lint** (python -m ruff check .)
- ✅ **Format check** (python -m ruff format --check .)
- ✅ **Type check** (python -m mypy)
- ✅ **Test** (python -m pytest with 80% coverage requirement)
- ✅ **HACS validation**

**The problem**: All these checks run inside the `validate` job, but GitHub only sees one check: `CI/Validate`

---

## Why This Happens

GitHub's status check system requires workflow jobs to be **explicitly named** to match what the branch protection expects.

**Current ci.yml structure:**
```yaml
jobs:
  validate:
    name: Validate
    runs-on: ubuntu-latest
    steps:
      - ... # All lint, test, format, type-check steps here
```

**GitHub translates this to:**
- Check name: `CI / Validate (pull_request)`

**Branch protection expects:**
- `lint` (separate check)
- `test` (separate check)

These don't match, so GitHub considers them "pending" indefinitely.

---

## Solution Options

### Option A: Create Separate Jobs (Recommended)
Refactor `ci.yml` to have separate jobs for lint and test:

```yaml
jobs:
  lint:
    name: Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
      - run: python -m pip install -r requirements_test.txt
      - run: python -m ruff check .
      - run: python -m ruff format --check .

  test:
    name: Test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
      - run: python -m pip install -r requirements_test.txt
      - run: python -m mypy custom_components/sh_entity_status/ --ignore-missing-imports
      - run: python -m pytest tests/ -v --cov=custom_components/sh_entity_status --cov-report=xml --cov-fail-under=80

  validate:
    name: Validate
    runs-on: ubuntu-latest
    needs: [lint, test]
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
      - run: python -m pip install -r requirements_test.txt
      - run: python -m ruff check .
      - run: python -m pytest tests/ -v --cov=custom_components/sh_entity_status --cov-report=xml --cov-fail-under=80
      # ... HACS validation ...
```

This creates three checks:
- `CI / Lint (pull_request)` ✅
- `CI / Test (pull_request)` ✅
- `CI / Validate (pull_request)` ✅

### Option B: Update Branch Protection Ruleset
Instead of creating separate jobs, remove the individual `lint` and `test` requirements from the branch protection and keep only `Validate`.

**Edit**: Settings → Rulesets → Main branch protection → Status checks

**Remove the requirement for:**
- `lint`
- `test`

**Keep only:**
- `Validate` (or rename it to be more specific)

---

## Recommended Path Forward

**Option A is better because:**
- ✅ Provides granular feedback on what failed (lint vs test)
- ✅ Allows parallel execution (faster CI)
- ✅ Follows GitHub best practices
- ✅ Makes CI output more readable
- ✅ Allows independent job caching strategies

---

## Files Affected

If implementing Option A:
- **Modify**: `.github/workflows/ci.yml`
  - Split `validate` job into `lint`, `test`, and `validate` jobs
  - Add `needs: [lint, test]` to the validate job for dependency ordering

---

## Next Steps

Choose one option:
1. **Option A**: Refactor ci.yml to create separate lint and test jobs (requires code change)
2. **Option B**: Update the Main branch protection ruleset to only require `Validate` check (no code change)

Then PR #46 can be merged successfully.

---

## Important Note

The workflow code itself is correct—lint, test, format, and type checking all work properly. The issue is purely about **GitHub's status check naming and matching** between the workflow jobs and the branch protection requirements.
