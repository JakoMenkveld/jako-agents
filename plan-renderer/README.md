# plan-renderer

Deterministic HTML render of a Plan-Contract markdown plan plus an
implementer-owned `progress.json` live-state overlay.

Two-layer design:

- **Source** lives in this directory (`plan-renderer/`) – the editable
  `index.html`, `renderer.js`, `styles.css`, and `black-silver.css`.
- **Shipped artifact** is a single self-contained `bake.py` with all of
  those assets embedded as Python string constants. That one file is the
  *only* runtime dependency the deployed agents need. After editing any
  source file, run `python pack.py` to refresh the embedded copies inside
  `bake.py`.

## Layout

```
plan-renderer/
  index.html              # template (BAKE: placeholder markers replaced at bake-time)
  renderer.js             # parser + DOM render + prompt-emit
  styles.css              # components, palette role variables
  black-silver.css        # palette, copied from omnis.shared.ui
  bake.py                 # self-contained: embeds all the above
  pack.py                 # refreshes the embedded assets inside bake.py
  README.md
  sample/
    implementation-plan.md
    implementation-plan.progress.json
    implementation-plan.html        # baked output (.gitignored in deployed projects)
```

## Workflow

### Edit + preview locally

Edit any of `index.html`, `renderer.js`, `styles.css`, `black-silver.css`,
then bake the sample plan and open the result in a browser:

```powershell
cd c:\vsprojects\jako-agents\plan-renderer
python pack.py                                   # refresh embedded assets
python bake.py --plan sample\implementation-plan.md
start sample\implementation-plan.html
```

`pack.py` rewrites only the lines between `# >>> PACK <file> >>>` and
`# <<< PACK <file> <<<` markers in `bake.py`. The bake logic itself stays
hand-edited.

### Deploy

The deploy ships only `bake.py` and this `README.md` into target projects'
`.deployed-agents/plan-renderer/`. Agents invoke it with:

```
python .deployed-agents/plan-renderer/bake.py --plan <plan-path>
```

It writes `<plan-stem>.html` next to the plan. The output is a single
self-contained file (CSS + JS inlined; mermaid loads from jsdelivr CDN).
Open it directly in any browser – `file://` works; no server needed.

## Plan-md schema additions

Beyond the current Plan Contract, the renderer relies on two small things:

1. **Stable per-item IDs** on `### Work`, `### Acceptance Criteria`, and
   `### Phase N` file bullets: `- [w1] …`, `- [a1] …`, `- [f1] …`.
   Required so `progress.json` can refer to specific items across edits.
   If missing, the parser auto-assigns sequential IDs by index but they
   will drift if bullets reorder.

2. **Phase Status table** *or* per-phase `Status:` line *or* Mermaid
   `class P0 done` lines – any one carries the per-phase lifecycle state
   (`pending` / `current` / `under-review` / `needs-fixes` / `completed`).
   Reviewer-owned; the renderer reads them.

The rest of the plan is parsed from the canonical Plan Contract layout.

## Progress overlay (`<plan>.progress.json`)

```json
{
  "version": 1,
  "plan_path": "implementation-plan.md",
  "updated_at": "ISO-8601",
  "active_phase": 1,
  "phases": {
    "<phase-number>": {
      "sub_state": "idle | coding | inner-review | applying-fixes | ready",
      "cycle": 2,
      "cycle_cap": 3,
      "started_at": "ISO-8601",
      "items": {
        "w1": { "state": "pending | in-progress | done | blocked", "note": "optional" }
      },
      "activity": [
        { "at": "ISO-8601", "role": "implementer | inner-review | reviewer", "msg": "…" }
      ],
      "proposed_decisions": [
        { "at": "ISO-8601", "text": "…", "justification": "…" }
      ]
    }
  }
}
```

Implementer-owned. Reviewer clears each `phases[N]` block when promoting
the phase to `completed`.

## Theme

Top-right toggle: light / dark. Mermaid re-themes on toggle. State persists
in localStorage. To use a different palette, drop another file from
`omnis.shared.ui/wwwroot/palettes/` over `black-silver.css`, update the
`data-omnis-palette` attribute on `<html>` in `index.html`, run `pack.py`,
then rebake.

## Interactivity

Every button on the page is a deterministic prompt template. Clicking
copies the prompt to the clipboard and shows a toast preview. The human
pastes it back to the agent to drive the next change. The renderer never
edits the plan or progress overlay itself.
