---
description: Take a list of findings (may span multiple phases), implement the fixes, review with review-iterate, iterate until clean, then commit locally. With no findings given, falls back to the first in-progress phase in {{plan_path}} and implements its still-unfinished work.
aliases: [fixes, ifix]
---

# /implement-fixes

Take a user-provided list of findings, implement the fixes yourself, spawn the read-only `review-iterate` agent to audit, iterate until clean, then commit locally.

**Live progress overlay.** Like `/implement-phase`, this command writes `{{plan_path}}.progress.json` and bakes after every write so the user can monitor progress in a browser. See **Live progress overlay** + **Implementer write checkpoints** in `.deployed-agents/conventions.md` for schema and timing. Bake command:

```
python .deployed-agents/plan-renderer/bake.py --plan {{plan_path}}
```

Which phase block to touch: if the findings list points at a specific phase (`Phase N: …`), update that phase's block; if `$ARGUMENTS` was empty and the command fell back to the first in-progress phase, update that block. Phase blocks must already exist (created by `/implement-phase`); if not, create one with `sub_state: "applying-fixes"` and bake.

## Steps

### 0. First-run check

Before anything else, do the **First-run self-configuration** in `.deployed-agents/conventions.md`: if any `<add …>` / `Unknown stack` / generic-fallback deploy placeholders remain, fill them from the actual repo (this file's commands, `.claude/settings.json`, and the `review-iterate` agent), report a one-line summary, then continue. Skip once the placeholders are gone.

### 1. Parse the findings

The findings are in `$ARGUMENTS`. If they reference specific files, read those first. If they reference phases in `{{plan_path}}`, read the relevant phase sections.

**If `$ARGUMENTS` is empty** (no findings given), do not stop — fall back to the plan: select the first in-progress phase in `{{plan_path}}`, read its full section, and reconcile it against disk. Each unfinished task or missing/incomplete file the phase calls out becomes a synthetic finding; skip anything already implemented. Read status bookkeeping only as a scope signal — never edit it. Explicitly given findings always take precedence over this fallback.

List the findings to the user so they can confirm before you proceed, noting whether each was explicitly given or auto-derived (and from which phase).

### 2. Fetch-first

`git fetch origin && git status --short --untracked-files=all`. Untracked files belong to someone — note them but don't revert them.

- **Origin ahead, no work in progress**: `git pull --rebase origin <current-branch>` and continue (the branch you are on; this overlay never assumes `main`).
- **Origin ahead, work in progress**: stop and surface the divergence to the user.
- **Dirty worktree with unrelated user changes**: do not revert user changes. Work around them. If they actively block the fixes, report a blocker.

### 3. Implement the fixes

Work through each finding systematically. Follow project conventions (see `.deployed-agents/conventions.md`). Do NOT exceed the scope of the findings — no opportunistic refactors.

**Apply every finding in full before you build or call the reviewer.** Finish the entire findings list — no partial passes, no building or spawning the reviewer with some findings still unaddressed. Before leaving this step, walk the findings list item by item and confirm each is actually resolved in the code. The build and the reviewer are gates on the *complete* fix set, not a progress check on a partial one — a partial pass just burns a build/review cycle.

Do NOT modify `{{plan_path}}` or related plan/data-model docs. The reviewer may report doc staleness as `[DOC]` findings — relay those to the user. The `## Decisions` section is free-form and live: if a fix reveals a decision that should be added or changed, you may *suggest* that edit (state the proposed Decisions wording in your report for the user/reviewer to apply) — but never edit the plan yourself.

### 4. Build

```bash
{{build_cmd}}
```

Reach this step only once every finding is applied (step 3 gate). Iterate build → fix until clean. Do NOT run tests — that's the reviewer's job.

**Pre-review self-sweep (before spawning the reviewer).** The reviewer's convergence-discipline rules forbid surfacing new instances of the same finding-class across multiple cycles, but the implementer can pre-empt entire sweep classes here:

- **Naming sweep.** Grep every file the fixes touched for single-letter callback params and accumulator pairs: `\.(find|filter|map|some|every)\(\([a-z]\)`, `\.(reduce|sort)\(\([a-z],\s*[a-z]\)`, plus the project's banned short-name list (`arr`, `obj`, `val`, `tmp`, `idx`, `cnt`, `cfg`, `opts`, `ctx`, `len`, `cur`, `buf`, `ret`, `dst`, `src`, `fn`, `cb`, `prev`).
- **Dead export sweep.** Grep the repo for every `module.exports` (or equivalent) key in new/changed modules. Drop or document any export with no consumer.
- **Bare config-literal sweep.** In every file the plan calls config-driven, grep for bare numeric literals (≥2 digits, excluding 0/1) and confirm each one comes from a constants module / a request-time argument / has a comment explaining why it cannot live in config.

### 5. Spawn the reviewer

Before spawning, update the target phase's block in `progress.json`: set `sub_state: "inner-review"`; on cycles ≥ 2 increment `cycle`; append activity `"inner-review pass requested (cycle K)"`. Bake.

Spawn the `review-iterate` agent (`.claude/agents/review-iterate.md`). Prompt:

> Independently verify whether each of the following findings is fully resolved in the code, that no regression was introduced, and that the implementation still satisfies `{{plan_path}}`: [paste the findings list from step 1 verbatim]. Do NOT assume any of them were addressed — check each against the actual code yourself. Report findings as BLOCKER / MAJOR / MINOR / NIT. Do NOT implement fixes — just report what's wrong.

Hand the reviewer the original findings list to verify against — not an account of what you did. Do NOT describe or summarize the changes you made; the reviewer judges each finding against the plan and the code from scratch.

### 6. Implement reviewer findings + re-spawn

For each non-trivial finding the reviewer returned, append an activity entry to `progress.json` with `role: "inner-review"` and a short `msg` like `finding[<SEV>] <file:line> <summary>`. Set `sub_state: "applying-fixes"`. Bake.

Same three-category protocol as `/implement-phase`:

- **Code findings**: you fix (BLOCKER/MAJOR always; MINOR unless they conflict with current architecture).
- **`[DOC]` findings**: relay to user, do not edit docs.
- **`[SHARED]` findings**: collect for the shared-library suggestions file.

Re-spawn the reviewer after each fix batch. Iterate until clean (zero BLOCKER/MAJOR/non-`[DOC]`-non-`[SHARED]` MINOR). On the clean pass, set `sub_state: "ready"` and bake.

**Repeated-feedback discipline**: if the reviewer reports the same finding across two cycles, address the exact `file:line` they cited before doing any other work.

**Cycle cap: 10 implementer cycles.** After 10 rounds without approval, stop and surface the situation.

### 7. Commit

```bash
git add <files...>
git commit -m "Apply fixes: <short summary>"
```

No `git add -A`, no `--no-verify`. Do not push.

After the commit, append activity `"committed <short-sha>"` to `progress.json` and bake. Leave `sub_state: "ready"` – the outer reviewer (`review-implementation`) is what promotes the phase to `completed` and clears the progress block.

### 8. Update this command, implement-phase, and review-iterate (mandatory last step before reporting)

Look back at the run that just finished. Edit the overlay files IN PLACE before you write your final report — this is what keeps the next run shorter than this one. Triggers:

- **Reviewer re-flagged the same finding across two+ cycles** → update `.claude/agents/review-iterate.md` to call it out as a first-pass check, OR update this command's expectations so the implementer catches it before the first review spawn.
- **Reviewer surfaced a NEW class of finding only in a later cycle** (e.g. abbreviations flagged piecemeal across passes) → update `review-iterate.md` to require an EXHAUSTIVE sweep of that class on the first pass.
- **Reviewer summarised "Review complete – clean" while also listing new MINORs** → tighten the "clean means clean" rule in `review-iterate.md`.
- **Reviewer misclassified a DOC-only item as MAJOR/BLOCKER** → tighten the DOC-vs-code-severity guidance in `review-iterate.md`.
- **A specific recurring fix, convention, or unclear step** → encode it here, in `implement-phase.md`, or in `review-iterate.md`'s checklist as appropriate.

Keep `implement-fixes.md` and `implement-phase.md` in sync where they overlap (review loop, severity protocol, commit protocol). Targets are the local `.claude/` files (gitignored, persist for this project). If the source-of-truth templates outside the repo are accessible, mirror the changes there too so the next deploy carries them.

This step is **mandatory** before reporting. If nothing is genuinely worth changing, say so explicitly in the report ("no overlay updates this run") so it's a deliberate decision, not an oversight.

### 9. Report

One-line summary plus the consolidated list of `[DOC]` findings collected across all review passes, plus any `[SHARED]` findings written. Include the rendered HTML location (`{{plan_path}}.html`) and any `proposed_decisions` you appended to `progress.json` during the run.
