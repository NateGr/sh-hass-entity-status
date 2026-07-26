# Plan Backup (from Copilot Memory)

Source memory path: `/memories/session/plan.md`

---

## Plan: HACS Readiness With SmartHass Branding

Prepare the integration for HACS testing and release readiness on the active context branch (`copilot/context`), keep all internal sh-prefixed identifiers unchanged, and defer public visibility until final validation.

**Completed so far**
1. Branch created and active: copilot/context.
2. Initial readiness updates committed on branch.
3. Virtual environment workflow established.
4. Ruff installed in venv and lint runs are working.
5. Draft PR opened from `copilot/context` to `main`: https://github.com/NateGr/sh-hass-entity-status/pull/10.

**Steps**
1. Phase 0 - Branch and guardrails (completed)
2. Keep all implementation commits on copilot/context.
3. Preserve internal names: repo slug, folders, domain, entity IDs, service IDs, and sh prefixes.

4. Phase 1 - Branding and documentation alignment
5. Update only public-facing branding references to SmartHass.
6. Keep technical identifiers unchanged unless presentation-only.
7. Reconcile docs with current implementation and remove stale references.

8. Phase 2 - CI, dependency, governance, and automation while private
9. Run lint and tests from venv and keep CI-compatible command set documented.
10. Verify workflow behavior so HACS checks do not create false failures while repo is private.
11. Add minimal Dependabot config in .github/dependabot.yml for weekly updates to pip and GitHub Actions.
12. Add dependency verification task for clean CI: confirm Ruff is installed via workflow steps in a fresh runner and not dependent on local machine state.
13. Validate CI dependency strategy for Ruff: either keep explicit installation in CI workflows or pin Ruff in dependency files and verify whichever approach is chosen is consistent across workflows.
14. Configure main branch protection before making repo public.
15. Branch protection baseline: require PR, require status checks, require up-to-date branch, restrict direct pushes, disable force pushes.
16. Validate release archive composition and version consistency.

17. Phase 3 - Copilot execution boundary and PR readiness
18. Copilot may implement and commit incrementally on copilot/context.
19. Copilot may create Draft PR from copilot/context to main.
20. Copilot must not approve the PR.
21. Do not merge to main until explicit final sign-off after private checks.

22. Phase 4 - Final HACS validation with public last
23. Immediately before testing, set repository description and topics required for HACS ecosystem expectations.
24. Make repository public.
25. Run HACS validation workflow and resolve findings.
26. Test custom repository install in Home Assistant HACS.
27. Test update path with a new release.
28. Merge approved PR to main only after final testing outcomes are successful.

**Relevant files**
- c:/git/sh-hass-entity-status/README.md - public-facing user documentation.
- c:/git/sh-hass-entity-status/docs/developer_spec.md - developer/test workflow guidance.
- c:/git/sh-hass-entity-status/docs/open_source_readiness.md - readiness checklist consistency.
- c:/git/sh-hass-entity-status/hacs.json - HACS metadata and public name alignment.
- c:/git/sh-hass-entity-status/custom_components/sh_entity_status/manifest.json - integration metadata and version alignment.
- c:/git/sh-hass-entity-status/custom_components/sh_entity_status/const.py - preserve internal naming constants.
- c:/git/sh-hass-entity-status/custom_components/sh_entity_status/strings.json - user-visible setup/options wording.
- c:/git/sh-hass-entity-status/custom_components/sh_entity_status/translations/en.json - user-visible translations.
- c:/git/sh-hass-entity-status/custom_components/sh_entity_status/services.yaml - user-visible service descriptions.
- c:/git/sh-hass-entity-status/custom_components/sh_entity_status/brand/icon.png - brand asset path.
- c:/git/sh-hass-entity-status/.github/workflows/ci.yml - lint/test runner setup and dependency installation path.
- c:/git/sh-hass-entity-status/.github/workflows/hacs.yml - HACS validation behavior.
- c:/git/sh-hass-entity-status/.github/workflows/publish.yml - release pipeline behavior pre/post public.
- c:/git/sh-hass-entity-status/.github/workflows/release.yml - tag release behavior and HACS gate.
- c:/git/sh-hass-entity-status/.github/dependabot.yml - dependency and actions update automation.

**Verification**
1. Branch verification: active branch is copilot/context and commits stay on this branch.
2. Naming verification: all internal sh-prefixed identifiers remain unchanged.
3. Branding verification: public-facing SH references are updated to SmartHass where intended.
4. Documentation verification: stale or removed-feature references are cleared.
5. Ruff dependency verification in clean CI: fresh runner can execute Ruff without relying on local cache/state.
6. Quality verification: Ruff and pytest pass using documented commands and CI checks.
7. Dependabot verification: .github/dependabot.yml is valid and scheduled PRs can be created.
8. PR readiness verification: draft PR is prepared; branch CI still needs GitHub-side action from current `action_required` state.
9. Gate verification: no merge to main before explicit sign-off.
10. HACS verification after public flip: validator pass plus successful install/update tests.

**Decisions**
- Branch name is copilot/context.
- Public branding only is updated to SmartHass.
- Internal/repo identifiers remain sh-prefixed.
- Main branch protection is required before public visibility/testing.
- Copilot may commit on branch and may open Draft PR only.
- Copilot cannot approve PR.
- Repo public flip remains a final-stage action.

**Dependabot Tips**
1. Start with weekly updates only, then tune PR volume after observing 1-2 cycles.
2. Add open-pull-requests-limit if update noise is high.
3. Add groups to combine minor/patch updates by ecosystem.
4. Add ignore rules for majors you want to schedule manually.
5. Keep required status checks on to auto-validate Dependabot PRs.
