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

## Future Maintainer Note

Before this file is considered final, revisit and define your hard boundaries so contributors
know what to expect. Consider documenting answers to:

- **Feature scope** — What fits the project's vision? Open to any HA-related ideas, or only
  improvements to existing functionality?
- **Code quality** — What's required before merging? (e.g., passing tests and linting, updated
  docs, no new dependencies without discussion)
- **Response time** — What can you realistically commit to? ("I review when I can, typically
  within X weeks")
- **Major changes** — What needs discussion before work starts? (e.g., rewrites, new
  dependencies, architecture changes)

Documenting these now saves you from difficult conversations later.
