---
name: archive-plan
description: Archive the completed implementation plan at {{plan_path}} into a dated file under an archive/ subdirectory and start a fresh, task-free plan that carries forward only still-relevant context (summary, Automation Contract, still-relevant Decisions, still-open Open Questions and Residual Risks). Refuses to run while the plan still has outstanding tasks and asks the user how to proceed. Reviewer lane only. Use when invoked as `/archive-plan`.
---

# /archive-plan

Archive the finished implementation plan at `{{plan_path}}` and replace it with a clean, **task-free** plan that keeps only the durable context. This is a reviewer-lane operation — the coder lane never archives plans.

The flow is: **verify nothing is outstanding → move the old plan into `archive/` with a dated name → write a fresh skeleton plan carrying forward still-relevant context → commit locally.**

## Hard precondition: no outstanding tasks

`archive-plan` only proceeds when **every** task in the plan is complete. Before touching anything, scan the plan's full status surface, interpreting it in the plan's **own** legend (a `Legend:` line, a status-table legend, or Mermaid `classDef` names like `done`/`inProgress`/`pending`/`blocked`; otherwise the default is `✅` done / `⚠️` partial / unmarked = not done):

- Any `## Phase N` heading or per-phase `Status:` line not marked done.
- Any `### Work` or `### Acceptance Criteria` bullet not marked done.
- Any unchecked checkbox (`- [ ]`).
- Any `## Phase Status` table row whose Status is not done.
- Any `## Phase Flow` Mermaid node whose label icon or `class … <className>` line is not the done class.
- Any in-progress / pending / blocked / partial marker anywhere (`🟡`, `⬜`, `🔴`, `⚠️`, …).
- Any non-empty phase block in `{{plan_path}}.progress.json` (the implementer-owned live overlay). A populated block means an implementer is mid-phase and review-implementation has not yet promoted it to completed – there is outstanding work even if no plan marker reflects it yet.

Placeholder skeleton bullets written in parentheses (e.g. `- (List work items for this phase.)`) are **not** outstanding tasks — they mean the phase was never populated.

**If anything is outstanding, STOP. Do not move, rewrite, or delete anything.** Report the outstanding items grouped by phase, then ask the user how to proceed with one bundled question (AskUserQuestion when available). Offer these options:

1. **Finish first (recommended)** — cancel archiving. The user completes the work (or runs `/review-implementation` to truthfully re-mark already-finished work), then re-invokes `/archive-plan`.
2. **Archive anyway, carry the unfinished work forward as context** — proceed with archiving, but summarize each unfinished item into a narrative **`## Carried-Forward Context`** section in the new plan. These are notes, **not** tasks: no `### Work` bullets, no checkboxes, no phases. The archived copy keeps the original unfinished tasks intact.
3. **Cancel** — do nothing.

Do not archive over outstanding tasks without an explicit choice of option 2. Never guess.

If the plan is an untouched skeleton (only placeholder bullets, no completed or outstanding work), say so and ask whether to archive anyway — there is nothing meaningful to preserve, only a date-stamped empty skeleton.

## Steps (only after the precondition passes or option 2 is chosen)

### 1. Locate the plan

`{{plan_path}}` is the plan. If no file exists there, report that there is nothing to archive and stop.

Read the whole plan. Note its `# <Title>`, summary/background paragraphs, `## Automation Contract`, `## Definition of Done`, the `## Decisions` content, the still-open `## Open Questions` entries, the still-relevant `## Residual Risks`, and any durable architecture/background narrative that remains true for future work.

### 2. Archive the current plan

- Archive directory: an `archive/` subdirectory beside the plan (e.g. for `docs/implementation-plan.md` → `docs/archive/`). Create it if missing.
- Dated filename: `<plan-stem>-<YYYYMMDD>.md` (today's date). If that file already exists, append `-<HHMMSS>` so nothing is overwritten.
- Move with `git mv` when the plan is tracked (history follows the rename); otherwise a plain move. **Copy the content byte-for-byte — never edit the archived copy**, including any unfinished tasks under option 2.
- If `{{plan_path}}.progress.json` exists, move it alongside with the same dated stem (`<plan-stem>-<YYYYMMDD>.progress.json`). Use `git mv` when tracked. If the file is effectively empty (no `phases` entries), delete it instead of archiving.
- Likewise the rendered HTML `{{plan_path}}.html` (if present) – move alongside as `<plan-stem>-<YYYYMMDD>.html`. It is the visual snapshot of the moment the plan was archived.

### 3. Write the fresh, task-free plan

Create a new `{{plan_path}}` in the canonical structure (the same layout `/review-and-fix` and `/implement-phase` expect), but with **no tasks** — every phase is an empty placeholder:

- `# <same title>` — keep the prior `# <Project Name> Implementation Plan` title.
- **Summary paragraph** — carry forward the still-relevant summary/background, trimmed to what is still true for future work. End it with: `Archived predecessor: archive/<dated file>. Created: <YYYY-MM-DD>.`
- `## Phase Flow` — minimal Mermaid: a single `flowchart TD` with `P0[Phase 0: Initial implementation]` and no status markers.
- `## Recommended Execution Order` — `1. Phase 0 – Initial implementation`.
- `## Automation Contract` — **copied verbatim** from the archived plan (build/test/CI assumptions are durable).
- `## Definition of Done` — placeholder bullet `- (List the exit criteria for the whole plan.)`; copy forward only individual DoD lines that are durable invariants rather than old-scope exit criteria.
- `## Phase 0: Initial implementation` with `### Work` and `### Acceptance Criteria`, each holding only the parenthetical placeholder bullet (`- (List work items for this phase.)` / `- (List acceptance criteria for this phase.)`). No real tasks.
- `## Files to Create or Modify by Phase` → `### Phase 0` → `- (List files this phase creates or modifies.)`. If the archived plan used the legacy heading `## Files to Create by Phase`, the fresh plan uses the new name.
- `## Test Plan` → `### Phase 0` → `- (List tests this phase ships or unblocks.)`.
- `## Decisions` – carry forward the still-relevant decisions, reworded or condensed as needed (it is free-form, not a fixed numbered list); drop what the archived work made moot. Place it immediately before `## Open Questions`. An empty section, or a note that there are none, is acceptable – never invent decisions the user did not make.
- `## Open Questions` – copy forward, verbatim and renumbered from 1, only the questions that are still genuinely open. Drop ones the archived work resolved. An empty section, or a note such as `None.`, is acceptable – never invent entries.
- `## Residual Risks` — copy forward only the risks still relevant; drop risks the archived work closed; reword any whose blast radius changed.
- `## Carried-Forward Context` — **only** when option 2 was chosen (or there is durable architectural context worth keeping). Narrative bullets summarizing unfinished/relevant context for whoever plans the next cycle. Never tasks, checkboxes, or phases.

No status markers anywhere in the new plan – it starts clean. Do not create a new `progress.json` – the fresh plan has no in-flight work.

After writing the fresh plan, run the bake command once to refresh the rendered HTML beside it:

```
python .deployed-agents/plan-renderer/bake.py --plan {{plan_path}}
```

### 4. Commit locally

Stage exactly the rename(s) and the new plan: the moved plan + any moved `progress.json` / `.html` snapshot under `archive/`, plus the fresh `{{plan_path}}`. The fresh `{{plan_path}}.html` is regenerable (the agent rebakes on every plan touch); leave it untracked. Nothing else:

```
git add <archive/dated-file(s)> {{plan_path}}
git commit -m "Archive implementation plan (<YYYYMMDD>) and start fresh plan"
```

No `git add -A`, no `--no-verify`, no co-author trailer. **Do not push** — local commit only; the user pushes when ready. Committing the move keeps the rename tracked so the repo is never left mid-rename.

### 5. Report

One short paragraph: the archived path, the new plan path, what was carried forward (Automation Contract, N still-open questions, M residual risks, and `## Carried-Forward Context` if written), and that it was committed locally and not pushed. If you stopped on the outstanding-tasks precondition instead, report the outstanding items by phase and the question you asked — and make no file changes.

## Things you do NOT do

- Do not archive while any task is outstanding unless the user explicitly chooses option 2.
- Do not edit the archived copy — it is the historical record.
- Do not carry tasks, checkboxes, or status markers into the new plan. The new plan has no tasks.
- Do not invent Decisions, Open Questions, or Residual Risks; only carry forward what was already there and still applies. An empty `## Decisions` or `## Open Questions` in the fresh plan is correct when nothing carries forward.
- Do not push. Local commit only.
- Do not run in the coder lane — this is a reviewer-lane skill.
