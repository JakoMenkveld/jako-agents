#!/usr/bin/env python3
"""migrate_ids.py - add stable [w*]/[a*]/[f*] IDs to a plan's bullets.

One-shot migration: walks an existing implementation-plan.md and adds
`[w1]`, `[w2]`, ... to each `### Work` bullet under a `## Phase N`
heading; `[a1]`, `[a2]`, ... to each `### Acceptance Criteria` bullet;
and `[f1]`, `[f2]`, ... to each per-phase Files block bullet under
`## Files to Create or Modify by Phase`. IDs restart at 1 per phase per
kind. Pre-existing IDs are preserved; numbering continues from the
highest seen.

Sub-bullets (indented with whitespace) are left untouched. Bullets in
other sections (Definition of Done, Automation Contract, Decisions,
Open Questions, Residual Risks, Test Plan, etc.) are out of scope.

Usage:
    python migrate_ids.py <path-to-plan.md>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# A top-level bullet: dash + space at column 0, followed by any content.
TOP_BULLET_RE = re.compile(r"^- (.*)$")
# Existing ID prefix, e.g. `[w1]`, `[a12]`, `[f3]` (case-insensitive).
ID_PREFIX_RE = re.compile(r"^\[([wfa])(\d+)\]\s+", re.IGNORECASE)


def migrate(text: str) -> tuple[str, int]:
    """Walk lines and emit a new version with IDs added. Returns the new
    text and a count of IDs added."""
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    i = 0
    n = len(lines)
    ids_added = 0

    # State: are we currently inside a Work/Acceptance/Files block?
    # And which phase number are we on (for per-phase counter resets)?
    block_kind: str | None = None       # "w" | "a" | "f" | None
    phase_num: int | None = None        # phase number we're in
    counters: dict[tuple[int, str], int] = {}  # (phase_num, kind) -> next index

    while i < n:
        line = lines[i]
        stripped = line.rstrip("\r\n")

        # Detect phase context.
        m_phase = re.match(r"^## Phase (\d+):", stripped)
        if m_phase:
            phase_num = int(m_phase.group(1))
            block_kind = None
            out.append(line)
            i += 1
            continue

        # Detect entering Files-to-Create-or-Modify - phase number comes from ### Phase N below.
        if stripped.startswith("## Files to Create or Modify by Phase"):
            phase_num = None  # reset; per-phase sub-headings will set it
            block_kind = "files-section"  # special sentinel
            out.append(line)
            i += 1
            continue

        # Top-level section other than Files-by-Phase or a phase: cancel block context.
        if stripped.startswith("## "):
            block_kind = None
            phase_num = None
            out.append(line)
            i += 1
            continue

        # Sub-headings.
        if stripped.startswith("### "):
            sub = stripped[4:].strip()
            if sub == "Work" and phase_num is not None and block_kind != "files-section":
                block_kind = "w"
            elif sub == "Acceptance Criteria" and phase_num is not None and block_kind != "files-section":
                block_kind = "a"
            elif block_kind == "files-section":
                m_p = re.match(r"^Phase\s+(\d+)\s*$", sub, re.IGNORECASE)
                if m_p:
                    phase_num = int(m_p.group(1))
                    block_kind = "f"
                else:
                    block_kind = None
            else:
                block_kind = None
            out.append(line)
            i += 1
            continue

        # Top-level bullet inside an active block?
        if block_kind in ("w", "a", "f") and phase_num is not None:
            m_b = TOP_BULLET_RE.match(stripped)
            if m_b:
                body = m_b.group(1)
                existing = ID_PREFIX_RE.match(body)
                key = (phase_num, block_kind)
                if existing:
                    # Pre-existing ID - learn the highest so we continue from there.
                    if existing.group(1).lower() == block_kind:
                        cur = int(existing.group(2))
                        counters[key] = max(counters.get(key, 0), cur)
                    out.append(line)
                else:
                    # Add a new ID at the next available number.
                    counters[key] = counters.get(key, 0) + 1
                    new_id = f"[{block_kind}{counters[key]}]"
                    # Preserve original line ending.
                    eol = line[len(stripped):]
                    out.append(f"- {new_id} {body}{eol}")
                    ids_added += 1
                i += 1
                continue

        # Sub-bullet (indented) or anything else: pass through.
        out.append(line)
        i += 1

    return "".join(out), ids_added


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: python migrate_ids.py <path-to-plan.md>", file=sys.stderr)
        sys.exit(2)
    plan = Path(sys.argv[1]).resolve()
    if not plan.exists():
        print(f"plan not found: {plan}", file=sys.stderr)
        sys.exit(1)

    original = plan.read_text(encoding="utf-8")
    migrated, added = migrate(original)
    if added == 0:
        print(f"no IDs added (plan already has them or no eligible bullets): {plan}")
        return
    plan.write_bytes(migrated.encode("utf-8"))
    print(f"added {added} stable IDs to {plan}")


if __name__ == "__main__":
    main()
