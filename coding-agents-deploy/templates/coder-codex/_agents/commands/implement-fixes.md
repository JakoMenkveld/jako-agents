---
name: implement-fixes
description: Take a list of findings (may span multiple phases), implement the fixes, review with review-iterate, iterate until clean, then commit locally. With no findings given, falls back to the first in-progress phase in {{plan_path}} and implements its still-unfinished work.
---

# /implement-fixes

Take a user-provided list of findings, implement the fixes yourself, spawn the read-only `review-iterate` agent to audit, iterate until clean, then commit locally.

**Live progress overlay (mandatory, not optional).** Like `/implement-phase`, this command writes `{{plan_progress_path}}` at every meaningful transition – per-finding start, per fix-batch, per inner-review cycle, commit. **Progress writes are step gates, not commentary.** Skipping them strands the user's browser tab on stale state and reads as a stall. Bake after every write:

```
python .deployed-agents/plan-renderer/bake.py --plan {{plan_path}}
```

See **Live progress overlay** + **Implementer write checkpoints** in `.deployed-agents/conventions.md` for schema and timing.

Which phase block to touch: if the findings list points at a specific phase (`Phase N: …`), update that phase's block; if `$ARGUMENTS` was empty and the command fell back to the first in-progress phase, update that block. Phase blocks must already exist (created by `/implement-phase`); if not, create one with `sub_state: "applying-fixes"` (carrying a real ISO-8601 `started_at` and `updated_at`, not a midnight placeholder) and bake.

## Steps

### 0. First-run check

Before anything else, do the **First-run self-configuration** in `.deployed-agents/conventions.md`: if any `<add …>` / `Unknown stack` / generic-fallback deploy placeholders remain, fill them from the actual repo (this file's commands, `.claude/settings.json`, and the `review-iterate` agent), report a one-line summary, then continue. Skip once the placeholders are gone.

### 1. Parse the findings

The findings are in `$ARGUMENTS`. If they reference specific files, read those first. If they reference phases in `{{plan_path}}`, read the relevant phase sections.

**If `$ARGUMENTS` is empty** (no findings given), do not stop – fall back to the plan: select the first in-progress phase in `{{plan_path}}`, read its full section, and reconcile it against disk. Each unfinished task or missing/incomplete file the phase calls out becomes a synthetic finding; skip anything already implemented. Read status bookkeeping only as a scope signal – never edit it. Explicitly given findings always take precedence over this fallback.

List the findings to the user so they can confirm before you proceed, noting whether each was explicitly given or auto-derived (and from which phase).

### 1.5. Open-questions gate (hard stop)

Read the `## Open Questions` section of `{{plan_path}}`. If it contains any non-empty bullet (a line starting with `-` that has content), **stop immediately**. Do not write to the progress overlay, do not fetch, do not touch code. Open questions are user-owned and append-only; the implementer never edits them, but it also refuses to proceed while any are outstanding.

Surface every open question to the user verbatim, then ask them to clear `## Open Questions` before re-running the command, in one of two ways:

- **Resolve the question** by recording the answer in `## Decisions` and removing the bullet from `## Open Questions`; or
- **Defer the question** by moving the bullet from `## Open Questions` to `## Residual Risks` (acknowledging the risk is being carried into the fixes).

This is a plan-wide gate: any open question blocks any implementer-side work, including fix runs. An empty `## Open Questions` (the heading with no bullets) is the only acceptable state.

### 2. Fetch-first

`git fetch origin && git status --short --untracked-files=all`. Untracked files belong to someone – note them but don't revert them.

- **Origin ahead, no work in progress**: `git pull --rebase origin <current-branch>` and continue (the branch you are on; this overlay never assumes `main`).
- **Origin ahead, work in progress**: stop and surface the divergence to the user.
- **Dirty worktree with unrelated user changes**: do not revert user changes. Work around them. If they actively block the fixes, report a blocker.

### 3. Implement the fixes

Work through each finding systematically. Follow project conventions (see `.deployed-agents/conventions.md`). Do NOT exceed the scope of the findings – no opportunistic refactors.

**Per-finding progress gate (do this for every finding, no exceptions).** Before you start a finding, write `{{plan_progress_path}}` appending `{role: "implementer", msg: "starting <SEV> <file:line>: <one-line scope>"}` and refresh `updated_at`. Bake. When the finding is resolved on disk, write another activity entry summarising what changed (`{role: "implementer", msg: "resolved <SEV> <file:line>: <one-line outcome>"}`). Bake. If a Work or Files item the plan tracks is affected, also flip / refresh its state and `note` in the same write.

A whole sweep of fixes with no new activity entries on disk means the overlay is broken – the user sees no movement. Even if a fix takes ninety seconds, log it.

A judgment call worth the outer reviewer's attention (architectural pivot, deferred sub-task, scope reduction) goes into `proposed_decisions` in the same write – do not save these for the end.

**Apply every finding in full before you build or call the reviewer.** Finish the entire findings list – no partial passes, no building or spawning the reviewer with some findings still unaddressed. Before leaving this step, walk the findings list item by item and confirm each is actually resolved in the code. The build and the reviewer are gates on the *complete* fix set, not a progress check on a partial one – a partial pass just burns a build/review cycle.

Do NOT modify `{{plan_path}}` or related plan/data-model docs. The reviewer may report doc staleness as `[DOC]` findings – relay those to the user. The `## Decisions` section is free-form and live: if a fix reveals a decision that should be added or changed, you may *suggest* that edit (state the proposed Decisions wording in your report for the user/reviewer to apply) – but never edit the plan yourself.

### 4. Build

```bash
{{build_cmd}}
```

Reach this step only once every finding is applied (step 3 gate). Iterate build → fix until clean. Do NOT run tests – that's the reviewer's job.

**Pre-review self-sweep (before spawning the reviewer).** The reviewer's convergence-discipline rules forbid surfacing new instances of the same finding-class across multiple cycles, but the implementer can pre-empt entire sweep classes here:

- **Naming sweep.** Grep every file the fixes touched for single-letter callback params and accumulator pairs: `\.(find|filter|map|some|every)\(\([a-z]\)`, `\.(reduce|sort)\(\([a-z],\s*[a-z]\)`, plus the project's banned short-name list (`arr`, `obj`, `val`, `tmp`, `idx`, `cnt`, `cfg`, `opts`, `ctx`, `len`, `cur`, `buf`, `ret`, `dst`, `src`, `fn`, `cb`, `prev`).
- **Dead export sweep.** Grep the repo for every `module.exports` (or equivalent) key in new/changed modules. Drop or document any export with no consumer.
- **Bare config-literal sweep.** In every file the plan calls config-driven, grep for bare numeric literals (≥2 digits, excluding 0/1) and confirm each one comes from a constants module / a request-time argument / has a comment explaining why it cannot live in config.
- **Validator-rejection-test sweep.** If the fix touches a `validateX` / `assertValidX` pair (or any documented-failure-mode function), enumerate the rejection branches and confirm a test exercises each. Cover: non-plain-object input, wrong `type` discriminator, missing required field, unknown enum value, container field set to a non-object/non-array, and one rejection driven by a constructed-then-mutated object.
- **Cache-behavioural-branch sweep.** If the fix touches a cache with hit / miss / refresh / mtime-only-touch / external-input-invalidation branches, enumerate every distinct branch and confirm a test drives each.

### 5. Spawn the reviewer

**Pre-spawn write (gate – do this before the Agent tool call, not after).** Edit `{{plan_progress_path}}`: set `sub_state: "inner-review"`; on cycles ≥ 2 increment `cycle`; append activity `{role: "implementer", msg: "inner-review pass requested (cycle K)"}`; refresh `updated_at`. Bake. Only then spawn the agent. The user must see the cycle change in their browser before the reviewer goes silent for a few minutes.

Spawn the `review-iterate` agent (`.agents/agents/review-iterate.md`). Prompt:

> Independently verify whether each of the following findings is fully resolved in the code, that no regression was introduced, and that the implementation still satisfies `{{plan_path}}`: [paste the findings list from step 1 verbatim]. Do NOT assume any of them were addressed – check each against the actual code yourself. Report findings as BLOCKER / MAJOR / MINOR / NIT. Do NOT implement fixes – just report what's wrong.

Hand the reviewer the original findings list to verify against – not an account of what you did. Do NOT describe or summarize the changes you made; the reviewer judges each finding against the plan and the code from scratch.

### 6. Implement reviewer findings + re-spawn

**Post-review write (gate – do this before the first code edit in response to findings).** When the reviewer returns, edit `{{plan_progress_path}}` in a single write:
- Set `sub_state: "applying-fixes"`.
- Append one activity entry per non-trivial finding: `{role: "inner-review", msg: "finding[<SEV>] <file:line> <one-line summary>"}`. Skip pure NITs, keep everything else.
- If every returned finding is `[DOC]`/`[SHARED]`/NIT and there is no code work to do, set `sub_state: "ready"` instead and skip to step 7.
- Refresh `updated_at`. Bake.

Only then start editing code.

Same three-category protocol as `/implement-phase`:

- **Code findings**: you fix (BLOCKER/MAJOR always; MINOR unless they conflict with current architecture).
- **`[DOC]` findings**: relay to user, do not edit docs.
- **`[SHARED]` findings**: collect for the final user-facing report (step 9). Do NOT write them to a separate file or edit any overlay file (`.deployed-agents/`, `.claude/`, `.agents/`). The user feeds them upstream to the source repo for the coding-agent overlay.

**Fix-batch write (gate – do this before rebuilding).** Once a batch of fixes is on disk, edit `{{plan_progress_path}}`: append `{role: "implementer", msg: "applied N fixes for cycle K: <one-line scope>"}`; refresh notes on affected Work/Files items; refresh `updated_at`. Bake. Then rebuild.

Re-spawn the reviewer after each fix batch (re-apply the step-5 pre-spawn write: increment `cycle`, set `sub_state: "inner-review"`, append the cycle activity, bake). Iterate until clean (zero BLOCKER/MAJOR/non-`[DOC]`-non-`[SHARED]` MINOR). On the clean pass, edit `{{plan_progress_path}}`: set `sub_state: "ready"`; append `{role: "inner-review", msg: "clean on cycle K"}`; refresh `updated_at`. Bake.

**Repeated-feedback discipline**: if the reviewer reports the same finding across two cycles, address the exact `file:line` they cited before doing any other work.

**Cycle cap: 10 implementer cycles.** After 10 rounds without approval, stop, set `sub_state: "blocked"` in `{{plan_progress_path}}` with an activity `{role: "implementer", msg: "cycle cap hit – escalating"}`, bake, and surface the situation.

### 7. Commit

```bash
git add <files...>
git commit -m "Apply fixes: <short summary>"
```

No `git add -A`, no `--no-verify`. Do not push.

After the commit, edit `{{plan_progress_path}}`: append `{role: "implementer", msg: "committed <short-sha>"}`; refresh `updated_at`. Bake. Leave `sub_state: "ready"` – the outer reviewer (`review-implementation`) is what promotes the phase to `completed` and clears the progress block.

### 8. Update this command, implement-phase, and review-iterate (mandatory last step before reporting)

Look back at the run that just finished. Edit the overlay files IN PLACE before you write your final report – this is what keeps the next run shorter than this one. Triggers:

- **Reviewer re-flagged the same finding across two+ cycles** → update `.agents/agents/review-iterate.md` to call it out as a first-pass check, OR update this command's expectations so the implementer catches it before the first review spawn.
- **Reviewer surfaced a NEW class of finding only in a later cycle** (e.g. abbreviations flagged piecemeal across passes) → update `review-iterate.md` to require an EXHAUSTIVE sweep of that class on the first pass.
- **Reviewer summarised "Review complete – clean" while also listing new MINORs** → tighten the "clean means clean" rule in `review-iterate.md`.
- **Reviewer misclassified a DOC-only item as MAJOR/BLOCKER** → tighten the DOC-vs-code-severity guidance in `review-iterate.md`.
- **A specific recurring fix, convention, or unclear step** → encode it here, in `implement-phase.md`, or in `review-iterate.md`'s checklist as appropriate.

Keep `implement-fixes.md` and `implement-phase.md` in sync where they overlap (review loop, severity protocol, commit protocol). Targets are the local `.agents/` files (gitignored, persist for this project). If the source-of-truth templates outside the repo are accessible, mirror the changes there too so the next deploy carries them.

This step is **mandatory** before reporting. If nothing is genuinely worth changing, say so explicitly in the report ("no overlay updates this run") so it's a deliberate decision, not an oversight.

### 9. Report

One-line summary, plus the complete consolidated lists of `[DOC]` and `[SHARED]` findings accumulated across all review passes – re-listed verbatim under two clearly labelled sections. This consolidated list IS the user's feedback from the run.

- **`[DOC]` items** are suggestions for changes to `{{plan_path}}`. The user applies them to the plan.
- **`[SHARED]` items** are suggestions for changes to the coding-agent overlay itself (`.deployed-agents/conventions.md`, `.agents/commands/`, `.agents/agents/review-iterate.md`, etc.). The user feeds them upstream to the source repo.

Implementer-side `BLOCKER`/`MAJOR`/`MINOR`/`NIT` findings are loop-internal – they have been fixed in code by the time the loop is clean and do NOT belong in the report. The user-facing feedback surface is `[DOC]` and `[SHARED]` only.

Include the rendered HTML location (`{{plan_html_path}}`) and any `proposed_decisions` you appended to `progress.json` during the run.
