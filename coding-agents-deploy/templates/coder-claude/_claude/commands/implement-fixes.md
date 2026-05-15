---
description: Take a list of findings (may span multiple phases), implement the fixes, review with review-iterate, iterate until clean, then commit locally.
aliases: [fixes, ifix]
---

# /implement-fixes

Take a user-provided list of findings, implement the fixes yourself, spawn the read-only `review-iterate` agent to audit, iterate until clean, then commit locally.

## Steps

### 1. Parse the findings

The findings are in `$ARGUMENTS`. If they reference specific files, read those first. If they reference phases in `{{plan_path}}`, read the relevant phase sections.

List the findings to the user so they can confirm before you proceed.

### 2. Fetch-first

`git fetch origin && git status --short --untracked-files=all`. Untracked files belong to someone — note them but don't revert them.

- **Origin ahead, no work in progress**: `git pull --rebase origin main` and continue.
- **Origin ahead, work in progress**: stop and surface the divergence to the user.
- **Dirty worktree with unrelated user changes**: do not revert user changes. Work around them. If they actively block the fixes, report a blocker.

### 3. Implement the fixes

Work through each finding systematically. Follow project conventions (see `AGENTS.md`). Do NOT exceed the scope of the findings — no opportunistic refactors.

Do NOT modify `{{plan_path}}` or related plan/data-model docs. The reviewer may report doc staleness as `[DOC]` findings — relay those to the user.

### 4. Build

```bash
{{build_cmd}}
```

Iterate build → fix until clean. Do NOT run tests — that's the reviewer's job.

### 5. Spawn the reviewer

Spawn the `review-iterate` agent (`.claude/agents/review-iterate.md`). Prompt:

> Review the implementation after applying these fixes: [list fixes applied]. Check that each fix is correctly implemented, no regressions were introduced, and the implementation still satisfies `{{plan_path}}`. Report findings as BLOCKER / MAJOR / MINOR / NIT. Do NOT implement fixes — just report what's wrong.

### 6. Implement reviewer findings + re-spawn

Same three-category protocol as `/implement-phase`:

- **Code findings**: you fix (BLOCKER/MAJOR always; MINOR unless they conflict with current architecture).
- **`[DOC]` findings**: relay to user, do not edit docs.
- **`[SHARED]` findings**: collect for the shared-library suggestions file.

Re-spawn the reviewer after each fix batch. Iterate until clean (zero BLOCKER/MAJOR/non-`[DOC]`-non-`[SHARED]` MINOR).

**Repeated-feedback discipline**: if the reviewer reports the same finding across two cycles, address the exact `file:line` they cited before doing any other work.

**Cycle cap: 3 implementer cycles.** After 3 rounds without approval, stop and surface the situation.

### 7. Commit

```bash
git add <files...>
git commit -m "Apply fixes: <short summary>"
```

No `git add -A`, no `--no-verify`. Do not push.

### 8. Report

One-line summary plus the consolidated list of `[DOC]` findings collected across all review passes, plus any `[SHARED]` findings written.
