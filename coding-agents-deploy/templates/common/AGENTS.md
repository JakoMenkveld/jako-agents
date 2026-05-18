# AGENTS.md — {{project_name}}

Persistent instructions for coding agents (Claude, Codex, Copilot, etc.) working in this repository. This file is the single source of truth; `CLAUDE.md` inherits from it via `@AGENTS.md`.

## First-run self-configuration

Before doing anything else on your first run in this repository, check whether this file and the agent configs still contain unfilled deploy placeholders, and fix them in place if so. Treat any of the following as unfilled:

- `## Project` reads `Unknown stack` or is empty.
- The build or test command is `<add build command>` / `<add test command>` — anywhere it appears: here under `## Build & test`, in the `## Conventions`/division-of-labour text, in `.claude/settings.json` permission entries, and in the `review-iterate` agent file.
- `## Conventions` contains only the generic-fallback note ("this is a generic fallback").
- Any other `<add …>` sentinel (e.g. `<add sln name>`).

When you find unfilled placeholders: detect the real stack from the repo (`package.json` scripts, `*.csproj`/`*.sln`, `pyproject.toml`, `go.mod`, Makefile, etc.), then edit, in this order, (1) `AGENTS.md` — `## Project`, `## Build & test`, `## Conventions`; (2) the harness settings file `.claude/settings.json` — replace the `<add build command>` / `<add test command>` Bash allow entries with the real commands; (3) the `review-iterate` agent file — its stack summary, build command, test command, and conventions lines. Keep the build and test commands byte-identical across all three. Report a one-line summary of what you filled in, then continue with the original task. If the stack genuinely cannot be determined, ask the user once instead of guessing.

This is a one-time repair: once the placeholders are gone, skip this section.

## Project

{{stack_summary}}

## Plan-driven delivery

The authoritative plan is **[{{plan_path}}]({{plan_path}})**. Phases are headed `## Phase N: <Title>`. A phase is complete when its heading carries a trailing `✅` marker. Work the lowest-numbered open phase unless the user names a specific one.

Do not invent acceptance criteria the plan doesn't list, and do not bundle multiple phases into one commit unless the orchestrating command says to.

## Build & test

```
{{build_cmd}}
{{test_cmd}}
```

**Division of labour — read this before running anything.**

- **Implementers** (`implement-phase`, `implement-fixes`) run **only the build** (`{{build_cmd}}`). Iterate build → fix until clean. Implementers do **NOT** run the test suite — delegate that by spawning the `review-iterate` agent.
- **Reviewers** (`review-iterate`, `review-implementation`) run **both** `{{build_cmd}}` and `{{test_cmd}}`. They own test verification.

Running the test suite from an implementer is wasted work — it re-runs on every reviewer pass anyway. A phase is complete only after the build is clean *and* the reviewer has run the tests green; the implementer is responsible for the former, the reviewer for the latter.

## Conventions

{{conventions_block}}

## Severity tags for findings

Reviewers use these levels — apply them to your own self-checks too.

- **BLOCKER** — won't compile, won't run, or causes data loss / security regression.
- **MAJOR** — missing requirement, broken behavior, race condition, code disagrees with the plan, missing test on a new code path.
- **MINOR** — convention drift, missing non-critical test, stale documentation, narrow edge case.
- **NIT** — cosmetic (naming, whitespace, unused import). Acceptable to leave.
- **DOC** — documentation/plan drift only; the code is correct but a doc is stale. **Reviewers own plan/doc bookkeeping** — reviewer-role agents keep the plan and docs current, including completion-status markers (`[ ]`/`[x]`, phase `✅`/`⚠️`). Implementer/coder-role agents do not edit docs and never comment on or flag the plan's completion status (the reviewer reconciles it and does not need it pointed out); they surface other DOC findings for the reviewer.
- **SHARED** — a pattern that should be elevated to a shared library/component. Reviewers collect these for a separate suggestions file.

## Things you do NOT do

- Do not commit code that the user did not ask you to commit (unless the active command says to).
- Do not use `--no-verify` on git hooks.
- Do not force-push.
- Do not invent acceptance criteria. Open questions go back to the user.
- Do not introduce backward-compat shims, dual-write paths, feature flags, deprecation comments, or `// TODO: drop after vN` markers unless the plan explicitly calls for one.
- **Implementers/coders:** do not edit documentation files or plan status markers (`✅`, `⚠️`, checkbox state), and never comment on or flag the plan's completion status — not even as a DOC finding. The reviewer reconciles it and does not need it pointed out. Surface other DOC findings for the reviewer. **Reviewers** own plan/doc bookkeeping and are responsible for keeping the plan documentation up to date.

## Critical rule

Never do anything the user did not explicitly ask for.
