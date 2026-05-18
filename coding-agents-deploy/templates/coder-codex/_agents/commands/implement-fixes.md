---
name: implement-fixes
description: Take a list of findings (may span multiple phases), implement the fixes, review with review-iterate, iterate until clean, then commit locally. With no findings given, falls back to the first in-progress phase in {{plan_path}} and implements its still-unfinished work.
---

# implement-fixes

Take a user-provided list of findings, implement the fixes, spawn the `review-iterate` agent, iterate until clean, then commit locally.

## Steps

### 0. First-run check

Before anything else, do the **First-run self-configuration** in `.deployed-agents/conventions.md`: if any `<add …>` / `Unknown stack` / generic-fallback deploy placeholders remain, fill them from the actual repo (this file's commands, `.claude/settings.json`, and the `review-iterate` agent), report a one-line summary, then continue. Skip once the placeholders are gone.

### 1. Parse findings

Read the findings carefully. If they reference specific files, read those first. If they reference phases in `{{plan_path}}`, read the relevant sections.

**If no findings are given**, do not stop — fall back to the plan: select the first in-progress phase in `{{plan_path}}`, read its full section, and reconcile it against disk. Each unfinished task or missing/incomplete file the phase calls out becomes a synthetic finding; skip anything already implemented. Read status bookkeeping only as a scope signal — never edit it. Explicitly given findings always take precedence over this fallback.

List the findings back to the user to confirm before proceeding, noting whether each was explicitly given or auto-derived (and from which phase).

### 2. Fetch-first

Run `git fetch origin && git status --short --untracked-files=all`. Untracked files belong to someone — note them but don't revert them.

- **Origin ahead, no work in progress**: `git pull --rebase origin main` and continue.
- **Origin ahead, work in progress**: stop and surface the divergence.
- **Dirty worktree with unrelated user changes**: do not revert user changes. Work around them. If they actively block the fixes, report a blocker.

### 3. Implement the fixes

Work systematically through each finding. Follow project conventions in `.deployed-agents/conventions.md`. Do not exceed the scope of the findings.

**Apply every finding in full before you build or call the reviewer.** Finish the entire findings list — no partial passes, no building or spawning the reviewer with some findings still unaddressed. Before leaving this step, walk the findings list item by item and confirm each is actually resolved in the code. The build and the reviewer are gates on the *complete* fix set, not a progress check on a partial one — a partial pass just burns a build/review cycle.

Do NOT modify `{{plan_path}}` or related plan/data-model docs.

### 4. Build

```bash
{{build_cmd}}
```

Reach this step only once every finding is applied (step 3 gate). Iterate build → fix until clean. Do NOT run tests — that's the reviewer's job.

### 5. Spawn the reviewer

Spawn `review-iterate` (`.agents/agents/review-iterate.md`):

> Independently verify whether each of the following findings is fully resolved in the code, that no regression was introduced, and that the code still satisfies `{{plan_path}}`: [paste the findings list from step 1 verbatim]. Do NOT assume any of them were addressed — check each against the actual code yourself. Report findings as BLOCKER / MAJOR / MINOR / NIT. Do NOT implement fixes.

Hand the reviewer the original findings list to verify against — not an account of what you did. Do NOT describe or summarize the changes you made; the reviewer judges each finding against the plan and the code from scratch.

### 6. Iterate

Same three-category protocol as `implement-phase`.

**Repeated-feedback discipline**: if the reviewer reports the same finding across two cycles, address the exact `file:line` they cited before doing any other work.

**Cycle cap: 10 implementer cycles.** After 10 rounds without approval, stop and surface.

### 7. Commit locally

```bash
git add <files...>
git commit -m "Apply fixes: <short summary>"
```

No `git add -A`. No `--no-verify`. Do not push.

### 8. Capture lessons learned

Reflect on patterns that emerged this run. If anything is generally useful, update this command file, the sibling `implement-phase` command (keep the two in sync where they overlap), and the `review-iterate` agent checklist. The `.agents/` directory is gitignored, so these updates stay local — they won't appear in the commit, but they persist for future sessions in this project.

### 9. Report

One-line summary plus consolidated `[DOC]` and `[SHARED]` findings.
