# AGENTS.md — {{project_name}}

Persistent instructions for coding agents (Claude, Codex, Copilot, etc.) working in this repository. This file is the single source of truth; `CLAUDE.md` inherits from it via `@AGENTS.md`.

## Project

{{stack_summary}}

Key locations: {{key_paths}}

## Plan-driven delivery

The authoritative plan is **[{{plan_path}}]({{plan_path}})**. Phases are headed `## Phase N — <Title>`. A phase is complete when its heading carries a trailing `✅` marker. Work the lowest-numbered open phase unless the user names a specific one.

Do not invent acceptance criteria the plan doesn't list, and do not bundle multiple phases into one commit unless the orchestrating command says to.

## Build & test

```
{{build_cmd}}
{{test_cmd}}
```

Build must be clean (zero new errors, zero new warnings introduced by the diff) before a phase can be claimed complete. Tests must be green.

## Conventions

{{conventions_block}}

## Severity tags for findings

Reviewers use these levels — apply them to your own self-checks too.

- **BLOCKER** — won't compile, won't run, or causes data loss / security regression.
- **MAJOR** — missing requirement, broken behavior, race condition, code disagrees with the plan, missing test on a new code path.
- **MINOR** — convention drift, missing non-critical test, stale documentation, narrow edge case.
- **NIT** — cosmetic (naming, whitespace, unused import). Acceptable to leave.
- **DOC** — documentation/plan drift only; the code is correct but a doc is stale. **The user owns plan/doc bookkeeping** — surface DOC findings to the user; do not edit completion-status markers (`[ ]`/`[x]`, phase `✅`) yourself.
- **SHARED** — a pattern that should be elevated to a shared library/component. Reviewers collect these for a separate suggestions file.

## Things you do NOT do

- Do not commit code that the user did not ask you to commit (unless the active command says to).
- Do not use `--no-verify` on git hooks.
- Do not force-push.
- Do not invent acceptance criteria. Open questions go back to the user.
- Do not introduce backward-compat shims, dual-write paths, feature flags, deprecation comments, or `// TODO: drop after vN` markers unless the plan explicitly calls for one.
- Do not edit phase status markers in the plan (`✅`, `⚠️`, checkbox state). The user owns plan bookkeeping.

## Critical rule

Never do anything the user did not explicitly ask for.
