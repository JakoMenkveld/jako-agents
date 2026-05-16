---
name: implement-phase
description: Implement one or more phases (by number) from {{plan_path}}, review with the read-only review-iterate agent, iterate fixes until clean, then commit locally. If no phase numbers are provided, auto-detects the in-progress phase, otherwise the next unimplemented one (never a blocked phase).
---

# implement-phase

Implement one or more phases from `{{plan_path}}`, spawn the read-only `review-iterate` agent to audit, fix any findings yourself, re-spawn the reviewer, and iterate until clean. Then commit locally.

Invoke as `implement-phase 19` (single), `implement-phase 19 20 21` (multi-phase), or with no arguments to auto-detect: the in-progress phase if there is one (finish it before starting anything new), otherwise the lowest-numbered phase not yet marked complete. It never auto-starts a phase the plan flags as blocked.

## Steps

### 1. Determine phases

Parse arguments for phase numbers. If none, read `{{plan_path}}` and auto-detect the target phase in this order: (1) the lowest-numbered phase marked in-progress (a `⚠️`/`⚠` marker on its heading) — carry its unfinished work to completion before starting anything new; (2) if none is in-progress, the lowest-numbered phase with no `✅` completion marker; (3) never auto-select a phase the plan flags as blocked or gated on unresolved open questions — if such a phase is the only candidate or is explicitly named, surface it and stop (clearing the block is the user's). Read each target phase's section in full, then reconcile the plan against disk: for each task or file the phase calls out, check whether it already exists and satisfies the plan, skip what is already complete, and implement only the outstanding remainder. Treat status bookkeeping only as a signal of intended scope, never edit it.

Report to the user which phases you'll implement — and when auto-detected, which phase you chose, whether it was explicit or auto-detected and why, and what you found already done.

**Plan-ambiguity stop.** Before starting, scan the target phase for unresolved open questions, TBDs, or sections explicitly flagged as needing input. If you find any — or if the current code has drifted from the plan in a way that affects this phase — stop and ask the user. Don't guess on architecture.

### 2. Fetch-first

Run `git fetch origin && git status --short --untracked-files=all`. Untracked files belong to someone — note them but don't revert them.

- **Origin ahead, no work in progress**: `git pull --rebase origin main` and continue.
- **Origin ahead, work in progress**: stop and surface the divergence — let the user decide.
- **Dirty worktree with unrelated user changes**: do not revert user changes. Work around them. If they actively block implementation, report a blocker.

### 3. Implement

Implement every artifact under each target phase. Follow `AGENTS.md` and the plan. Reuse existing helpers before introducing new ones.

Do NOT implement files from phases beyond those specified. Stubs the plan defers to a later phase remain stubs.

Do NOT modify `{{plan_path}}` or related plan/data-model docs. The user owns plan bookkeeping. The reviewer will surface staleness as `[DOC]` findings — relay them verbatim at the end.

### 4. Build

```bash
{{build_cmd}}
```

Iterate build → fix until clean. Do NOT run tests at this stage.

### 5. Spawn the reviewer

Spawn the `review-iterate` agent (`.agents/agents/review-iterate.md`) with:

> Review the Phase N[, Phase M, …] implementation against `{{plan_path}}`. Report findings as BLOCKER / MAJOR / MINOR / NIT. Do NOT implement fixes.

### 6. Implement reviewer findings

Three categories:

**Code findings**: fix BLOCKER/MAJOR always; fix MINOR unless they conflict with the architecture. Rebuild after each batch.
**`[DOC]` findings**: relay to user verbatim, do not edit docs. Filter out any `[ ]`/`[x]` or `✅` bookkeeping.
**`[SHARED]` findings**: collect for a separate shared-library suggestions file (path from the user; ask if unspecified).

### 7. Re-spawn the reviewer

Same prompt. Loop steps 6–7 until clean (zero BLOCKER/MAJOR/non-`[DOC]`-non-`[SHARED]` MINOR).

**Repeated-feedback discipline**: if the reviewer reports the same finding across two cycles, address the exact `file:line` they cited before doing any other work.

**Cycle cap: 3 implementer cycles.** After 3 rounds without approval, stop and surface.

### 8. Commit locally

```bash
git add <files...>
git commit -m "Phase N: <Title>

<1-3 line summary>"
```

No `git add -A`. No `--no-verify`. Do not push. **When implementing multiple phases in one run, commit each phase separately as you go; push only after every phase in the run has been committed.**

### 9. Capture lessons learned

Reflect on patterns that emerged this run. If anything is generally useful — a recurring fix, a convention the reviewer kept flagging, a step that needed clarifying — update this command file, the sibling `implement-fixes` command (keep the two in sync where they overlap), and the `review-iterate` agent checklist. The `.agents/` directory is gitignored, so these updates stay local: they won't appear in the commit, but they persist for future sessions in this project.

### 10. Report

Per phase, one terse line. At the end, output the consolidated list of `[DOC]` findings across all review passes plus any `[SHARED]` findings written.

## Things you do NOT do

- Skip the reviewer.
- Bundle multiple phases into one commit unless asked.
- Push.
- Edit phases other than the active one in the plan file.
- Silently downgrade scope to pass review.
