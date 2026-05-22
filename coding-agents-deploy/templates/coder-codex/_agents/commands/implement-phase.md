---
name: implement-phase
description: Implement one or more phases (by number) from {{plan_path}}, review with the read-only review-iterate agent, iterate fixes until clean, then commit locally. If no phase numbers are provided, auto-detects the in-progress phase, otherwise the next unimplemented one (never a blocked phase).
---

# /implement-phase

Implement one or more phases from `{{plan_path}}`, spawn the read-only `review-iterate` agent to audit them, implement any findings yourself, re-spawn the reviewer, and iterate until the reviewer reports clean. Then commit locally.

Invoke as `/implement-phase 19` (single phase) or `/implement-phase 19 20 21` (multiple phases). Comma-separated also works: `/implement-phase 19,20,21`. If no phase numbers are provided, the command auto-detects: the in-progress phase if there is one (finish it before starting anything new), otherwise the lowest-numbered phase not yet marked complete. It never auto-starts a phase the plan flags as blocked.

When implementing multiple phases, implement them all before building, testing, and reviewing as a single batch.

**Live progress overlay.** This command writes `{{plan_path}}.progress.json` (sibling of the plan) to publish live state during the phase – which items are in flight, which inner-review cycle is running, an activity log, and any judgment calls worth surfacing to the reviewer. After every write, also bake the rendered view:

```
python .deployed-agents/plan-renderer/bake.py --plan {{plan_path}}
```

See **Live progress overlay** in `.deployed-agents/conventions.md` for the schema and the **Implementer write checkpoints** table for the exact when/what of each update. The bake is fast (a single Python invocation) – do not skip it after a progress write, or the user sees stale state in the browser.

## Steps

### 0. First-run check

Before anything else, do the **First-run self-configuration** in `.deployed-agents/conventions.md`: if any `<add …>` / `Unknown stack` / generic-fallback deploy placeholders remain, fill them from the actual repo (this file's commands, `.claude/settings.json`, and the `review-iterate` agent), report a one-line summary, then continue. Skip once the placeholders are gone.

### 1. Determine which phases to implement

Parse `$ARGUMENTS` for phase numbers. If provided (e.g. `19` or `19 20 21`), split on spaces and/or commas. If no arguments are provided, read `{{plan_path}}` and auto-detect the target phase in this order: (1) the lowest-numbered phase marked in-progress (a `⚠️`/`⚠` marker on its heading) – carry its unfinished work to completion before starting anything new; (2) if none is in-progress, the lowest-numbered phase with no `✅` completion marker; (3) never auto-select a phase the plan flags as blocked or gated on unresolved open questions – if such a phase is the only candidate or is explicitly named, surface it and stop (clearing the block is the user's).

For each target phase, read the relevant section of `{{plan_path}}`, then reconcile the plan against disk to find only what still needs implementing: for each task or file the phase calls out, check whether it already exists and satisfies the plan. Skip work that is already complete; implement only the outstanding remainder. Treat status bookkeeping only as a signal of intended scope, never edit it.

Report to the user: which phases you're implementing and what each covers – and when auto-detected, which phase you chose, whether it was explicit or auto-detected and why, and what you found already done.

**Plan-ambiguity stop.** Before starting, scan the target phase for unresolved open questions, TBDs, or sections explicitly flagged as needing input. If you find any – or if the current code has drifted from the plan in a way that affects this phase – stop and ask the user. Don't guess on architecture.

### 2. Fetch-first

Run `git fetch origin && git status --short --untracked-files=all` and report what you find. Untracked files belong to someone – note them but don't revert them.

- **Origin ahead, no work in progress**: `git pull --rebase origin <current-branch>` and continue (the branch you are on; this overlay never assumes `main`).
- **Origin ahead, work in progress**: stop and surface the divergence – let the user decide whether to rebase, reset, or proceed.
- **Dirty worktree with unrelated user changes**: do not revert user changes. Work around them. If they actively block implementation, report a blocker.

### 2.5. Initialise progress overlay

For each target phase, ensure the phase's block in `{{plan_path}}.progress.json` exists. Create it if missing: `started_at` = now, `sub_state` = `"coding"`, `cycle` = `1`, `cycle_cap` = `10`, `items` keyed off the plan's `[w*]`/`[a*]`/`[f*]` bullet IDs (all `state: "pending"` initially), `activity` opens with `"phase started"`. Set `active_phase` to the lowest target phase number. Then bake.

If the plan's bullets do not yet carry stable IDs, fall back to plain `1`, `2`, … indices (per kind) – the renderer matches by index when no ID prefix is present. Stable IDs survive bullet reorders; index-based fallback does not.

### 3. Implement the phases

Implement every artifact listed under each target phase. Follow the project conventions in `.deployed-agents/conventions.md` and {{plan_path}}. Reuse existing helpers before introducing new ones – grep first.

As you work, update `progress.json` per the **Implementer write checkpoints** table in `.deployed-agents/conventions.md` – at minimum: flip a Work or Files item to `"in-progress"` when you start it, to `"done"` when finished, and bake after each flip. Skip the bake and the user's open browser tab on the rendered HTML goes stale.

**Implement the phase in full before you build or call the reviewer.** Every artifact, file, and task the phase calls out must be written and wired – no partial passes, no "build now and finish the rest after the review". Before leaving this step, re-read the phase and walk its `### Work`, `### Acceptance Criteria`, and the `## Files to Create or Modify by Phase` list (files to create *and* files to modify) against what you actually wrote; if any item is unwritten, stubbed where the plan expects an implementation, or only half-done, finish it now. The build and the reviewer are gates on a *complete* phase, not a progress check on a partial one – a partial pass just burns a build/review cycle.

Do NOT implement files from phases beyond those specified. Stubs that the plan says will be wired in a later phase remain stubs (constructor + minimal body, throw `NotImplementedException` if needed).

Do NOT modify `{{plan_path}}` or any other plan/data-model docs. The user owns plan bookkeeping. The reviewer may report documentation staleness as `[DOC]` findings – relay those to the user verbatim at the end. The `## Decisions` section is free-form and live: if implementation reveals a decision that should be added or changed, you may *suggest* that edit (state the proposed Decisions wording in your final report for the user/reviewer to apply) – but never edit the plan yourself.

### 4. Build

```bash
{{build_cmd}}
```

Reach this step only once the phase is fully implemented (step 3 gate). Fix every compilation error before proceeding. Iterate build → fix until clean. Do NOT run tests at this stage – the review-iterate agent is responsible for testing.

**Pre-review self-sweep (before spawning the reviewer for the first time).** The reviewer's convergence-discipline rules forbid surfacing new instances of the same finding-class across multiple cycles, but the implementer can pre-empt entire sweep classes by doing them here once:

- **Naming sweep.** Grep every file the phase touched for single-letter callback params and accumulator pairs the reviewer's abbreviation list flags: `\.(find|filter|map|some|every)\(\([a-z]\)`, `\.(reduce|sort)\(\([a-z],\s*[a-z]\)`, plus the project's banned short-name list (`arr`, `obj`, `val`, `tmp`, `idx`, `cnt`, `cfg`, `opts`, `ctx`, `len`, `cur`, `buf`, `ret`, `dst`, `src`, `fn`, `cb`, `prev`). Rename in one pass.
- **Dead export sweep.** For every new module the phase introduced, grep the repo for each `module.exports` (or equivalent) key. Drop or document any export with no consumer.
- **Bare config-literal sweep.** For every file the plan calls config-driven (engine/algorithm modules), grep for bare numeric literals (≥2 digits, excluding 0/1) and confirm each one comes from a constants module / a request-time argument / has a comment explaining why it cannot live in config.

These checks duplicate the reviewer's first-pass sweeps; doing them here means the reviewer reports zero of them on cycle 1 instead of trickling them across cycles 3–8.

### 5. Spawn the reviewer (read-only audit)

Before spawning, update the active phase block in `progress.json`: set `sub_state: "inner-review"`; on cycles ≥ 2 increment `cycle`; append activity `"inner-review pass requested (cycle K)"`. Bake.

Spawn the `review-iterate` agent (`.agents/agents/review-iterate.md`). Use this prompt:

> Independently review Phase N[, Phase M, …] against `{{plan_path}}` and the code on disk. Do NOT assume anything is implemented – verify each `### Work` and `### Acceptance Criteria` item against the actual code yourself, checking all items in your review checklist. Report findings as BLOCKER / MAJOR / MINOR / NIT. Do NOT implement fixes – just report what's wrong.

Hand the reviewer only the phase number(s). Do NOT describe, summarize, or list what you changed – the reviewer audits the plan and the code from scratch and must not be primed by your account of the work.

### 6. Implement review findings yourself

For each non-trivial finding the reviewer returned, append an activity entry to `progress.json` with `role: "inner-review"` and a short `msg` like `finding[<SEV>] <file:line> <summary>`. Set `sub_state: "applying-fixes"`. Bake.

The reviewer returned a list of findings. YOU (the main conversation) implement the fixes for CODE findings. Findings come in three categories:

**Code findings (you fix):**
- Fix every BLOCKER and MAJOR finding in the code.
- Fix MINOR findings unless they conflict with the current architecture.
- Rebuild after each batch. Do NOT run tests – the reviewer will.

**Documentation findings (relay to user, do NOT fix):**
- Findings tagged `[DOC]` are documentation inconsistencies – the reviewer found that `{{plan_path}}` or another doc is stale.
- Relay `[DOC]` findings to the user verbatim. Do NOT edit the plan or related docs yourself.
- `[DOC]` findings are NOT blockers for the review gate.
- **Never report completion status as a finding.** Filter out any `[ ]`/`[x]` or phase `✅` bookkeeping before relaying.

**Shared-library suggestions (collect, do NOT implement here):**
- Findings tagged `[SHARED]` are suggestions for a separate shared-library or component-repo improvement.
- Accumulate all `[SHARED]` findings across review passes.
- After the review loop is clean, write them to a `suggested_improvements.md` file in the shared-library repo (see step 8). The user can tell you which repo – if unspecified, accumulate them and ask.

### 7. Re-spawn the reviewer

Spawn the `review-iterate` agent again with the same prompt. The reviewer audits the updated code and reports new findings.

Repeat steps 6–7 (you fix code, reviewer audits) until the reviewer returns zero BLOCKER, zero MAJOR, and zero non-`[DOC]` non-`[SHARED]` MINOR findings. `[DOC]` and `[SHARED]` findings do NOT block the review gate. NITs are acceptable but fix the trivial ones.

When the reviewer reports clean, set `sub_state: "ready"` in `progress.json` and bake – this is the signal to the outer reviewer (and the user) that the phase is implementer-clean.

**Repeated-feedback discipline**: if the reviewer reports the same finding across two cycles, address the exact `file:line` they cited before doing any other work. Don't add adjacent fixes – fix the specific thing first, rebuild, then re-spawn the reviewer.

**Cycle cap: 10 implementer cycles.** If you've done 10 rounds without approval, stop and surface the situation to the user – don't grind indefinitely.

### 8. Write shared-library suggestions (if any)

If the review accumulated `[SHARED]` findings, append them to the shared-library repo's `docs/suggested_improvements.md` (path the user has told you about). Format:

```markdown
## <YYYY-MM-DD> – Phase N

### <affected shared component>

**Workaround in {{project_name}}**: `<file>:<line>` – <one-line description>

**Suggestion**: <concrete suggested improvement>
```

### 9. Commit locally

Stage exactly the files that changed for this phase. Use a focused message:

```
git add <files...>
git commit -m "Phase N: <Title>

<1-3 line summary of what shipped>"
```

Do not use `git add -A` (stray files sneak in). Do not use `--no-verify`. Do not push – local commit only; the user pushes when they're ready. **When implementing multiple phases in one run, commit each phase separately as you go; push only after every phase in the run has been committed.**

After the commit, append activity `"committed <short-sha>"` to `progress.json` and bake. Keep `sub_state: "ready"`; the outer reviewer (`review-implementation`) is what promotes the phase to `completed` and clears the progress block.

### 10. Update this command, implement-fixes, and review-iterate (mandatory last step before reporting)

Look back at the run that just finished. Edit the overlay files IN PLACE before you write your final report – this is what keeps the next run shorter than this one. Triggers:

- **Reviewer re-flagged the same finding across two+ cycles** → update `.agents/agents/review-iterate.md` to call it out as a first-pass check, OR update this command's expectations so the implementer catches it before the first review spawn.
- **Reviewer surfaced a NEW class of finding only in a later cycle** (e.g. abbreviations flagged piecemeal across passes) → update `review-iterate.md` to require an EXHAUSTIVE sweep of that class on the first pass.
- **Reviewer summarised "Review complete – clean" while also listing new MINORs** → tighten the "clean means clean" rule in `review-iterate.md`.
- **Reviewer misclassified a DOC-only item as MAJOR/BLOCKER** → tighten the DOC-vs-code-severity guidance in `review-iterate.md`.
- **A specific recurring fix, convention, or unclear step** → encode it here, in `implement-fixes.md`, or in `review-iterate.md`'s checklist as appropriate.

Keep `implement-phase.md` and `implement-fixes.md` in sync where they overlap (review loop, severity protocol, commit protocol). Targets are the local `.agents/` files (gitignored, persist for this project). If the source-of-truth templates outside the repo are accessible, mirror the changes there too so the next deploy carries them.

This step is **mandatory** before reporting. If nothing is genuinely worth changing, say so explicitly in the report ("no overlay updates this run") so it's a deliberate decision, not an oversight.

### 11. Report

Per phase: one terse line. `Phase N (<Title>) – implemented, build clean, tests <X>/<Y>, committed <short-sha>, rendered HTML: {{plan_path}}.html.`

At the end, **always output the complete list of `[DOC]` findings accumulated across all review passes.** Even if you mentioned some during earlier steps, re-list every `[DOC]` finding so the user has one consolidated list. **Also list any `[SHARED]` findings** that were written to the shared-library suggestions file.

If you appended any `proposed_decisions` to `progress.json` during the run, note them in the report so the user knows there are pending decisions for the outer reviewer to apply or reject.

## Things you do NOT do

- Do not skip the reviewer. The inner loop has caught real bugs.
- Do not bundle multiple phases into one commit when implementing them sequentially. One phase, one commit (unless the user asked for a batch).
- Do not push. Local commits only.
- Do not edit phases other than the active one in the plan file.
- Do not silently downgrade a phase's scope to make it pass review. If the plan asks for X and X is genuinely problematic, stop and ask.
