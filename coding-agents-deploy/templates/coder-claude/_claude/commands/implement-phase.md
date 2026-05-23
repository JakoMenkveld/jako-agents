---
description: Implement one or more phases (by number) from {{plan_path}}, review with the read-only review-iterate agent, iterate fixes until clean, then commit locally. If no phase numbers are provided, auto-detects the in-progress phase, otherwise the next unimplemented one (never a blocked phase).
aliases: [iphase, next-phase]
---

# /implement-phase

Implement one or more phases from `{{plan_path}}`, spawn the read-only `review-iterate` agent to audit them, implement any findings yourself, re-spawn the reviewer, and iterate until the reviewer reports clean. Then commit locally.

Invoke as `/implement-phase 19` (single phase) or `/implement-phase 19 20 21` (multiple phases). Comma-separated also works: `/implement-phase 19,20,21`. If no phase numbers are provided, the command auto-detects: the in-progress phase if there is one (finish it before starting anything new), otherwise the lowest-numbered phase not yet marked complete. It never auto-starts a phase the plan flags as blocked.

When implementing multiple phases, implement them all before building, testing, and reviewing as a single batch.

**Live progress overlay (mandatory, not optional).** This command writes `{{plan_progress_path}}` (sibling of the plan) at every meaningful transition so the user can watch a live HTML view (`{{plan_html_path}}`) of what's happening. **Progress writes are step gates, not commentary** – if you do real work (start a Work item, finish it, kick off the reviewer, receive findings, apply a batch of fixes, hit a decision) without writing the overlay and baking, you have broken the contract. The bake is one fast Python invocation – skipping it leaves the user's browser tab stuck on stale state:

```
python .deployed-agents/plan-renderer/bake.py --plan {{plan_path}}
```

See **Live progress overlay** in `.deployed-agents/conventions.md` for the schema and the **Implementer write checkpoints** table for the exact when/what of each update. The user judges "is it making progress?" entirely from this overlay; silence reads as a stall. Every step below that does real work ends in a checkpoint write – treat the write as part of the step, not a footnote.

## Steps

### 0. First-run check

Before anything else, do the **First-run self-configuration** in `.deployed-agents/conventions.md`: if any `<add …>` / `Unknown stack` / generic-fallback deploy placeholders remain, fill them from the actual repo (this file's commands, `.claude/settings.json`, and the `review-iterate` agent), report a one-line summary, then continue. Skip once the placeholders are gone.

### 1. Determine which phases to implement

Parse `$ARGUMENTS` for phase numbers. If provided (e.g. `19` or `19 20 21`), split on spaces and/or commas. If no arguments are provided, read `{{plan_path}}` and auto-detect the target phase in this order: (1) the lowest-numbered phase marked in-progress (a `⚠️`/`⚠` marker on its heading) — carry its unfinished work to completion before starting anything new; (2) if none is in-progress, the lowest-numbered phase with no `✅` completion marker; (3) never auto-select a phase the plan flags as blocked or gated on unresolved open questions — if such a phase is the only candidate or is explicitly named, surface it and stop (clearing the block is the user's).

For each target phase, read the relevant section of `{{plan_path}}`, then reconcile the plan against disk to find only what still needs implementing: for each task or file the phase calls out, check whether it already exists and satisfies the plan. Skip work that is already complete; implement only the outstanding remainder. Treat status bookkeeping only as a signal of intended scope, never edit it.

Report to the user: which phases you're implementing and what each covers – and when auto-detected, which phase you chose, whether it was explicit or auto-detected and why, and what you found already done.

**Plan-ambiguity stop.** Before starting, scan the target phase for in-phase TBDs or sections explicitly flagged as needing input. If you find any – or if the current code has drifted from the plan in a way that affects this phase – stop and ask the user. Don't guess on architecture. (Plan-wide `## Open Questions` are enforced separately by step 1.5.)

### 1.5. Open-questions gate (hard stop)

Read the `## Open Questions` section of `{{plan_path}}`. If it contains any non-empty bullet (a line starting with `-` that has content), **stop immediately**. Do not initialise the progress overlay, do not fetch, do not touch code. Open questions are user-owned and append-only; the implementer never edits them, but it also refuses to proceed while any are outstanding.

Surface every open question to the user verbatim, then ask them to clear `## Open Questions` before re-running the command, in one of two ways:

- **Resolve the question** by recording the answer in `## Decisions` and removing the bullet from `## Open Questions`; or
- **Defer the question** by moving the bullet from `## Open Questions` to `## Residual Risks` (acknowledging the risk is being carried into implementation).

This is a plan-wide gate: any open question – on the target phase or another – blocks all implementation. An empty `## Open Questions` (the heading with no bullets) is the only acceptable state.

### 2. Fetch-first

Run `git fetch origin && git status --short --untracked-files=all` and report what you find. Untracked files belong to someone — note them but don't revert them.

- **Origin ahead, no work in progress**: `git pull --rebase origin <current-branch>` and continue (the branch you are on; this overlay never assumes `main`).
- **Origin ahead, work in progress**: stop and surface the divergence — let the user decide whether to rebase, reset, or proceed.
- **Dirty worktree with unrelated user changes**: do not revert user changes. Work around them. If they actively block implementation, report a blocker.

### 2.5. Initialise progress overlay

For each target phase, ensure the phase's block in `{{plan_progress_path}}` exists. Create it if missing:
- `started_at` = now (real ISO-8601 with seconds, e.g. `2026-05-23T10:14:07Z`, **not** a midnight placeholder).
- `sub_state` = `"coding"`, `cycle` = `1`, `cycle_cap` = `10`.
- `items` keyed off the plan's `[w*]`/`[a*]`/`[f*]` bullet IDs, each seeded as `{ "state": "pending", "note": null }`. Seed `note` explicitly (even as `null`) so later writes that refresh a note via in-place property assignment don't fail on shells that can't add properties to an existing JSON object (e.g. PowerShell's `PSCustomObject`).
- `activity` opens with `{role: "implementer", msg: "phase started"}` carrying a real timestamp.

Refresh the file-level `updated_at` on every write throughout the run; the renderer surfaces it as the "updated" relative-time. Set `active_phase` to the lowest target phase number. Then bake.

If the plan's bullets do not yet carry stable IDs, fall back to plain `1`, `2`, … indices (per kind) – the renderer matches by index when no ID prefix is present. Stable IDs survive bullet reorders; index-based fallback does not.

### 3. Implement the phases

Implement every artifact listed under each target phase. Follow the project conventions in `.deployed-agents/conventions.md` and {{plan_path}}. Reuse existing helpers before introducing new ones — grep first.

**Per-item progress gate (do this for every Work item and every Files item, no exceptions).** For each `[w*]` Work item or `[f*]` Files item you pick up:

1. **Before touching the code**: write `{{plan_progress_path}}` flipping that item from `"pending"` → `"in-progress"`; refresh `updated_at`; optional one-line `note`. Bake.
2. Do the actual code work for that item.
3. **As soon as the item is written and would survive the build**: write `{{plan_progress_path}}` flipping the item to `"done"`. Bake.

A whole pass through the phase with everything still `"pending"` on disk means the overlay is broken – the user sees no movement. Batching the flips ("I'll update progress when I'm done coding") is the failure mode this gate exists to prevent. Even if an item takes ninety seconds, flip it. The bake is fast.

A judgment call that the reviewer should see (architectural choice not pre-decided in the plan, scope reduction, deferred sub-task) goes into `proposed_decisions` in the same write – do not save these up for the end of the phase.

**Implement the phase in full before you build or call the reviewer.** Every artifact, file, and task the phase calls out must be written and wired — no partial passes, no "build now and finish the rest after the review". Before leaving this step, re-read the phase and walk its `### Work`, `### Acceptance Criteria`, and the `## Files to Create or Modify by Phase` list (files to create *and* files to modify) against what you actually wrote; if any item is unwritten, stubbed where the plan expects an implementation, or only half-done, finish it now. The build and the reviewer are gates on a *complete* phase, not a progress check on a partial one — a partial pass just burns a build/review cycle.

Do NOT implement files from phases beyond those specified. Stubs that the plan says will be wired in a later phase remain stubs (constructor + minimal body, throw `NotImplementedException` if needed).

Do NOT modify `{{plan_path}}` or any other plan/data-model docs. The user owns plan bookkeeping. The reviewer may report documentation staleness as `[DOC]` findings — relay those to the user verbatim at the end. The `## Decisions` section is free-form and live: if implementation reveals a decision that should be added or changed, you may *suggest* that edit (state the proposed Decisions wording in your final report for the user/reviewer to apply) — but never edit the plan yourself.

### 4. Build

```bash
{{build_cmd}}
```

Reach this step only once the phase is fully implemented (step 3 gate). Fix every compilation error before proceeding. Iterate build → fix until clean. Do NOT run tests at this stage — the review-iterate agent is responsible for testing.

**Pre-review self-sweep (before spawning the reviewer for the first time).** The reviewer's convergence-discipline rules forbid surfacing new instances of the same finding-class across multiple cycles, but the implementer can pre-empt entire sweep classes by doing them here once:

- **Naming sweep.** Grep every file the phase touched for single-letter callback params and accumulator pairs the reviewer's abbreviation list flags: `\.(find|filter|map|some|every)\(\([a-z]\)`, `\.(reduce|sort)\(\([a-z],\s*[a-z]\)`, plus the project's banned short-name list (`arr`, `obj`, `val`, `tmp`, `idx`, `cnt`, `cfg`, `opts`, `ctx`, `len`, `cur`, `buf`, `ret`, `dst`, `src`, `fn`, `cb`, `prev`). Rename in one pass.
- **Dead export sweep.** For every new module the phase introduced, grep the repo for each `module.exports` (or equivalent) key. Drop or document any export with no consumer.
- **Bare config-literal sweep.** For every file the plan calls config-driven (engine/algorithm modules), grep for bare numeric literals (≥2 digits, excluding 0/1) and confirm each one comes from a constants module / a request-time argument / has a comment explaining why it cannot live in config.
- **Validator-rejection-test sweep.** For every new module that exports a `validateX` / `assertValidX` pair (or any other documented-failure-mode function), enumerate the rejection branches inside the validator and confirm a test exercises each one. Validator rejection paths are a recurring trickle source – the reviewer's `Validator-schema-completeness sweep` (review-iterate.md) covers it, but pre-empting catches every branch in one bundle before the first review spawn. Cover at minimum: non-plain-object input, wrong `type` discriminator, missing required field, unknown enum value, container field set to a non-object/non-array, and one rejection driven by a constructed-then-mutated object (to confirm the validator is not relying on the constructor's checks).
- **Cache-behavioural-branch sweep.** When the phase introduces a cache with hit / miss / refresh / mtime-only-touch / external-input-invalidation branches, enumerate every distinct branch in the cache implementation and confirm a test drives each. Trickle-cause in past runs: "touch-without-edit" or one specific runtime-input is missing a test, surfaced only on cycle 2+.

These checks duplicate the reviewer's first-pass sweeps; doing them here means the reviewer reports zero of them on cycle 1 instead of trickling them across cycles 3–8.

### 5. Spawn the reviewer (read-only audit)

**Pre-spawn write (gate – do this before the Agent tool call, not after).** Edit `{{plan_progress_path}}` to: set `sub_state: "inner-review"`; on cycles ≥ 2 increment `cycle`; append activity `{role: "implementer", msg: "inner-review pass requested (cycle K)"}`; refresh `updated_at`. Bake. Only then spawn the agent. The user must see the cycle change in their browser before the reviewer goes silent for a few minutes.

Spawn the `review-iterate` agent (`.claude/agents/review-iterate.md`). Use this prompt:

> Independently review Phase N[, Phase M, …] against `{{plan_path}}` and the code on disk. Do NOT assume anything is implemented — verify each `### Work` and `### Acceptance Criteria` item against the actual code yourself, checking all items in your review checklist. Report findings as BLOCKER / MAJOR / MINOR / NIT. Do NOT implement fixes — just report what's wrong.

Hand the reviewer only the phase number(s). Do NOT describe, summarize, or list what you changed — the reviewer audits the plan and the code from scratch and must not be primed by your account of the work.

### 6. Implement review findings yourself

**Post-review write (gate – do this before the first code edit in response to findings).** When the reviewer returns, edit `{{plan_progress_path}}` in a single write:
- Set `sub_state: "applying-fixes"`.
- Append one activity entry per non-trivial finding: `{role: "inner-review", msg: "finding[<SEV>] <file:line> <one-line summary>"}`. Skip pure NIT cosmetic items, keep everything else (including `[DOC]` and `[SHARED]`).
- If every returned finding is `[DOC]`/`[SHARED]`/NIT and there is no code work to do, set `sub_state: "ready"` instead and skip the rest of step 6.
- Refresh `updated_at`. Bake.

Only then start editing code. The user must see in the browser that the cycle returned and the implementer is now applying fixes.

The reviewer returned a list of findings. YOU (the main conversation) implement the fixes for CODE findings. Findings come in three categories:

**Code findings (you fix):**
- Fix every BLOCKER and MAJOR finding in the code.
- Fix MINOR findings unless they conflict with the current architecture.
- **Fix-batch write (gate – do this before rebuilding).** Once a batch of fixes is written and would survive the build, edit `{{plan_progress_path}}`: append one activity entry summarising the batch (`{role: "implementer", msg: "applied N fixes for cycle K: <one-line scope>"}`); for any Work/Files item the batch touched substantively, refresh its `note`; refresh `updated_at`. Bake. A batch is "the set of fixes you finished before the next rebuild" – do not let the agent silently fix 8 things in a row without surfacing it.
- Rebuild after each batch. Do NOT run tests — the reviewer will.

**Documentation findings (relay to user, do NOT fix):**
- Findings tagged `[DOC]` are documentation inconsistencies — the reviewer found that `{{plan_path}}` or another doc is stale.
- Relay `[DOC]` findings to the user verbatim. Do NOT edit the plan or related docs yourself.
- `[DOC]` findings are NOT blockers for the review gate.
- **Never report completion status as a finding.** Filter out any `[ ]`/`[x]` or phase `✅` bookkeeping before relaying.

**Overlay-improvement suggestions (collect, surface in the report):**
- Findings tagged `[SHARED]` are suggestions for the deployed coding-agent overlay itself – this `implement-phase.md`, `implement-fixes.md`, `review-iterate.md`, `.deployed-agents/conventions.md`, or a deployed skill.
- Accumulate every `[SHARED]` finding across review passes.
- Surface them verbatim in the final report (step 11). The user feeds them upstream to the source repo for the coding-agent overlay. Do NOT edit any overlay file yourself and do NOT write `[SHARED]` findings to a separate file.

### 7. Re-spawn the reviewer

Re-apply the step-5 pre-spawn write (increment `cycle`, set `sub_state: "inner-review"`, append the `"inner-review pass requested (cycle K)"` activity, bake) and spawn the `review-iterate` agent again with the same prompt. The reviewer audits the updated code and reports new findings.

Repeat steps 6–7 (you fix code, reviewer audits) until the reviewer returns zero BLOCKER, zero MAJOR, and zero non-`[DOC]` non-`[SHARED]` MINOR findings. `[DOC]` and `[SHARED]` findings do NOT block the review gate. NITs are acceptable but fix the trivial ones.

When the reviewer reports clean, edit `{{plan_progress_path}}`: set `sub_state: "ready"`; append activity `{role: "inner-review", msg: "clean on cycle K"}`; refresh `updated_at`. Bake. This is the signal to the outer reviewer (and the user) that the phase is implementer-clean.

**Repeated-feedback discipline**: if the reviewer reports the same finding across two cycles, address the exact `file:line` they cited before doing any other work. Don't add adjacent fixes — fix the specific thing first, rebuild, then re-spawn the reviewer.

**Cycle cap: 10 implementer cycles.** If you've done 10 rounds without approval, stop, set `sub_state: "blocked"` in `{{plan_progress_path}}` with an activity `{role: "implementer", msg: "cycle cap hit – escalating"}`, bake, and surface the situation to the user — don't grind indefinitely.

### 8. Surface `[SHARED]` suggestions (no file write)

`[SHARED]` findings stay in your accumulator only. Do NOT write them to a separate file, do NOT edit any overlay file (`.deployed-agents/`, `.claude/`, `.agents/`), and do NOT push them anywhere. They land in the final report in step 11 and the user feeds them upstream to the source repo for the coding-agent overlay. This is the only allowed handling – there is no separate suggestions file.

### 9. Commit locally

Stage exactly the files that changed for this phase. Use a focused message:

```
git add <files...>
git commit -m "Phase N: <Title>

<1-3 line summary of what shipped>"
```

Do not use `git add -A` (stray files sneak in). Do not use `--no-verify`. Do not push — local commit only; the user pushes when they're ready. **When implementing multiple phases in one run, commit each phase separately as you go; push only after every phase in the run has been committed.**

After the commit, edit `{{plan_progress_path}}`: append `{role: "implementer", msg: "committed <short-sha>"}`; refresh `updated_at`. Bake. Keep `sub_state: "ready"`; the outer reviewer (`review-implementation`) is what promotes the phase to `completed` and clears the progress block.

### 10. Update this command, implement-fixes, and review-iterate (mandatory last step before reporting)

Look back at the run that just finished. Edit the overlay files IN PLACE before you write your final report — this is what keeps the next run shorter than this one. Triggers:

- **Reviewer re-flagged the same finding across two+ cycles** → update `.claude/agents/review-iterate.md` to call it out as a first-pass check, OR update this command's expectations so the implementer catches it before the first review spawn.
- **Reviewer surfaced a NEW class of finding only in a later cycle** (e.g. abbreviations flagged piecemeal across passes) → update `review-iterate.md` to require an EXHAUSTIVE sweep of that class on the first pass.
- **Reviewer summarised "Review complete – clean" while also listing new MINORs** → tighten the "clean means clean" rule in `review-iterate.md`.
- **Reviewer misclassified a DOC-only item as MAJOR/BLOCKER** → tighten the DOC-vs-code-severity guidance in `review-iterate.md`.
- **A specific recurring fix, convention, or unclear step** → encode it here, in `implement-fixes.md`, or in `review-iterate.md`'s checklist as appropriate.

Keep `implement-phase.md` and `implement-fixes.md` in sync where they overlap (review loop, severity protocol, commit protocol). Targets are the local `.claude/` files (gitignored, persist for this project). If the source-of-truth templates outside the repo are accessible, mirror the changes there too so the next deploy carries them.

This step is **mandatory** before reporting. If nothing is genuinely worth changing, say so explicitly in the report ("no overlay updates this run") so it's a deliberate decision, not an oversight.

### 11. Report

Per phase: one terse line. `Phase N (<Title>) – implemented, build clean, tests <X>/<Y>, committed <short-sha>, rendered HTML: {{plan_html_path}}.`

At the end, **always output the complete consolidated lists of `[DOC]` and `[SHARED]` findings accumulated across all review passes**, re-listed verbatim under two clearly labelled sections. Even if you mentioned items during earlier steps, re-list every one – this consolidated list IS the user's feedback from the run.

- **`[DOC]` items** are suggestions for changes to `{{plan_path}}` (design sections, Files lists, `## Decisions`, etc.). The user applies them to the plan.
- **`[SHARED]` items** are suggestions for changes to the coding-agent overlay itself (`.deployed-agents/conventions.md`, `.claude/commands/`, `.claude/agents/review-iterate.md`, etc.). The user feeds them upstream to the source repo.

Implementer-side `BLOCKER`/`MAJOR`/`MINOR`/`NIT` findings are loop-internal – by the time the loop is clean, they have been fixed in code. They do NOT belong in the report. The user-facing feedback surface is `[DOC]` and `[SHARED]` only.

If you appended any `proposed_decisions` to `progress.json` during the run, note them in the report so the user knows there are pending decisions for the outer reviewer to apply or reject.

## Things you do NOT do

- Do not skip the reviewer. The inner loop has caught real bugs.
- Do not bundle multiple phases into one commit when implementing them sequentially. One phase, one commit (unless the user asked for a batch).
- Do not push. Local commits only.
- Do not edit phases other than the active one in the plan file.
- Do not silently downgrade a phase's scope to make it pass review. If the plan asks for X and X is genuinely problematic, stop and ask.
