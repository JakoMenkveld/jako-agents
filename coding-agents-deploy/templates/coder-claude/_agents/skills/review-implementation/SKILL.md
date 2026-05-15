---
name: review-implementation
description: Review one or more {{project_name}} implementation phases end-to-end against {{plan_path}} and the current codebase. Update phase status markers truthfully, commit the review locally, and report remaining actionable work. Use when invoked as `/review-implementation` with optional phase numbers or a range.
---

# Review Implementation

Review one or more {{project_name}} implementation phases end to end, update `{{plan_path}}` truthfully with status markers, commit the review locally, and report remaining actionable work.

## Plan Write Policy

`{{plan_path}}` is writable for THIS command, but the scope is narrow.

**Allowed edits:**
- Status markers (`✅`, `⚠️`, `⚠`) on phase headings, `### Work` bullets, `### Acceptance Criteria` bullets, `## Phase Flow` nodes and edge labels, and `## Recommended Execution Order` entries.
- Concise partial-reason notes inside the bracketed marker: `⚠️ [partial: SetMeasures fixed but tests pending]`.
- `## Open Questions`: **append-only**. Add new questions to the bottom of the numbered list. Do NOT edit, renumber, resolve, mark, remove, or move existing entries — the user resolves Open Questions manually.
- `## Residual Risks`: add new items raised during the review, remove risks resolved by shipped code, re-word risks whose blast radius changed.

**Disallowed edits:**
- Adding new phase sections, renaming phases, rewriting acceptance-criteria text, moving text between phases, or changing any non-marker plan content.
- Editing, renumbering, resolving, or removing any existing `## Open Questions` entry.

Status icons:
- `✅` — complete.
- `⚠️` or `⚠` — partially complete (always include a short reason in brackets).
- (no icon) — not started or not yet reviewed.

Never invent acceptance criteria, never silently delete plan text, and never leave a phase in a state that contradicts the code.

## Inputs

Infer the target phase number(s) from the user. Accept a single number (`phase 1`), an inclusive range (`2 to 5`, `2-5`), comma/word lists (`2, 3, 4 and 5`), or a mix. Normalize to a sorted, de-duplicated list and review in ascending order unless asked otherwise. If no phase number is provided, ask once.

Repository root is the current workspace. Plan file: `{{plan_path}}`.

## Review severity

- `BLOCKER` — code does not compile, target phase cannot work, data corruption risk, security regression, or acceptance criteria are clearly unmet.
- `MAJOR` — important behavior, validation, test, tool wiring, or documentation contract is missing or wrong.
- `MINOR` — edge case, maintainability issue, incomplete docs, or narrow test gap that does not invalidate the phase.
- `NIT` — style or local cleanup with no material behavioral risk.
- `DOC` — documentation or plan drift only. Code is acceptable but docs are stale.

When supporting docs are stale but the implementation is correct, treat it as a `DOC` finding and update the relevant doc instead of asking for a code change.

## Workflow

1. **Survey state.** `git status --short`. Read the selected phase(s) in `{{plan_path}}`, including each phase's `### Work` and `### Acceptance Criteria`, plus surrounding `## Phase Flow`, `## Recommended Execution Order`, `## Open Questions`, and `## Residual Risks`. Read supporting docs in the repo when they overlap the reviewed phases.

2. **Inspect the diff.** If the phase work is committed, use `git diff --stat HEAD~1..HEAD`; otherwise `git diff --stat` and `git status --short`. Note files outside the phase's plausible scope as possible scope creep.

3. **Locate implementation files.** Use `rg`, `rg --files`, `git grep`, and direct reads. Prefer parallel reads.

4. **Apply the review checklist (below).** Prioritize bugs, race conditions, data loss, incorrect behavior, schema/contract drift, missing production wiring, and missing tests.

5. **Update `{{plan_path}}` markers** before final reporting:
   - For each reviewed phase, mark `### Work` bullets `✅` only when the change exists and is correct. Use `⚠️ [partial: reason]` for partial items. Leave unimplemented items unmarked.
   - For each reviewed phase, mark `### Acceptance Criteria` bullets `✅` only when met and verifiable now. Use `⚠️ [partial: reason]` for partial coverage.
   - Mark the phase heading `✅` only when every `### Work` and `### Acceptance Criteria` bullet for that phase is `✅`. Use `⚠️` when any reviewed bullet is partial.
   - In `## Phase Flow`, mark the phase node `✅` when the heading is `✅`, `⚠️` when partial. When a phase heading is `✅`, also mark every inbound/outbound edge whose connected nodes are both `✅`.
   - In `## Recommended Execution Order`, apply the same markers to numbered entries.
   - Apply the same markers to every other reference to the reviewed phase elsewhere in the plan.
   - Walk `## Open Questions` (append-only) and `## Residual Risks` (add/remove/reword) per the policy above.

6. **Run verification.** `{{build_cmd}}` always. `{{test_cmd}}` when tests exist. Record which phases the verification covered and note any command that could not be run.

7. **Re-read edited sections** to ensure the plan says what the code actually does.

8. **Commit locally.** Inspect `git status --short`, stage only review-related files (normally just `{{plan_path}}` plus any supporting-doc edits made during the review), leave unrelated changes unstaged. Concise message: `Review implementation phase N` for one phase, `Review implementation phases N-M` for a range. No co-author trailer. Do not push.

## Review Checklist

Use selectively but explicitly; skip items only when irrelevant to the phase.

- **Phase artifacts.** Every change promised by the target phase exists in the expected location with the expected shape and behavior.
- **Plan compliance.** Each acceptance criterion is satisfied and verifiable now, or marked partial with a reason.
- **Conventions** (see `AGENTS.md` and the conventions block embedded in `.claude/agents/review-iterate.md`). Layer boundaries, naming, nullability, exception types, FK constraints, etc.
- **Race conditions / transactions** where the phase owns write behavior under concurrent callers.
- **Tests.** New behaviour has a test that exercises it. Test names match what the body asserts.
- **Documentation.** Stale supporting-docs text → `DOC` finding. Do not silently rewrite supporting docs — flag the drift.
- **Open Questions and Residual Risks.** If the review surfaced a question that needs the user's decision, append it to `## Open Questions`. Update `## Residual Risks` per the policy.

## Completion Rules

If findings remain for a reviewed phase, do not mark the phase heading `✅`. Mark implemented bullets `✅`, partial bullets `⚠️ [partial: reason]`, leave missing items unmarked, and mark the phase heading `⚠️`.

If no findings remain, mark every `### Work` bullet, every `### Acceptance Criteria` bullet, the phase heading, the matching `## Phase Flow` node, and the matching `## Recommended Execution Order` entry `✅`. Confirm no other reference to that phase still implies it is incomplete.

When no phases require review, leave the plan untouched and do not create an empty commit.

## Final Response

Return one plain-text paragraph describing only what is still outstanding for the reviewed phase(s). Mention each outstanding item inline by phase number with the concrete file, test, command, or behavior that needs to change. Convert every remaining `⚠️ [partial: reason]` marker into a concrete next action inside the same paragraph. If you appended an Open Question during this review and it needs the user's attention, mention it in the same paragraph as `Open Question: ...`.

Do not include headings, bullet lists, task-list syntax, code fences, severity labels, review narrative, verification history, documentation summaries, or any list of unchanged areas. Do not end with an offer or a summary sentence.

If nothing is outstanding, return exactly:
- `No outstanding items for phase N.` (single phase)
- `No outstanding items for phases N-M.` (contiguous range)
- `No outstanding items for phases N, M, and P.` (non-contiguous list)
