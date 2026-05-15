---
description: Implement one or more phases (by number) from {{plan_path}}, review with the read-only review-iterate agent, iterate fixes until clean, then commit locally. If no phase numbers are provided, auto-detects the next unimplemented phase.
aliases: [iphase, next-phase]
---

# /implement-phase

Implement one or more phases from `{{plan_path}}`, spawn the read-only `review-iterate` agent to audit them, implement any findings yourself, re-spawn the reviewer, and iterate until the reviewer reports clean. Then commit locally.

Invoke as `/implement-phase 19` (single phase) or `/implement-phase 19 20 21` (multiple phases). Comma-separated also works: `/implement-phase 19,20,21`. If no phase numbers are provided, the command auto-detects the lowest-numbered phase not yet marked complete.

When implementing multiple phases, implement them all before building, testing, and reviewing as a single batch.

## Steps

### 1. Determine which phases to implement

Parse `$ARGUMENTS` for phase numbers. If provided (e.g. `19` or `19 20 21`), split on spaces and/or commas. If no arguments are provided, read `{{plan_path}}` and identify the lowest-numbered phase NOT marked complete (no `✅` in its heading) — implement just that one.

For each target phase, read the relevant section of `{{plan_path}}`. Also check what files from each phase already exist on disk, since a partial implementation may be present.

Report to the user: which phases you're implementing and what each covers.

**Plan-ambiguity stop.** Before starting, scan the target phase for unresolved open questions, TBDs, or sections explicitly flagged as needing input. If you find any — or if the current code has drifted from the plan in a way that affects this phase — stop and ask the user. Don't guess on architecture.

### 2. Fetch-first

Run `git fetch origin && git status --short --untracked-files=all` and report what you find. Untracked files belong to someone — note them but don't revert them.

- **Origin ahead, no work in progress**: `git pull --rebase origin main` and continue.
- **Origin ahead, work in progress**: stop and surface the divergence — let the user decide whether to rebase, reset, or proceed.
- **Dirty worktree with unrelated user changes**: do not revert user changes. Work around them. If they actively block implementation, report a blocker.

### 3. Implement the phases

Implement every artifact listed under each target phase. Follow the project conventions in `AGENTS.md` and {{plan_path}}. Reuse existing helpers before introducing new ones — grep first.

Do NOT implement files from phases beyond those specified. Stubs that the plan says will be wired in a later phase remain stubs (constructor + minimal body, throw `NotImplementedException` if needed).

Do NOT modify `{{plan_path}}` or any other plan/data-model docs. The user owns plan bookkeeping. The reviewer may report documentation staleness as `[DOC]` findings — relay those to the user verbatim at the end.

### 4. Build

```bash
{{build_cmd}}
```

Fix every compilation error before proceeding. Iterate build → fix until clean. Do NOT run tests at this stage — the review-iterate agent is responsible for testing.

### 5. Spawn the reviewer (read-only audit)

Spawn the `review-iterate` agent (`.claude/agents/review-iterate.md`). Use this prompt:

> Review the Phase N[, Phase M, …] implementation for completeness and correctness against `{{plan_path}}`. Check all items in your review checklist. Report findings as BLOCKER / MAJOR / MINOR / NIT. Do NOT implement fixes — just report what's wrong.

### 6. Implement review findings yourself

The reviewer returned a list of findings. YOU (the main conversation) implement the fixes for CODE findings. Findings come in three categories:

**Code findings (you fix):**
- Fix every BLOCKER and MAJOR finding in the code.
- Fix MINOR findings unless they conflict with the current architecture.
- Rebuild after each batch. Do NOT run tests — the reviewer will.

**Documentation findings (relay to user, do NOT fix):**
- Findings tagged `[DOC]` are documentation inconsistencies — the reviewer found that `{{plan_path}}` or another doc is stale.
- Relay `[DOC]` findings to the user verbatim. Do NOT edit the plan or related docs yourself.
- `[DOC]` findings are NOT blockers for the review gate.
- **Never report completion status as a finding.** Filter out any `[ ]`/`[x]` or phase `✅` bookkeeping before relaying.

**Shared-library suggestions (collect, do NOT implement here):**
- Findings tagged `[SHARED]` are suggestions for a separate shared-library or component-repo improvement.
- Accumulate all `[SHARED]` findings across review passes.
- After the review loop is clean, write them to a `suggested_improvements.md` file in the shared-library repo (see step 8). The user can tell you which repo — if unspecified, accumulate them and ask.

### 7. Re-spawn the reviewer

Spawn the `review-iterate` agent again with the same prompt. The reviewer audits the updated code and reports new findings.

Repeat steps 6–7 (you fix code, reviewer audits) until the reviewer returns zero BLOCKER, zero MAJOR, and zero non-`[DOC]` non-`[SHARED]` MINOR findings. `[DOC]` and `[SHARED]` findings do NOT block the review gate. NITs are acceptable but fix the trivial ones.

**Repeated-feedback discipline**: if the reviewer reports the same finding across two cycles, address the exact `file:line` they cited before doing any other work. Don't add adjacent fixes — fix the specific thing first, rebuild, then re-spawn the reviewer.

**Cycle cap: 3 implementer cycles.** If you've done 3 rounds without approval, stop and surface the situation to the user — don't grind indefinitely.

### 8. Write shared-library suggestions (if any)

If the review accumulated `[SHARED]` findings, append them to the shared-library repo's `docs/suggested_improvements.md` (path the user has told you about). Format:

```markdown
## <YYYY-MM-DD> — Phase N

### <affected shared component>

**Workaround in {{project_name}}**: `<file>:<line>` — <one-line description>

**Suggestion**: <concrete suggested improvement>
```

### 9. Commit locally

Stage exactly the files that changed for this phase. Use a focused message:

```
git add <files...>
git commit -m "Phase N: <Title>

<1-3 line summary of what shipped>"
```

Do not use `git add -A` (stray files sneak in). Do not use `--no-verify`. Do not push — local commit only; the user pushes when they're ready. **When implementing multiple phases in one run, commit each phase separately as you go; push only after every phase in the run has been committed.**

### 10. Report

Per phase: one terse line. `Phase N (<Title>) — implemented, build clean, tests <X>/<Y>, committed <short-sha>.`

At the end, **always output the complete list of `[DOC]` findings accumulated across all review passes.** Even if you mentioned some during earlier steps, re-list every `[DOC]` finding so the user has one consolidated list. **Also list any `[SHARED]` findings** that were written to the shared-library suggestions file.

## Things you do NOT do

- Do not skip the reviewer. The inner loop has caught real bugs.
- Do not bundle multiple phases into one commit when implementing them sequentially. One phase, one commit (unless the user asked for a batch).
- Do not push. Local commits only.
- Do not edit phases other than the active one in the plan file.
- Do not silently downgrade a phase's scope to make it pass review. If the plan asks for X and X is genuinely problematic, stop and ask.
