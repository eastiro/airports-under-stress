# External implementation agent guide

This repository may be edited by an external coding agent working under Codex's product and review direction.

## Role split

- The external agent is the high-permission implementation engineer. It may handle component construction, repetitive styling, data transforms, tests, accessibility passes, and mechanical refactors.
- Codex owns product direction, visual judgment, architecture boundaries, acceptance review, Git decisions, and publishing.
- Read `PROJECT_STATUS.md`, `HANDOFF.md`, and the active task in `tasks/external-agent/` before editing.

## Standing repository permissions

Inside this repository, the external agent may:

- read, create, edit, move, and refactor project files;
- run local builds, tests, formatters, and development checks;
- install a necessary dependency when the task genuinely requires it;
- generate derived data or visual assets from checked-in project data;
- make broad but task-scoped edits without asking for approval file by file.

## Safety and product boundaries

- Preserve user-authored work and unrelated dirty-worktree changes.
- Do not delete raw/source data, expose secrets, change machine-level permissions, or access unrelated directories.
- Do not rewrite Git history, force-push, use destructive resets, publish the site, alter Sites visibility, or create a new Sites project.
- Do not silently replace audited metrics with invented or externally fetched values.
- Treat propagation as descriptive continuity, not causal attribution.
- Keep Chinese and English interface content in sync.
- When a task says a stable section is out of scope, leave it functionally unchanged.

## Verification

For frontend work, run from `web/`:

```powershell
npm.cmd test
```

For data-pipeline work, run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Report changed files, test results, and any unresolved risks. Do not commit or publish unless the active task explicitly authorizes it.
