# Contributing

Thank you for your interest in contributing to SmartHass Entity Status.

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
