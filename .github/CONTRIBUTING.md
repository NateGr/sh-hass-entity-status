# Contributing

SmartHass Entity Status is a solo-maintained project. I'm happy when others find it useful,
and I welcome contributions that align with the project's goals. That said, I have limited time,
so please set realistic expectations around review cycles and what's in scope.

## Getting Started

1. Fork the repository and create a branch for your change.
2. Create and activate a virtual environment.
3. Install test dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements_test.txt
   pip install ruff
   ```

## Running Checks

Run the same checks used in GitHub Actions before opening a pull request.

```bash
ruff check .
python -m pytest tests/ -v
```

## Pull Request Guidelines

- Keep changes focused and scoped to one topic.
- Add or update tests when behavior changes.
- Update documentation when user-facing behavior changes.
- Do not bump `custom_components/sh_entity_status/manifest.json` version in feature or fix pull requests.
- Make sure the CI workflow is green before requesting review.

## Reporting Bugs

Use the GitHub bug report form and include:

- Home Assistant version
- Integration version
- Steps to reproduce
- Expected behavior
- Actual behavior
- Relevant logs or screenshots

## Proposing Features

Use the GitHub feature request form to describe the problem, the proposed
solution, and any alternatives you considered.

## Code of Conduct

By participating in this project, you agree to follow the
[Code of Conduct](CODE_OF_CONDUCT.md).

---

## Contributor Boundaries

To set clear expectations:

- **Feature scope** — This project focuses on improving existing functionality. PRs that add
  entirely new features are out of scope and will not be merged. If you have a new feature idea,
  open a discussion issue first—I may consider it for a future roadmap, but I make no commitment.
- **Code quality** — All PRs must pass linting (`ruff check .`) and tests (`python -m pytest tests/ -v`),
  include updated tests for any behavior change, and update documentation if user-facing behavior
  changes. No new dependencies without prior discussion.
- **Response time** — I review when I can. There is no SLA. Don't expect a turnaround in days.
- **Major changes** — Rewrites, architectural changes, or new dependencies require an open issue
  and agreement before work starts. PRs that arrive without prior discussion will be closed.
