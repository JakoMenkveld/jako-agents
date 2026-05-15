---
name: implement-phase
description: Implement one or more phases (by number) from {{plan_path}}, review with the read-only review-iterate agent, iterate fixes until clean, then commit locally. If no phase numbers are provided, auto-detects the next unimplemented phase.
---

# implement-phase

Implement one or more phases from `{{plan_path}}`, spawn the read-only `review-iterate` agent to audit, fix any findings yourself, re-spawn the reviewer, and iterate until clean. Then commit locally.

Invoke as `implement-phase 19` (single), `implement-phase 19 20 21` (multi-phase), or with no arguments to auto-detect the lowest-numbered phase not yet marked complete.

## Steps

### 1. Determine phases

Parse arguments for phase numbers. If none, read `{{plan_path}}` and pick the lowest-numbered phase without a `✅` in its heading. Read each target phase's section in full.

Report to the user which phases you'll implement. If a phase has open questions or TBDs, stop and ask before starting.

### 2. Fetch-first

`git fetch origin && git status`. If origin is ahead with no work in progress, `git pull --rebase`. If work in progress and origin moved, surface to the user.

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

**Cycle cap: 3 implementer cycles.** After 3 rounds without approval, stop and surface.

### 8. Commit locally

```bash
git add <files...>
git commit -m "Phase N: <Title>

<1-3 line summary>"
```

No `git add -A`. No `--no-verify`. Do not push.

### 9. Report

Per phase, one terse line. At the end, output the consolidated list of `[DOC]` findings across all review passes plus any `[SHARED]` findings written.

## Things you do NOT do

- Skip the reviewer.
- Bundle multiple phases into one commit unless asked.
- Push.
- Edit phases other than the active one in the plan file.
- Silently downgrade scope to pass review.
