# Coding-agent conventions — {{project_name}}

Source of truth for the **deployed coding-agent overlay** in this repository. It is deployed scaffolding (gitignored by default), kept deliberately separate from whatever root-level agent-instruction files the project or developer maintains — this overlay never reads, writes, or merges those. The deployed commands and skills point here for project conventions; nothing outside the overlay is touched.

## First-run self-configuration

Before doing anything else on your first run in this repository, check whether this file and the agent configs still contain unfilled deploy placeholders, and fix them in place if so. Treat any of the following as unfilled:

- `## Project` reads `Unknown stack` or is empty.
- The build or test command is `<add build command>` / `<add test command>` — anywhere it appears: here under `## Build & test`, in the `## Conventions`/division-of-labour text, in `.claude/settings.json` permission entries, and in the `review-iterate` agent file.
- `## Conventions` contains only the generic-fallback note ("this is a generic fallback").
- Any other `<add …>` sentinel (e.g. `<add sln name>`).

When you find unfilled placeholders: detect the real stack from the repo (`package.json` scripts, `*.csproj`/`*.sln`, `pyproject.toml`, `go.mod`, Makefile, etc.), then edit, in this order, (1) this file (`.deployed-agents/conventions.md`) — `## Project`, `## Build & test`, `## Conventions`; (2) the harness settings file `.claude/settings.json` — replace the `<add build command>` / `<add test command>` Bash allow entries with the real commands; (3) the `review-iterate` agent file — its stack summary, build command, test command, and conventions lines. Keep the build and test commands byte-identical across all three. Report a one-line summary of what you filled in, then continue with the original task. If the stack genuinely cannot be determined, ask the user once instead of guessing.

This is a one-time repair: once the placeholders are gone, skip this section.

## Project

{{stack_summary}}

## Plan-driven delivery

The authoritative plan is **[{{plan_path}}]({{plan_path}})**. Phases are headed `## Phase N: <Title>`. A phase is complete when its heading carries a trailing `✅` marker. Work the lowest-numbered open phase unless the user names a specific one.

Do not invent acceptance criteria the plan doesn't list, and do not bundle multiple phases into one commit unless the orchestrating command says to.

### Plan structure for the renderer

The deployed plan renderer ([`.deployed-agents/plan-renderer/`](.deployed-agents/plan-renderer/)) reads the plan plus an implementer-owned progress overlay and emits a self-contained HTML view. Two small structural additions in the plan let the renderer key into the right items deterministically:

1. **Stable per-item IDs** on Work, Acceptance, and Files bullets:

   ```markdown
   ### Work
   - [w1] add @xyflow/react runtime dependency
   - [w2] render ReactFlow top-to-bottom, full width

   ### Acceptance Criteria
   - [a1] a large run renders as a full-width vertically scrolling flowchart
   - [a2] mixed-status run shows all five colours correctly

   ### Phase 1
   - [f1] `package.json` – add @xyflow/react runtime dep
   - [f2] `src/components/observatory/Flowchart.tsx` – ReactFlow render
   ```

   IDs are per phase, numbered from 1, and prefixed `w` (Work), `a` (Acceptance), `f` (Files). Reviewer-emitted; coders never rewrite them.

2. **Per-phase lifecycle marker** – any one of these carries the state (`pending`, `current`, `under-review`, `needs-fixes`, `completed`):

   - A `## Phase Status` table near the top: `| Phase 0 | completed | … |`
   - A `Status:` line immediately under the phase heading
   - A Mermaid `class P0 done` / `class P0 current` line inside the `## Phase Flow` block (`classDef` declares the visual)

   These are additive to the existing `✅` (completed) and `⚠️` (partial) heading markers. Reviewer-owned.

### Live progress overlay

`{{plan_progress_path}}` (sibling of the plan, e.g. `docs/implementation-plan.progress.json`) is an **implementer-owned** overlay that carries live state during a phase: which Work/Files items are in progress, which inner-review cycle the implementer is on, an activity log, and any decisions the implementer wants to propose to the reviewer. The renderer merges this into the HTML view in near-real-time.

Schema:

```json
{
  "version": 1,
  "plan_path": "{{plan_path}}",
  "updated_at": "<ISO-8601 UTC>",
  "active_phase": 1,
  "phases": {
    "<phase-number>": {
      "sub_state": "idle | coding | inner-review | applying-fixes | ready | blocked",
      "cycle": 2,
      "cycle_cap": 10,
      "started_at": "<ISO-8601 UTC, with seconds>",
      "items": {
        "w1": { "state": "pending | in-progress | done | blocked", "note": "optional" }
      },
      "activity": [
        { "at": "<ISO-8601 UTC, with seconds>", "role": "implementer | inner-review | reviewer", "msg": "…" }
      ],
      "proposed_decisions": [
        { "at": "<ISO-8601 UTC, with seconds>", "text": "…", "justification": "…" }
      ]
    }
  }
}
```

Ownership:

- **Implementer commands** (`implement-phase`, `implement-fixes`) read and write `progress.json` continuously (see "Implementer write checkpoints" below).
- The **inner reviewer** (`review-iterate`) stays read-only. The calling implementer command relays its findings into `activity` (with role `inner-review`) as part of the same write.
- **Reviewer commands** (`review-implementation`) clear the `phases[N]` block when promoting phase N to `completed` (the plan's lifecycle marker is the authoritative record from that point). They may also fold accepted `proposed_decisions` into `## Decisions` in the plan and then clear them.
- **`archive-plan`** moves `progress.json` alongside the plan when archiving and starts the fresh plan with no overlay.

Coder-role agents do not edit the plan, but `proposed_decisions` is their channel for surfacing decisions to the reviewer.

**Implementer write checkpoints.** Update `progress.json` and bake at each of these events. These are **step gates, not commentary** – the calling command treats each as a mandatory write paired with the bake. The whole point is that the user, watching the rendered HTML in a browser, sees visible movement between every transition. Silence reads as a stall:

| Event | Update | Bake |
|---|---|---|
| Phase started | Initialise `phases[N]` block (`started_at` with seconds, `sub_state: "coding"`, `cycle: 1`, `cycle_cap: 10`, items keyed off the plan's `[w*]`/`[a*]`/`[f*]` IDs, all `state: "pending"`); append activity `{role: "implementer", msg: "phase started"}`. | yes |
| Begin a Work item / start writing a file | Flip the relevant item from `"pending"` → `"in-progress"`; optional one-line `note`. | yes |
| Finish a Work item / file is written and would survive the build | Flip the item to `"done"`. | yes |
| About to spawn `review-iterate` | Set `sub_state: "inner-review"`; on cycles ≥ 2 increment `cycle`; append activity `{role: "implementer", msg: "inner-review pass requested (cycle K)"}`. **Write before the Agent tool call, not after.** | yes |
| Inner reviewer returned findings (cycle K) | Set `sub_state: "applying-fixes"`. For each non-trivial finding, append `{role: "inner-review", msg: "finding[<SEV>] <file:line> <summary>"}`. **Write before the first code edit in response**, not after. | yes |
| Started applying a specific finding (implement-fixes lane) | Append `{role: "implementer", msg: "starting <SEV> <file:line>: <one-line scope>"}`. | yes |
| Resolved a specific finding on disk (implement-fixes lane) | Append `{role: "implementer", msg: "resolved <SEV> <file:line>: <one-line outcome>"}`; refresh affected item `note`. | yes |
| Finished a batch of fix code (implement-phase lane) | Append `{role: "implementer", msg: "applied N fixes for cycle K: <one-line scope>"}`. **Write before rebuilding**, not after, so the user sees the batch boundary in real time. | yes |
| Inner reviewer returned clean | Set `sub_state: "ready"`; append `{role: "inner-review", msg: "clean on cycle K"}`. | yes |
| Cycle cap hit without approval | Set `sub_state: "blocked"`; append `{role: "implementer", msg: "cycle cap hit – escalating"}`. Stop and surface to the user. | yes |
| Made a judgment call during implementation | Append to `proposed_decisions` with `text` (the decision) and `justification` (why). Surface them as they happen, not at the end. | yes |
| Phase committed | Append `{role: "implementer", msg: "committed <short-sha>"}`; keep `sub_state: "ready"` (the outer reviewer takes over from here). | yes |

`activity` entries are appended; the renderer sorts them newest-first for display, so write order does not matter. Trim each phase's list to ~50 entries by dropping the oldest (lowest `at`). Every timestamp (`updated_at`, `started_at`, each `at`) is full ISO-8601 with seconds (e.g. `2026-05-23T10:14:07Z`) and reflects a real wall-clock instant – never a midnight placeholder. `updated_at` is the file-level timestamp; refresh it on every write.

Reviewer commands run the same bake command after every plan or progress write. The skipped bake leaves the rendered HTML stale, so anyone watching `{{plan_html_path}}` in a browser sees outdated state.

### Bake step

Every write to the plan or the progress overlay must be followed by a bake. The deployed renderer is at `.deployed-agents/plan-renderer/`; the bake command is:

```
python .deployed-agents/plan-renderer/bake.py --plan {{plan_path}}
```

This refreshes `{{plan_html_path}}` (sibling of the plan) – a self-contained file the user can open directly in any browser (`file://`; no server). Auto-refresh on the page picks up the new state without intervention.

The bake is fast (single-pass file reads + string replace); per-write overhead is negligible. Skipping the bake leaves the rendered HTML stale, so the user sees outdated state.

### Diagrams in planning

When `review-and-fix` creates or repairs phases, lean into Mermaid diagrams to make spatial information legible – the renderer turns them into proper visuals. Use the right diagram for the situation:

- **Sequence diagrams** for request/response flows, agent interactions, message handoffs.
- **Class diagrams** for new data models, object relationships, type hierarchies.
- **ER diagrams** for database schema changes.
- **State diagrams** for state machines, lifecycle transitions.
- **Flowcharts** for control flow that branches non-trivially.

Inline diagram blocks directly inside the phase prose (between the phase heading and `### Work`) where they clarify the design. Top-level `## Phase Flow` is the existing place for the phase dependency graph; new diagrams go in-phase.

## Build & test

```
{{build_cmd}}
{{test_cmd}}
```

**Division of labour — read this before running anything.**

- **Implementers** (`implement-phase`, `implement-fixes`) run **only the build** (`{{build_cmd}}`). Iterate build → fix until clean. Implementers do **NOT** run the test suite — delegate that by spawning the `review-iterate` agent.
- **Reviewers** (`review-iterate`, `review-implementation`) run **both** `{{build_cmd}}` and `{{test_cmd}}`. They own test verification.

Running the test suite from an implementer is wasted work — it re-runs on every reviewer pass anyway. A phase is complete only after the build is clean *and* the reviewer has run the tests green; the implementer is responsible for the former, the reviewer for the latter.

## Conventions

{{conventions_block}}

## Writing style

- **Never use em dashes.** Do not emit the em dash character (`—`, U+2014) anywhere — not in code comments, identifiers, commit messages, the plan, docs, reports, or any other prose you write or edit. Always use an en dash (`–`, U+2013) instead. This applies to every agent and every artifact, including plan sections this overlay generates. When rewording is cleaner than a dash, prefer that; otherwise use the en dash.

## Severity tags for findings

Reviewers use these levels — apply them to your own self-checks too.

- **BLOCKER** — won't compile, won't run, or causes data loss / security regression.
- **MAJOR** — missing requirement, broken behavior, race condition, code disagrees with the plan, missing test on a new code path.
- **MINOR** — convention drift, missing non-critical test, stale documentation, narrow edge case.
- **NIT** — cosmetic (naming, whitespace, unused import). Acceptable to leave.
- **DOC** — documentation/plan drift only; the code is correct but a doc is stale. **Reviewers own plan/doc bookkeeping** — reviewer-role agents keep the plan and docs current, including completion-status markers (`[ ]`/`[x]`, phase `✅`/`⚠️`). Implementer/coder-role agents do not edit docs and never comment on or flag the plan's completion status (the reviewer reconciles it and does not need it pointed out); they surface other DOC findings for the reviewer.
- **SHARED** — a pattern that should be elevated to a shared library/component. Reviewers collect these for a separate suggestions file.

## Things you do NOT do

- Do not commit code that the user did not ask you to commit (unless the active command says to).
- Do not use `--no-verify` on git hooks.
- Do not force-push.
- Do not invent acceptance criteria. Open questions go back to the user.
- Do not introduce backward-compat shims, dual-write paths, feature flags, deprecation comments, or `// TODO: drop after vN` markers unless the plan explicitly calls for one.
- **Implementers/coders:** do not edit documentation files or plan status markers (`✅`, `⚠️`, checkbox state), and never comment on or flag the plan's completion status — not even as a DOC finding. The reviewer reconciles it and does not need it pointed out. Surface other DOC findings for the reviewer. **Reviewers** own plan/doc bookkeeping and are responsible for keeping the plan documentation up to date.

## Critical rule

Never do anything the user did not explicitly ask for.
