---
description: Review one or more {{project_name}} implementation phases against {{plan_path}} and the current codebase, truthfully update the whole status surface (phase headings, Work/Acceptance bullets, task checkboxes, the Phase Status table, per-phase Status lines, and the Phase Flow Mermaid graph – node labels and class lines), commit the review locally, and report remaining actionable work. Arguments are interpreted as phase selectors and/or plan-update suggestions; with no explicit phase it auto-detects and reviews the in-progress phase(s).
---

# Review Implementation

Review one or more {{project_name}} implementation phases end to end, update `{{plan_path}}` truthfully with status markers, commit the review locally, and report remaining actionable work.

**Live progress overlay.** Each implementer command (`/implement-phase`, `/implement-fixes`) writes `{{plan_path}}.progress.json` during a phase. This skill reads that overlay (especially `phases[N].activity` and `phases[N].proposed_decisions`) for context, then clears the phase block when promoting the phase to `completed` – the plan's lifecycle marker is authoritative from that point. After every write to `{{plan_path}}` *or* `{{plan_path}}.progress.json`, run:

```
python .deployed-agents/plan-renderer/bake.py --plan {{plan_path}}
```

See **Live progress overlay** in `.deployed-agents/conventions.md` for the schema.

## Plan Write Policy

`{{plan_path}}` is writable for THIS command, but the scope is narrow.

**Allowed edits – the full status surface of every reviewed phase:**
- Status markers on the phase heading, `### Work` bullets, `### Acceptance Criteria` bullets, and `## Recommended Execution Order` entries.
- The `## Phase Flow` Mermaid graph – **both** the status icon embedded in the node label (e.g. `P3[Phase 3: … ⬜]` → `… ✅`) **and** the matching classification line (e.g. `class P3 pending` → `class P3 done`). Keep the node label, the `class` line, and the diagram's own `classDef` names consistent with each other. Also update edge labels.
- A `## Phase Status` table (or any phase status/summary table): the Status cell of each reviewed phase's row.
- A per-phase `Status:` line directly beneath the phase heading.
- Task/checklist checkboxes (`- [ ]` → `- [x]`) and `## Files to Create or Modify` / file-inventory bullets for the reviewed phase – flip an individual item only when that specific item is verified complete in code.
- Concise partial-reason notes inside the bracketed marker: `⚠️ [partial: SetMeasures fixed but tests pending]`.
- `## Decisions`: **free-form and live.** Add, edit, reword, reorganize, or remove entries so the section accurately records the decisions the user made, confirmed, ratified, or revised during design or implementation. It is NOT append-only and NOT a fixed numbered list. Never fabricate a decision the user did not make; when unsure whether something is settled, surface it instead of writing it. An empty `## Decisions`, or one noting there are none, is fine and never flagged.
- `## Open Questions`: **append-only**. Add new questions to the bottom of the numbered list. Do NOT edit, renumber, resolve, mark, remove, or move existing entries – the user resolves Open Questions manually. An empty `## Open Questions`, or one whose only content is a note such as `None.` / `No open questions.`, is fully acceptable: it is never a finding and never blocks phase completion. Append only a genuine new question.
- `## Residual Risks`: add new items raised during the review, remove risks resolved by shipped code, re-word risks whose blast radius changed.
- `{{plan_path}}.progress.json`: clear (delete) `phases[N]` for any phase you promoted to `completed` in this review. The plan's lifecycle marker is now the authoritative record. If `proposed_decisions` were carried in that block, decide on them first (fold any you accept into `## Decisions`, drop the rest) and then clear the whole block. After any write to the overlay, also bake.

**Use the plan's own status vocabulary.** If the plan declares a legend – a `Legend:` line, a status-table legend, or Mermaid `classDef` names like `done`/`inProgress`/`pending`/`blocked` – match it exactly (icons *and* class names; e.g. `🟡 in-progress` and `class P1 inProgress`, not `⚠️`). Only when the plan declares no vocabulary, default to `✅` complete / `⚠️ [partial: reason]` / unmarked. Every surface above must end the review agreeing with every other surface and with the code.

**Disallowed edits:**
- Adding new phase sections, renaming phases, rewriting acceptance-criteria text, moving text between phases, or changing any non-marker plan content.
- Editing, renumbering, resolving, or removing any existing `## Open Questions` entry, or flagging an empty `## Open Questions` / `## Decisions` (or a "none" note) as a defect. (`## Decisions` itself is free-form and editable – see the allowed edits.)

Status icons:
- `✅` – complete.
- `⚠️` or `⚠` – partially complete (always include a short reason in brackets).
- (no icon) – not started or not yet reviewed.

Never invent acceptance criteria, never silently delete plan text, and never leave a phase in a state that contradicts the code.

## Inputs

`$ARGUMENTS` is free-form. Treat every token as **either** a phase selector **or** a plan-update suggestion – a single invocation may carry both at once. Split the arguments into the two kinds:

- **Phase selectors** – anything that denotes phase numbers: a single number (`phase 1`, `1`), an inclusive range (`2 to 5`, `2-5`), or comma/word lists (`2, 3, 4 and 5`). Normalize to a sorted, de-duplicated list and review in ascending order unless asked otherwise.
- **Plan-update suggestions** – any remaining prose (e.g. "the retry logic moved to the worker", "Phase 4 now depends on Phase 6"). Carry these into the review as hypotheses to verify against the code, and into the status update within the Plan Write Policy. A suggestion never overrides that policy: if acting on it would require a disallowed edit (rewriting acceptance criteria, restructuring phases, editing/resolving an Open Question), apply only what the policy allows and surface the rest to the user instead of performing it.

**Phase selection:**
- If the arguments contain explicit phase selectors, review exactly those phases.
- If the arguments contain **no** explicit phase selectors – even when they do carry plan-update suggestions – do NOT ask. Auto-detect instead: review every phase the plan currently marks in-progress (`⚠️`/`⚠` on the heading, the per-phase `Status:` line, the `## Phase Status` table cell, or the plan's own in-progress legend such as `class Pn inProgress`), in ascending order.
- If no phase is explicitly given and none is marked in-progress, fall back to the lowest-numbered phase that has implementation on disk but is not yet marked complete. If even that is ambiguous, ask once.

Plan-update suggestions apply to whichever phases end up selected, including auto-detected in-progress phases.

Repository root is the current workspace. Plan file: `{{plan_path}}`.

## Review severity

- `BLOCKER` – code does not compile, target phase cannot work, data corruption risk, security regression, or acceptance criteria are clearly unmet.
- `MAJOR` – important behavior, validation, test, tool wiring, or documentation contract is missing or wrong.
- `MINOR` – edge case, maintainability issue, incomplete docs, or narrow test gap that does not invalidate the phase.
- `NIT` – style or local cleanup with no material behavioral risk.
- `DOC` – documentation or plan drift only. Code is acceptable but docs are stale.

When supporting docs are stale but the implementation is correct, treat it as a `DOC` finding and update the relevant doc instead of asking for a code change.

## Workflow

0. **First-run check.** Before anything else, do the **First-run self-configuration** in `.deployed-agents/conventions.md`: if any `<add …>` / `Unknown stack` / generic-fallback deploy placeholders remain, fill them from the actual repo (`.deployed-agents/conventions.md`, `.claude/settings.json`, the `review-iterate` agent), report a one-line summary, then continue. Skip once the placeholders are gone.

1. **Survey state – including untracked files and the live overlay.** Run `git status --short --untracked-files=all`, `git diff --check`, and `git ls-files --others --exclude-standard`. **Untracked files are part of the review surface** – do not approve if relevant implementation files are untracked and you didn't inspect them. Read the selected phase(s) in `{{plan_path}}`, including each phase's `### Work` and `### Acceptance Criteria`, plus surrounding `## Phase Flow`, `## Recommended Execution Order`, `## Open Questions`, and `## Residual Risks`. Read `{{plan_path}}.progress.json` if present – its `activity` log shows what the implementer worked through, and `proposed_decisions` is its channel for surfacing judgment calls for you to apply or reject. Read supporting docs in the repo when they overlap the reviewed phases.

2. **Inspect the diff.** If the phase work is committed, use `git diff --stat HEAD~1..HEAD`; otherwise `git diff --stat`. Note files outside the phase's plausible scope as possible scope creep.

3. **Locate implementation files.** Use `rg`, `rg --files`, `git grep`, and direct reads – and include the untracked file list from step 1. Prefer parallel reads.

4. **Apply the review checklist (below).** Prioritize bugs, race conditions, data loss, incorrect behavior, schema/contract drift, missing production wiring, and missing tests.

5. **Update the full status surface in `{{plan_path}}`** before final reporting (use the plan's own legend – see Plan Write Policy):
   - For each reviewed phase, mark `### Work` bullets done only when the change exists and is correct. Use the partial marker for partial items. Leave unimplemented items unmarked.
   - For each reviewed phase, mark `### Acceptance Criteria` bullets done only when met and verifiable now; partial marker for partial coverage.
   - Flip task/checklist checkboxes (`- [ ]` → `- [x]`) and `## Files to Create or Modify` / file-inventory bullets only for items individually verified complete.
   - Mark the phase heading and any per-phase `Status:` line done only when every `### Work` bullet, `### Acceptance Criteria` bullet, and tracked checkbox/file for that phase is done. Use the partial/in-progress marker otherwise.
   - Update the `## Phase Status` table (or any status/summary table): set each reviewed phase's Status cell to match its heading.
   - In the `## Phase Flow` Mermaid graph, update **both** the icon in the phase's node label **and** its `class <node> <className>` line so they agree (e.g. heading done → `… ✅` in the label and `class P3 done`). When a phase is fully done, also update every inbound/outbound edge whose connected nodes are both done.
   - In `## Recommended Execution Order`, apply the same markers to numbered entries.
   - Apply the same markers to every other reference to the reviewed phase elsewhere in the plan.
   - Update `## Decisions` (free-form, live) so it reflects every decision made, confirmed, or changed during this review; walk `## Open Questions` (append-only) and `## Residual Risks` (add/remove/reword) per the policy above. Leaving `## Decisions` or `## Open Questions` empty (or as a "none" note) is correct when nothing arose – do not add placeholder content.
   - Walk `{{plan_path}}.progress.json` `proposed_decisions` for each reviewed phase: fold any accepted ones into `## Decisions` (rephrasing as needed), drop the rest. If you promoted a phase to `completed`, also clear the entire `phases[N]` block from progress.json – the plan now carries the authoritative state.
   - After all writes (to `{{plan_path}}` and/or `{{plan_path}}.progress.json`), run the bake command once to refresh the rendered HTML.

6. **Run verification.** `{{build_cmd}}` always. `{{test_cmd}}` when tests exist. **Passing tests are necessary but not sufficient** – confirm the tests actually prove each acceptance criterion, not just that they execute. A test whose name implies coverage but whose body doesn't exercise the claimed behavior is a finding. Record which phases the verification covered and note any command that could not be run.

7. **Re-read edited sections** to ensure the plan says what the code actually does.

8. **Commit locally – always, whenever the plan changed.** This command owns the plan's status surface; if step 5 edited the plan it must end in a local commit. Inspect `git status --short`, stage only review-related files (normally just `{{plan_path}}` plus any supporting-doc edits made during the review – this includes the Mermaid graph, status table, per-phase `Status:` lines, and checkbox flips, all in `{{plan_path}}`), leave unrelated implementation changes unstaged. Concise message: `Review implementation phase N` for one phase, `Review implementation phases N-M` for a range. No co-author trailer. Do not push. Only skip the commit when the review made zero plan edits (see Completion Rules – no empty commits).

## Review Checklist

Use selectively but explicitly; skip items only when irrelevant to the phase.

- **Phase artifacts.** Every change promised by the target phase exists in the expected location with the expected shape and behavior.
- **Plan compliance.** Each acceptance criterion is satisfied and verifiable now, or marked partial with a reason.
- **Conventions** (see `.deployed-agents/conventions.md` and the conventions block embedded in `.agents/agents/review-iterate.md`). Layer boundaries, naming, nullability, exception types, FK constraints, etc.
- **Race conditions / transactions** where the phase owns write behavior under concurrent callers.
- **Tests.** New behaviour has a test that exercises it. Test names match what the body asserts.
- **Documentation.** Stale supporting-docs text → `DOC` finding. Do not silently rewrite supporting docs – flag the drift.
- **Decisions, Open Questions, and Residual Risks.** If the review surfaced a question that needs the user's decision, append it to `## Open Questions` (append-only). Maintain `## Decisions` (free-form, live): record decisions the user made/confirmed/ratified, and revise or remove entries that changed during the review. An empty `## Open Questions` or `## Decisions` (or a "none" note) is acceptable and is never a finding. Update `## Residual Risks` per the policy.

## Completion Rules

If findings remain for a reviewed phase, do not mark the phase heading `✅`. Mark implemented bullets `✅`, partial bullets `⚠️ [partial: reason]`, leave missing items unmarked, and mark the phase heading `⚠️`.

If no findings remain, mark the whole surface done in the plan's legend: every `### Work` bullet, every `### Acceptance Criteria` bullet, every tracked checkbox (`- [x]`) and file-inventory bullet, the phase heading, the per-phase `Status:` line, the `## Phase Status` table row, the `## Phase Flow` node label **and** its `class` line, and the matching `## Recommended Execution Order` entry. Confirm no other reference to that phase still implies it is incomplete.

When no phases require review, leave the plan untouched and do not create an empty commit.

## Final Response

The Final Response is **always two parts**, in this order, separated by a blank line. Part 2 is always present, even when nothing is outstanding.

**Part 1 – Review summary (one paragraph).** Return one plain-text paragraph describing only what is still outstanding for the reviewed phase(s). Mention each outstanding item inline by phase number with the concrete file, test, command, or behavior that needs to change. When you auto-detected the phase(s) because no explicit selector was given, begin the response with a single short clause naming the phase(s) reviewed and why (e.g. `Auto-detected in-progress Phase 4; ` or `No phase in-progress, fell back to Phase 7; `) and then continue with the outstanding-work paragraph or the exact no-outstanding sentence below. Convert every remaining `⚠️ [partial: reason]` marker into a concrete next action inside the same paragraph. If you appended an Open Question during this review and it needs the user's attention, mention it in the same paragraph as `Open Question: ...`. Do not include headings, bullet lists, task-list syntax, code fences, severity labels, review narrative, verification history, documentation summaries, or any list of unchanged areas. Do not end with an offer or a summary sentence.

If nothing is outstanding, Part 1 is exactly one of:
- `No outstanding items for phase N.` (single phase)
- `No outstanding items for phases N-M.` (contiguous range)
- `No outstanding items for phases N, M, and P.` (non-contiguous list)

**Part 2 – Coder instructions (separate paragraph, always present).** After a blank line, add a paragraph addressed to the implementer/coder that states **only the code changes to make**: the files to edit, the behavior to implement, and the test(s) to add or update so the acceptance criteria and contract are met. State nothing else. Do NOT tell the coder to run the build, to iterate, to not edit the plan/docs/status markers, or any other process or prohibition – the coder already knows its own workflow and constraints. No meta-instructions, no "do not", no verification or commit guidance. Make it directly actionable so the coder can act without re-deriving the findings. Begin this paragraph with `Coder instructions: `. When Part 1 is a `No outstanding items` sentence, Part 2 is exactly `Coder instructions: Nothing to fix.`
