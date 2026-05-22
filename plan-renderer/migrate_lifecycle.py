#!/usr/bin/env python3
"""migrate_lifecycle.py - add lifecycle surfaces to an existing plan.

One-shot migration. Reads an implementation-plan.md, infers each phase's
current lifecycle state from existing markers (or defaults to `pending`),
and adds the two machine-readable surfaces the new renderer prefers:

  1. A `## Phase Status` table inserted right after `## Phase Flow`, with
     one row per phase mapping `Phase N | <state>`.
  2. Mermaid `class P<N> <state>` lines inside the `## Phase Flow`
     fenced block, so the rendered flowchart colours follow the palette.

State inference per phase heading:
  - heading ends with `✅`              -> `completed`
  - heading ends with `⚠️` or `⚠`       -> `current`
  - otherwise                           -> `pending`

If the plan already has a `## Phase Status` table or any Mermaid `class P*`
lines, both blocks are left untouched (idempotent).

Usage:
    python migrate_lifecycle.py <path-to-plan.md>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PHASE_HEADING_RE = re.compile(r"^## Phase (\d+):\s*(.+?)\s*$")
DONE_MARKER_RE = re.compile(r"✅\s*$")
PARTIAL_MARKER_RE = re.compile(r"⚠️?\s*(\[[^\]]*\])?\s*$")


def infer_state(heading: str) -> str:
    if DONE_MARKER_RE.search(heading):
        return "completed"
    if PARTIAL_MARKER_RE.search(heading):
        return "current"
    return "pending"


def collect_phases(text: str) -> list[tuple[int, str, str]]:
    """Returns [(phase_num, full_heading_text, inferred_state), ...]."""
    out = []
    for line in text.splitlines():
        m = PHASE_HEADING_RE.match(line)
        if m:
            out.append((int(m.group(1)), line, infer_state(line)))
    return out


def has_phase_status_table(text: str) -> bool:
    return bool(re.search(r"(?m)^## Phase Status\s*$", text))


def has_mermaid_class_lines(text: str) -> bool:
    """Detect whether the Phase Flow block already has any `class P# state`
    lines. Only inspects the first ```mermaid``` block since that's where
    Phase Flow lives."""
    m = re.search(r"```mermaid\s*\n([\s\S]*?)```", text)
    if not m:
        return False
    return bool(re.search(r"^\s*class\s+P\d+\s+\w+\s*$", m.group(1), re.MULTILINE))


def insert_phase_status_table(text: str, phases: list[tuple[int, str, str]]) -> str:
    """Insert `## Phase Status` table immediately after the `## Phase Flow`
    block (the whole mermaid fence). Returns updated text."""
    # Find end of Phase Flow section (next ## heading or EOF).
    flow_match = re.search(r"(?m)^## Phase Flow\s*$", text)
    if not flow_match:
        return text
    after_flow = text[flow_match.end():]
    next_heading = re.search(r"(?m)^## ", after_flow)
    insert_at = flow_match.end() + (next_heading.start() if next_heading else len(after_flow))

    rows = ["| Phase | Status |", "|---|---|"]
    for num, _heading, state in sorted(phases, key=lambda p: p[0]):
        rows.append(f"| Phase {num} | {state} |")
    table = "\n## Phase Status\n" + "\n".join(rows) + "\n\n"
    return text[:insert_at].rstrip() + "\n\n" + table + text[insert_at:].lstrip("\n")


def insert_mermaid_class_lines(text: str, phases: list[tuple[int, str, str]]) -> str:
    """Append `class P# state` directives at the bottom of the first
    ```mermaid``` block."""
    m = re.search(r"```mermaid\s*\n([\s\S]*?)```", text)
    if not m:
        return text
    body = m.group(1).rstrip()
    additions = [f"    class P{num} {state}" for num, _h, state in sorted(phases, key=lambda p: p[0])]
    new_body = body + "\n\n" + "\n".join(additions) + "\n"
    return text[:m.start()] + "```mermaid\n" + new_body + "```" + text[m.end():]


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: python migrate_lifecycle.py <path-to-plan.md>", file=sys.stderr)
        sys.exit(2)
    plan = Path(sys.argv[1]).resolve()
    if not plan.exists():
        print(f"plan not found: {plan}", file=sys.stderr)
        sys.exit(1)

    original = plan.read_text(encoding="utf-8")
    phases = collect_phases(original)
    if not phases:
        print(f"no phases found in {plan}; nothing to migrate")
        return

    text = original
    added: list[str] = []

    if not has_phase_status_table(text):
        text = insert_phase_status_table(text, phases)
        added.append("Phase Status table")

    if not has_mermaid_class_lines(text):
        text = insert_mermaid_class_lines(text, phases)
        added.append("Mermaid class lines")

    if not added:
        print(f"already current-format (Phase Status + Mermaid class present): {plan}")
        return

    plan.write_bytes(text.encode("utf-8"))
    states = ", ".join(f"P{n}={s}" for n, _h, s in phases)
    print(f"updated {plan}")
    print(f"  added: {', '.join(added)}")
    print(f"  states: {states}")


if __name__ == "__main__":
    main()
