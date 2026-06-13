---
description: Archive the completed implementation plan at {{plan_path}} and every related spec document into dated files under an archive/ subdirectory, reset {{plan_path}} to a blank skeleton, and delete {{plan_html_path}}. Refuses to run while the plan still has outstanding tasks and asks the user how to proceed. Reviewer lane only.
---

# /archive-plan

Archive the finished implementation plan at `{{plan_path}}`, archive every related feature/spec document with it, replace the plan with a clean, empty skeleton, and delete `{{plan_html_path}}`. This is a reviewer-lane operation – the coder lane never archives plans.

The flow is: **verify nothing is outstanding → move the old plan and every related spec into `archive/` with dated names → write a fresh empty skeleton plan → delete the rendered HTML → commit locally.**

## Hard precondition: no outstanding tasks

`archive-plan` only proceeds when **every** task in the plan is complete. Before touching anything, scan the plan's full status surface, interpreting it in the plan's **own** legend (a `Legend:` line, a status-table legend, or Mermaid `classDef` names like `done`/`inProgress`/`pending`/`blocked`; otherwise the default is `✅` done / `⚠️` partial / unmarked = not done):

- Any `## Phase N` heading or per-phase `Status:` line not marked done.
- Any `### Work` or `### Acceptance Criteria` bullet not marked done.
- Any unchecked checkbox (`- [ ]`).
- Any `## Phase Status` table row whose Status is not done.
- Any `## Phase Flow` Mermaid node whose label icon or `class … <className>` line is not the done class.
- Any in-progress / pending / blocked / partial marker anywhere (`🟡`, `⬜`, `🔴`, `⚠️`, …).
- Any non-empty phase block in `{{plan_progress_path}}` (the implementer-owned live overlay). A populated block means an implementer is mid-phase and review-implementation has not yet promoted it to completed – there is outstanding work even if no plan marker reflects it yet.

Placeholder skeleton bullets written in parentheses (e.g. `- (List work items for this phase.)`) are **not** outstanding tasks – they mean the phase was never populated.

**If anything is outstanding, STOP. Do not move, rewrite, or delete anything.** Report the outstanding items grouped by phase, then ask the user how to proceed with one bundled question (AskUserQuestion when available). Offer these options:

1. **Finish first (recommended)** – cancel archiving. The user completes the work (or runs `/review-implementation` to truthfully re-mark already-finished work), then re-invokes `/archive-plan`.
2. **Archive anyway, with no carry-forward** – proceed with archiving and reset the new plan to the same blank skeleton. The archived copy keeps the original unfinished tasks intact.
3. **Cancel** – do nothing.

Do not archive over outstanding tasks without an explicit choice of option 2. Never guess. Even when option 2 is chosen, do not carry unfinished tasks or context into the fresh plan.

If the plan is an untouched skeleton (only placeholder bullets, no completed or outstanding work), say so and ask whether to archive anyway – there is nothing meaningful to preserve, only a date-stamped empty skeleton.

## Steps (only after the precondition passes or option 2 is chosen)

### 1. Locate the plan

`{{plan_path}}` is the plan. If no file exists there, report that there is nothing to archive and stop.

Read the whole plan. Note its `# <Title>` and every related feature/spec document referenced by the plan or clearly associated with it in the same docs directory. Related spec archiving is mandatory: scan the whole plan for local Markdown links and also look in the docs directory for an obvious paired spec. Archive every related spec you find. If the plan references a local spec path that should exist but does not, stop and report the missing file instead of silently skipping it.

### 2. Archive the current plan and related specs

- Archive directory: an `archive/` subdirectory beside the plan (e.g. for `docs/implementation-plan.md` → `docs/archive/`). Create it if missing.
- Dated filename: `<plan-stem>-<YYYYMMDD>.md` (today's date). If that file already exists, append `-<HHMMSS>` so nothing is overwritten.
- Move with `git mv` when the plan is tracked (history follows the rename); otherwise a plain move. **Copy the content byte-for-byte – never edit the archived copy**, including any unfinished tasks under option 2.
- If `{{plan_progress_path}}` exists, move it alongside with the same dated stem (`<plan-stem>-<YYYYMMDD>.progress.json`). Use `git mv` when tracked. If the file is effectively empty (no `phases` entries), delete it instead of archiving.
- Delete the rendered HTML `{{plan_html_path}}` if present. Use `git rm` when tracked; otherwise remove the untracked file. Do not archive or recreate it during this command.
- Move every related feature/spec document into the same archive directory as `<spec-stem>-<YYYYMMDD>.md`. If that file already exists, append `-<HHMMSS>` so nothing is overwritten. Use `git mv` when tracked. Do not edit the archived plan or spec just to repair historical links.

### 3. Write the blank skeleton plan

Create a new `{{plan_path}}` in the canonical structure (the same layout `/review-and-fix` and `/implement-phase` expect), but keep it as an empty skeleton only:

- `# <same title>` – keep the prior `# <Project Name> Implementation Plan` title.
- `## Phase Flow` – minimal Mermaid: a single `flowchart TD` with `P0[Phase 0: Initial implementation]` and no status markers.
- `## Recommended Execution Order` – `1. Phase 0 – Initial implementation`.
- `## Automation Contract` – placeholder bullet `- (Define automation contract.)`.
- `## Definition of Done` – placeholder bullet `- (List the exit criteria for the whole plan.)`.
- `## Phase 0: Initial implementation` with `### Work` and `### Acceptance Criteria`, each holding only the parenthetical placeholder bullet (`- (List work items for this phase.)` / `- (List acceptance criteria for this phase.)`). No real tasks.
- `## Files to Create or Modify by Phase` → `### Phase 0` → `- (List files this phase creates or modifies.)`. If the archived plan used the legacy heading `## Files to Create by Phase`, the fresh plan uses the new name.
- `## Test Plan` → `### Phase 0` → `- (List tests this phase ships or unblocks.)`.
- `## Decisions` → `None.`
- `## Open Questions` → `None.`
- `## Residual Risks` → `None.`

Do not carry forward summaries, Decisions, Open Questions, Residual Risks, architectural context, implementation history, or spec facts unless the user explicitly asks for that content in the new plan.

No status markers anywhere in the new plan – it starts clean. Do not create a new `progress.json` and do not bake a fresh HTML file – the fresh plan has no in-flight work and `{{plan_html_path}}` must be absent after archiving.

### 4. Commit locally

Stage exactly the rename(s), deletions, and the new plan: the moved plan, every moved related spec, any moved or deleted `progress.json`, the deletion of `{{plan_html_path}}` if it was tracked, plus the fresh `{{plan_path}}`. Nothing else:

```
git add <archive/dated-file(s)> {{plan_path}}
git commit -m "Archive implementation plan (<YYYYMMDD>) and start fresh plan"
```

No `git add -A`, no `--no-verify`, no co-author trailer. **Do not push** – local commit only; the user pushes when ready. Committing the move keeps the rename tracked so the repo is never left mid-rename.

### 5. Report

One short paragraph: the archived path(s) (plan and any specs), the blank-skeleton path, and that it was committed locally and not pushed. If you stopped on the outstanding-tasks precondition instead, report the outstanding items by phase and the question you asked – and make no file changes.

## Things you do NOT do

- Do not archive while any task is outstanding unless the user explicitly chooses option 2.
- Do not edit the archived copy – it is the historical record.
- Do not carry any content forward into the blank skeleton – it must be clean and template-only.
- Do not run the bake command or create `{{plan_html_path}}` after archiving.
- Do not push. Local commit only.
- Do not run in the coder lane – this is a reviewer-lane skill.
