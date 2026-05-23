"""One-shot patch: apply the "seed note: null" change to all already-deployed
projects so the implementer and reviewer instructions match the new template
contract. Idempotent — if the old_string is not present in a file (already
patched, or never had that text), the edit is skipped silently.

Run from anywhere:
    python scripts/patch_note_seed.py
"""
from __future__ import annotations

from pathlib import Path
import sys

EDITS = [
    # conventions.md – schema example
    (
        '"w1": { "state": "pending | in-progress | done | blocked", "note": "optional" }',
        '"w1": { "state": "pending | in-progress | done | blocked", "note": null }',
    ),
    # conventions.md – "Phase started" row
    (
        '| Phase started | Initialise `phases[N]` block (`started_at` with seconds, `sub_state: "coding"`, `cycle: 1`, `cycle_cap: 10`, items keyed off the plan\'s `[w*]`/`[a*]`/`[f*]` IDs, all `state: "pending"`); append activity `{role: "implementer", msg: "phase started"}`. | yes |',
        '| Phase started | Initialise `phases[N]` block (`started_at` with seconds, `sub_state: "coding"`, `cycle: 1`, `cycle_cap: 10`, items keyed off the plan\'s `[w*]`/`[a*]`/`[f*]` IDs, each seeded as `{ "state": "pending", "note": null }` — seed `note` explicitly so later in-place property writes don\'t fail on shells that can\'t add properties to existing JSON objects, e.g. PowerShell\'s `PSCustomObject`); append activity `{role: "implementer", msg: "phase started"}`. | yes |',
    ),
    # conventions.md – "Outer review started" row
    (
        '| Outer review started for phase N | Ensure `phases[N]` exists. If absent (e.g. the phase was previously completed and the block cleared, or the reviewer was invoked on a phase that never ran through `/implement-phase`), create it with a real ISO-8601 `started_at`, `cycle: 1`, `cycle_cap: 10`, and items seeded from the plan\'s `[w*]`/`[a*]`/`[f*]` IDs (`state: "pending"` unless the plan\'s `✅`/`⚠️` markers indicate otherwise – mirror them). Set `sub_state: "outer-review"`. Append `{role: "reviewer", msg: "outer review started"}`. Refresh `updated_at`. | yes |',
        '| Outer review started for phase N | Ensure `phases[N]` exists. If absent (e.g. the phase was previously completed and the block cleared, or the reviewer was invoked on a phase that never ran through `/implement-phase`), create it with a real ISO-8601 `started_at`, `cycle: 1`, `cycle_cap: 10`, and items seeded from the plan\'s `[w*]`/`[a*]`/`[f*]` IDs as `{ "state": "pending", "note": null }` (mirror the plan\'s `✅`/`⚠️` markers into `state` where they indicate something other than pending — `note` still seeds as `null`). Set `sub_state: "outer-review"`. Append `{role: "reviewer", msg: "outer review started"}`. Refresh `updated_at`. | yes |',
    ),
    # implement-phase.md (claude lane) – step 2.5 bullet
    (
        "- `items` keyed off the plan's `[w*]`/`[a*]`/`[f*]` bullet IDs (all `state: \"pending\"` initially).",
        "- `items` keyed off the plan's `[w*]`/`[a*]`/`[f*]` bullet IDs, each seeded as `{ \"state\": \"pending\", \"note\": null }`. Seed `note` explicitly (even as `null`) so later writes that refresh a note via in-place property assignment don't fail on shells that can't add properties to an existing JSON object (e.g. PowerShell's `PSCustomObject`).",
    ),
    # review-implementation – overlay-open paragraph (1b.). Anchored on the
    # substring after the rendered `{{plan_progress_path}}` so it works in
    # both template files and deployed-and-rendered project files.
    (
        "items seeded from the plan's `[w*]`/`[a*]`/`[f*]` IDs and mirroring any existing `✅`/`⚠️` markers); set `sub_state: \"outer-review\"`",
        "items seeded from the plan's `[w*]`/`[a*]`/`[f*]` IDs as `{ \"state\": \"pending\", \"note\": null }`, with the plan's `✅`/`⚠️` markers folded into `state` where they indicate something other than pending — always seed `note` as `null` so later in-place note writes don't fail on shells that can't add properties to existing JSON objects, e.g. PowerShell's `PSCustomObject`); set `sub_state: \"outer-review\"`",
    ),
    # review-implementation – top-of-file Plan Write Policy bullet. Anchored
    # mid-sentence so it matches both template and rendered project files.
    (
        "create it if absent, seeding items from the plan's `[w*]`/`[a*]`/`[f*]` IDs and mirroring any `✅`/`⚠️` markers already on the bullets), then set `sub_state: \"outer-review\"`",
        "create it if absent, seeding each item from the plan's `[w*]`/`[a*]`/`[f*]` IDs as `{ \"state\": \"pending\", \"note\": null }`; mirror any `✅`/`⚠️` markers already on the bullets into `state`, but `note` still seeds as `null` so later in-place note writes don't fail on shells that can't add properties to existing JSON objects, e.g. PowerShell's `PSCustomObject`), then set `sub_state: \"outer-review\"`",
    ),
]


CANDIDATE_FILES = [
    ".deployed-agents/conventions.md",
    ".claude/commands/implement-phase.md",
    ".agents/commands/implement-phase.md",
    ".claude/commands/review-implementation.md",
    ".agents/skills/review-implementation/SKILL.md",
]


def patch_project(project: Path) -> tuple[int, int]:
    """Returns (files_changed, edits_applied)."""
    files_changed = 0
    edits_applied = 0
    for rel in CANDIDATE_FILES:
        target = project / rel
        if not target.exists():
            continue
        text = target.read_text(encoding="utf-8")
        original = text
        local_edits = 0
        for old, new in EDITS:
            if old in text:
                text = text.replace(old, new, 1)
                local_edits += 1
        if text != original:
            target.write_text(text, encoding="utf-8")
            files_changed += 1
            edits_applied += local_edits
            print(f"  {rel} – {local_edits} edit(s)")
    return files_changed, edits_applied


def main(argv: list[str]) -> int:
    projects = [
        Path(p) for p in [
            r"c:/vsprojects/A1L/ecogenie-ai-observatory",
            r"c:/vsprojects/A1L/ecogenie-backend-ai-agent",
            r"c:/vsprojects/A1L/ecogenie-backend",
            r"c:/vsprojects/A1L/ecogenie-frontend",
            r"c:/vsprojects/A1L/ecogenie-ui-library",
            r"c:/vsprojects/A1L/ecogenie-ui-prime",
            r"c:/vsprojects/omnis/gold",
            r"c:/vsprojects/omnis/omnis-shared",
            r"c:/vsprojects/pp/AIAPI",
        ]
    ]
    total_files = 0
    total_edits = 0
    for proj in projects:
        if not proj.exists():
            print(f"SKIP (missing): {proj}")
            continue
        print(f"== {proj}")
        f, e = patch_project(proj)
        if f == 0:
            print("  (no changes — already patched or no matching files)")
        total_files += f
        total_edits += e
    print()
    print(f"Done: {total_files} file(s) changed, {total_edits} edit(s) applied across {len(projects)} project(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
