---
description: Review one or more {{project_name}} implementation phases against {{plan_path}} and the current codebase, truthfully update the whole status surface (phase headings, Work/Acceptance bullets, task checkboxes, the Phase Status table, per-phase Status lines, and the Phase Flow Mermaid graph — node labels and class lines), commit the review locally, and report remaining actionable work.
---

# review-implementation

Review one or more {{project_name}} implementation phases end to end, update `{{plan_path}}` truthfully with status markers, commit the review locally, and report remaining actionable work.

## Plan Write Policy

`{{plan_path}}` is writable for THIS command, but the scope is narrow.

**Allowed edits — the full status surface of every reviewed phase:**
- Status markers on the phase heading, `### Work` bullets, `### Acceptance Criteria` bullets, and `## Recommended Execution Order` entries.
- The `## Phase Flow` Mermaid graph — **both** the status icon embedded in the node label (e.g. `P3[Phase 3: … ⬜]` → `… ✅`) **and** the matching classification line (e.g. `class P3 pending` → `class P3 done`). Keep the node label, the `class` line, and the diagram's own `classDef` names consistent with each other. Also update edge labels.
- A `## Phase Status` table (or any phase status/summary table): the Status cell of each reviewed phase's row.
- A per-phase `Status:` line directly beneath the phase heading.
- Task/checklist checkboxes (`- [ ]` → `- [x]`) and `## Files to Create` / file-inventory bullets for the reviewed phase — flip an individual item only when that specific item is verified complete in code.
- Concise partial-reason notes inside the bracketed marker, e.g. `⚠️ [partial: SetMeasures fixed but tests pending]`.
- `## Open Questions`: **append-only**. Add new questions to the bottom of the numbered list. Do NOT edit, renumber, mark, resolve, remove, or move existing entries — the user resolves Open Questions manually.
- `## Residual Risks`: add new items raised during the review, remove risks resolved by shipped code, re-word risks whose blast radius has changed.

**Use the plan's own status vocabulary.** If the plan declares a legend — a `Legend:` line, a status-table legend, or Mermaid `classDef` names like `done`/`inProgress`/`pending`/`blocked` — match it exactly (icons *and* class names; e.g. `🟡 in-progress` and `class P1 inProgress`, not `⚠️`). Only when the plan declares no vocabulary, default to `✅` complete / `⚠️ [partial: reason]` / unmarked. Every surface above must end the review agreeing with every other surface and with the code.

**Disallowed edits:**
- Adding new phase sections, renaming phases, rewriting acceptance-criteria text, moving text between phases, or changing any non-marker plan content. If the plan is structurally stale, report that to the user instead of restructuring it.
- Editing, renumbering, resolving, or removing any existing `## Open Questions` entry.

Status icons:
- `✅` — complete.
- `⚠️` or `⚠` — partially complete (always include a short reason in square brackets).
- (no icon) — not started, not reviewed, or not status-marked yet.

Never invent acceptance criteria, never silently delete plan text, and never leave a phase in a state that contradicts the code.

## Inputs

Infer the target phase number(s) from the user. Accept a single number (`phase 1`), an inclusive range (`2 to 5`, `2-5`), comma/word lists (`2, 3, 4 and 5`), or a mix. Normalize to a sorted, de-duplicated list. If no phase number is provided, ask once.

Repository root is the current workspace. Plan file: `{{plan_path}}`.

## Review severity

- `BLOCKER` — code does not compile, target phase cannot work, data corruption risk, security regression, or acceptance criteria are clearly unmet.
- `MAJOR` — important behavior, validation, test, tool wiring, or documentation contract is missing or wrong.
- `MINOR` — edge case, maintainability issue, incomplete docs, or narrow test gap that does not invalidate the phase.
- `NIT` — style or local cleanup with no material behavioral risk.
- `DOC` — documentation or plan drift only.

## Workflow

1. **Survey state — including untracked files.** Run `git status --short --untracked-files=all`, `git diff --check`, and `git ls-files --others --exclude-standard`. **Untracked files are part of the review surface** — do not approve if relevant implementation files are untracked and you didn't inspect them. Read the selected phase(s) in `{{plan_path}}` in full — `### Work`, `### Acceptance Criteria`, surrounding `## Phase Flow`, `## Recommended Execution Order`, `## Open Questions`, `## Residual Risks`. Read supporting docs in the repo when they overlap.

2. **Inspect the diff.** Committed → `git diff --stat HEAD~1..HEAD`. Uncommitted → `git diff --stat`. Note files outside plausible scope.

3. **Locate implementation files.** Use `rg`, `rg --files`, `git grep`, direct reads — and include the untracked file list from step 1. Parallel where possible.

4. **Apply the review checklist** (below). Prioritize bugs, race conditions, data loss, incorrect behavior, schema/contract drift, missing production wiring, missing tests.

5. **Update the full status surface in `{{plan_path}}`** before final reporting (use the plan's own legend — see Plan Write Policy):
   - For each reviewed phase, mark `### Work` bullets done only when the change exists and is correct. Partial marker for partial items. Unmarked for missing.
   - For each reviewed phase, mark `### Acceptance Criteria` bullets done only when met and verifiable now.
   - Flip task/checklist checkboxes (`- [ ]` → `- [x]`) and `## Files to Create` / file-inventory bullets only for items individually verified complete.
   - Mark the phase heading and any per-phase `Status:` line done only when every `### Work` bullet, `### Acceptance Criteria` bullet, and tracked checkbox/file for that phase is done. Partial/in-progress marker otherwise.
   - Update the `## Phase Status` table (or any status/summary table): set each reviewed phase's Status cell to match its heading.
   - In the `## Phase Flow` Mermaid graph, update **both** the icon in the phase's node label **and** its `class <node> <className>` line so they agree. When a phase is fully done, also update every inbound/outbound edge whose connected nodes are both done.
   - In `## Recommended Execution Order`, apply the same markers.
   - Apply markers to every other reference to the reviewed phase elsewhere in the plan.
   - Walk `## Open Questions` (append-only) and `## Residual Risks` (add/remove/reword) per the policy above.

6. **Run verification**: `{{build_cmd}}` always; `{{test_cmd}}` when tests exist. **Passing tests are necessary but not sufficient** — confirm the tests actually prove each acceptance criterion, not just that they execute. A test whose name implies coverage but whose body doesn't exercise the claimed behavior is a finding. Record which phases the verification covered.

7. **Re-read edited sections** to ensure the plan says what the code actually does.

8. **Commit locally — always, whenever the plan changed.** This command owns the plan's status surface; if step 5 edited the plan (Mermaid graph, status table, per-phase `Status:` lines, checkbox flips, bullets — all in `{{plan_path}}`) it must end in a local commit. `git status --short`, stage only review-related files (normally `{{plan_path}}` plus supporting-doc edits), leave unrelated implementation changes unstaged. Message: `Review implementation phase N` (one phase) or `Review implementation phases N-M` (range) or `Review implementation phases N, M` (non-contiguous). No co-author trailer. Do not push. Only skip the commit when the review made zero plan edits (no empty commits).

## Review Checklist

Use selectively but explicitly; skip items only when irrelevant.

- **Phase artifacts.** Every change promised by the target phase exists in the expected location with the expected shape.
- **Plan compliance.** Each acceptance criterion is satisfied and verifiable now, or marked partial with a reason.
- **Conventions** (see `AGENTS.md` and `.agents/agents/review-iterate.md`).
- **Race conditions / transactions** where the phase owns write behavior.
- **Tests.** New behaviour has a test. Test names match what the body asserts.
- **Documentation.** Stale supporting-docs text → `DOC` finding. Flag the drift; do not silently rewrite.
- **Open Questions and Residual Risks.** Append questions surfaced by the review; update risks per the policy.

## Completion Rules

If findings remain for a reviewed phase, do not mark the heading `✅`. Mark implemented bullets `✅`, partial bullets `⚠️ [partial: reason]`, leave missing unmarked, and mark the phase heading `⚠️`.

If no findings remain, mark the whole surface done in the plan's legend: every `### Work` bullet, every `### Acceptance Criteria` bullet, every tracked checkbox (`- [x]`) and file-inventory bullet, the phase heading, the per-phase `Status:` line, the `## Phase Status` table row, the `## Phase Flow` node label **and** its `class` line, and the matching `## Recommended Execution Order` entry. Confirm no other reference to that phase still implies it is incomplete.

When no phases require review, leave the plan untouched and do not create an empty commit.

## Final Response

Return one plain-text paragraph describing only what is still outstanding. Mention each outstanding item inline by phase number with the concrete file, test, command, or behavior that needs to change. Convert every remaining `⚠️ [partial: reason]` into a concrete next action. If you appended an Open Question during this review and it needs the user's attention, mention it in the same paragraph as `Open Question: ...`.

Do not include headings, bullet lists, task-list syntax, code fences, severity labels, review narrative, verification history, documentation summaries, or any list of unchanged areas. Do not end with an offer or a summary sentence.

If nothing is outstanding:
- `No outstanding items for phase N.` (single)
- `No outstanding items for phases N-M.` (range)
- `No outstanding items for phases N, M, and P.` (non-contiguous)
