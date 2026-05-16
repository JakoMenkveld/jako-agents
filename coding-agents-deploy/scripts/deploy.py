#!/usr/bin/env python3
"""
Deploy the coding-agent template tree into a target project.

Usage:
    python deploy.py --target <path> --role <claude-codes|codex-codes|both>
                     [--dry-run] [--no-backup] [--merge-existing]
                     [--template-updates ask|never|always]
                     [--interactive auto|always|never] [--skip-plan]

What it does:
  1. Runs detect_stack on the target.
  2. Reads conventions/<stack>.md and substitutes it into {{conventions_block}}.
  3. Walks templates/common/ and templates/coder-<role>/ (or both).
  4. For each template file, renders {{placeholders}} and writes to the target.
     If --merge-existing is supplied, Markdown files are merged by heading so
     project-only sections are preserved and conflicts can be resolved by the
     user. Otherwise existing files are moved to <path>.bak.<timestamp> before
     being replaced (unless --no-backup).
  5. Ensures the implementation plan exists and has the canonical structural
     sections, backing up an existing plan before changing it.
  6. Prints a tree of what changed plus a final one-line summary.

Placeholder syntax: {{var}} (no spaces, no jinja conditionals).
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import datetime as _dt
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROLES = {"claude-codes", "codex-codes", "both"}
SUB_RE = re.compile(r"\{\{\s*([a-z_][a-z0-9_]*)\s*\}\}", re.IGNORECASE)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
PHASE_RE = re.compile(
    r"^##\s+Phase\s+(\d+)(?:\s*[:\-\u2013\u2014]\s*(.*?))?\s*$",
    re.IGNORECASE | re.MULTILINE,
)
MANAGED_TOP_LEVEL_FILES = {Path("AGENTS.md"), Path("CLAUDE.md")}
GITIGNORE_BEGIN = "# >>> coding-agents (managed by deploy.py) — do not edit inside this block >>>"
GITIGNORE_END = "# <<< coding-agents (managed by deploy.py) <<<"


@dataclass
class MarkdownBlock:
    key: str
    label: str
    text: str


@dataclass
class Phase:
    number: int
    title: str
    start: int
    end: int = 0


def load_detection(target: Path, skill_root: Path) -> dict:
    """Run detect_stack.py and return its JSON output as a dict."""
    detect = skill_root / "scripts" / "detect_stack.py"
    result = subprocess.run(
        [sys.executable, str(detect), str(target)],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def load_conventions(skill_root: Path, info: dict) -> str:
    """Load the per-stack conventions text. Falls back to generic.md."""
    path = skill_root / info["conventions_file"]
    if not path.exists():
        path = skill_root / "conventions" / "generic.md"
    return path.read_text(encoding="utf-8") if path.exists() else ""


def build_substitutions(info: dict, conventions_block: str) -> dict[str, str]:
    return {
        "project_name": info["project_name"],
        "stack_summary": info["stack_summary"],
        "build_cmd": info["build_cmd"],
        "test_cmd": info["test_cmd"],
        "lint_cmd": info["lint_cmd"] or "",
        "plan_path": info["plan_path"],
        "conventions_block": conventions_block,
    }


def render(text: str, subs: dict[str, str]) -> str:
    def sub_fn(m: re.Match[str]) -> str:
        key = m.group(1).lower()
        return subs.get(key, m.group(0))
    return SUB_RE.sub(sub_fn, text)


def unrender(text: str, subs: dict[str, str]) -> str:
    """Best-effort conversion from project-rendered text back to template text."""
    result = text
    for key, value in sorted(subs.items(), key=lambda item: len(item[1]), reverse=True):
        if value:
            result = result.replace(value, "{{" + key + "}}")
    return result


def timestamp() -> str:
    return _dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def backup_path(path: Path) -> Path:
    return Path(str(path) + f".bak.{timestamp()}")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def backup_existing(path: Path, dry_run: bool, no_backup: bool) -> str | None:
    if no_backup or not path.exists():
        return None
    backup = backup_path(path)
    if not dry_run:
        shutil.move(str(path), str(backup))
    return backup.name


def resolve_interactive(mode: str) -> bool:
    if mode == "always":
        return True
    if mode == "never":
        return False
    return sys.stdin.isatty()


def ask_choice(prompt: str, choices: dict[str, str], default: str, interactive: bool) -> str:
    if not interactive:
        return default

    choice_list = "/".join(
        key.upper() if key == default else key for key in choices
    )
    while True:
        print()
        print(prompt)
        for key, label in choices.items():
            suffix = " (default)" if key == default else ""
            print(f"  {key}: {label}{suffix}")
        answer = input(f"Choose [{choice_list}]: ").strip().lower()
        if not answer:
            return default
        if answer in choices:
            return answer
        print(f"Please choose one of: {', '.join(choices)}")


def should_promote(prompt: str, template_updates: str, interactive: bool) -> bool:
    if template_updates == "always":
        return True
    if template_updates == "never":
        return False
    return ask_choice(
        prompt,
        {"y": "promote to the source template", "n": "keep only in this project"},
        "n",
        interactive,
    ) == "y"


def translate_path(rel: Path) -> Path:
    """Translate placeholder dir names in the template tree to the real target names.

    The template tree uses `_claude` and `_agents` because the harness blocks
    writing source files inside literal `.claude` / `.agents` directories. On
    deploy we rewrite the path back to the conventional dotted names.
    """
    parts = []
    for p in rel.parts:
        if p == "_claude":
            parts.append(".claude")
        elif p == "_agents":
            parts.append(".agents")
        else:
            parts.append(p)
    return Path(*parts)


def reverse_translate_path(rel: Path) -> Path:
    parts = []
    for p in rel.parts:
        if p == ".claude":
            parts.append("_claude")
        elif p == ".agents":
            parts.append("_agents")
        else:
            parts.append(p)
    return Path(*parts)


def iter_template_files(root: Path):
    """Yield (relative_path_in_target, absolute_path_in_template) for every file under root."""
    for p in sorted(root.rglob("*")):
        if p.is_file():
            rel = p.relative_to(root)
            yield translate_path(rel), p


def normalize_heading(title: str) -> str:
    title = title.strip().lower()
    title = re.sub(r"\s+", " ", title)
    return title


def normalize_text_for_compare(text: str) -> str:
    lines = [line.rstrip() for line in text.strip().splitlines()]
    return "\n".join(lines).strip()


def split_heading_body(block: str) -> tuple[str, str]:
    lines = block.splitlines(keepends=True)
    if lines and HEADING_RE.match(lines[0].rstrip("\r\n")):
        return lines[0], "".join(lines[1:])
    return "", block


def parse_markdown_blocks(text: str) -> list[MarkdownBlock]:
    """Split Markdown into comparable heading blocks.

    This intentionally treats each heading as its own block, regardless of
    nesting depth. That keeps merge decisions small and preserves the original
    order when blocks are joined again.
    """
    lines = text.splitlines(keepends=True)
    blocks: list[MarkdownBlock] = []
    idx = 0

    if lines and lines[0].strip() == "---":
        for end in range(1, len(lines)):
            if lines[end].strip() == "---":
                blocks.append(
                    MarkdownBlock("frontmatter", "frontmatter", "".join(lines[: end + 1]))
                )
                idx = end + 1
                break

    start = idx
    counts: dict[tuple[int, str], int] = {}

    def emit(end: int) -> None:
        nonlocal start
        if end <= start:
            return
        chunk = "".join(lines[start:end])
        first = lines[start].rstrip("\r\n") if start < len(lines) else ""
        match = HEADING_RE.match(first)
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            norm = normalize_heading(title)
            count = counts.get((level, norm), 0)
            counts[(level, norm)] = count + 1
            key = f"h{level}:{norm}:{count}"
            label = f"{match.group(1)} {title}"
        else:
            key = f"preamble:{len(blocks)}"
            label = "preamble"
        blocks.append(MarkdownBlock(key, label, chunk))
        start = end

    while idx < len(lines):
        if HEADING_RE.match(lines[idx].rstrip("\r\n")):
            emit(idx)
            start = idx
        idx += 1
    emit(len(lines))
    return blocks


def join_blocks(blocks: list[str]) -> str:
    text = "".join(blocks)
    if text and not text.endswith("\n"):
        text += "\n"
    return text


def merge_markdown(
    rel: Path,
    rendered_template: str,
    existing: str,
    interactive: bool,
    template_updates: str,
    summary: list[str],
) -> tuple[str, str | None]:
    """Merge a rendered Markdown template with an existing project file.

    Returns (project_text, promoted_template_text). promoted_template_text is
    rendered text and must still be passed through unrender() before writing to
    the source template.
    """
    template_blocks = parse_markdown_blocks(rendered_template)
    existing_blocks = parse_markdown_blocks(existing)
    existing_by_key = {block.key: block for block in existing_blocks}
    existing_index_by_key = {block.key: idx for idx, block in enumerate(existing_blocks)}
    template_keys = {block.key for block in template_blocks}
    project_parts: list[str] = []
    template_parts: list[str] = []
    template_changed = False
    cursor = 0

    def append_project_only_range(start: int, end: int) -> None:
        nonlocal template_changed
        for project_block in existing_blocks[start:end]:
            if project_block.key in template_keys:
                continue
            if not normalize_text_for_compare(project_block.text):
                continue
            project_parts.append(project_block.text)
            promote = should_promote(
                f"Project-only section {project_block.label} exists in {rel}. Add it to the source template?",
                template_updates,
                interactive,
            )
            detail = "kept in project"
            if promote:
                detail += "; promoted to template"
            summary.append(f"    - Project-only section {project_block.label}: {detail}")
            if promote:
                template_parts.append(project_block.text)
                template_changed = True

    for block in template_blocks:
        match_idx = existing_index_by_key.get(block.key)
        if match_idx is not None:
            append_project_only_range(cursor, match_idx)
            cursor = max(cursor, match_idx + 1)

        other = existing_by_key.get(block.key)
        if other is None:
            project_parts.append(block.text)
            template_parts.append(block.text)
            continue

        if normalize_text_for_compare(block.text) == normalize_text_for_compare(other.text):
            project_parts.append(block.text)
            template_parts.append(block.text)
            continue

        decision = ask_choice(
            f"Conflict in {rel} at {block.label}.",
            {
                "p": "keep the project version",
                "t": "use the source template version",
                "a": "use the template and append the project body",
            },
            "p",
            interactive,
        )

        promote = False
        if decision in {"p", "a"}:
            promote = should_promote(
                f"Promote the project version of {block.label} in {rel} into the source template?",
                template_updates,
                interactive,
            )

        if decision == "t":
            summary.append(f"    - Conflict at {block.label}: used template version")
            project_parts.append(block.text)
            template_parts.append(block.text)
        elif decision == "a":
            _heading, body = split_heading_body(other.text)
            appended = block.text
            if body.strip():
                if appended and not appended.endswith("\n"):
                    appended += "\n"
                appended += "\n" + body.lstrip("\n")
            detail = "used template and appended project body"
            if promote:
                detail += "; promoted to template"
            summary.append(f"    - Conflict at {block.label}: {detail}")
            project_parts.append(appended)
            template_parts.append(appended if promote else block.text)
            template_changed = template_changed or promote
        else:
            detail = "kept project version"
            if promote:
                detail += "; promoted to template"
            summary.append(f"    - Conflict at {block.label}: {detail}")
            project_parts.append(other.text)
            template_parts.append(other.text if promote else block.text)
            template_changed = template_changed or promote

    append_project_only_range(cursor, len(existing_blocks))

    return join_blocks(project_parts), join_blocks(template_parts) if template_changed else None


def merge_plain_text(
    rel: Path,
    rendered_template: str,
    existing: str,
    interactive: bool,
    template_updates: str,
    summary: list[str],
) -> tuple[str, str | None]:
    decision = ask_choice(
        f"Existing non-Markdown file differs from template: {rel}.",
        {
            "p": "keep the project file",
            "t": "use the source template file",
        },
        "p",
        interactive,
    )
    if decision == "t":
        summary.append("    - Non-Markdown conflict: used template file")
        return rendered_template, None

    promote = should_promote(
        f"Promote the project version of {rel} into the source template?",
        template_updates,
        interactive,
    )
    detail = "kept project file"
    if promote:
        detail += "; promoted to template"
    summary.append(f"    - Non-Markdown conflict: {detail}")
    return existing, existing if promote else None


def write_template_update(
    src: Path,
    rendered_template_text: str,
    subs: dict[str, str],
    dry_run: bool,
    summary: list[str],
) -> None:
    template_text = unrender(rendered_template_text, subs)
    if normalize_text_for_compare(read_text(src)) == normalize_text_for_compare(template_text):
        return
    summary.append(f"  {'UPDATE TEMPLATE':<35} {src.relative_to(src.parents[2])}")
    if not dry_run:
        write_text(src, template_text)


def write_project_file(
    dest: Path,
    rel: Path,
    text: str,
    action: str,
    dry_run: bool,
    no_backup: bool,
    summary: list[str],
) -> None:
    if dest.exists() and normalize_text_for_compare(read_text(dest)) == normalize_text_for_compare(text):
        summary.append(f"  {'UNCHANGED':<35} {rel}")
        return

    backup_name = backup_existing(dest, dry_run, no_backup)
    if backup_name:
        action = f"{action}  (backup: {backup_name})"

    summary.append(f"  {action:<35} {rel}")
    if not dry_run:
        write_text(dest, text)


def deploy_tree(template_root: Path, target: Path, subs: dict[str, str],
                dry_run: bool, no_backup: bool, merge_existing: bool,
                interactive: bool, template_updates: str,
                summary: list[str], rendered_rels: set[Path]) -> None:
    """Render every file under template_root into target."""
    if not template_root.is_dir():
        return
    for rel, abs_src in iter_template_files(template_root):
        rendered_rels.add(rel)
        dest = target / rel
        text = read_text(abs_src)
        rendered = render(text, subs)

        if not dest.exists():
            summary.append(f"  {'CREATE':<35} {rel}")
            if not dry_run:
                write_text(dest, rendered)
            continue

        if not merge_existing:
            write_project_file(dest, rel, rendered, "REPLACE", dry_run, no_backup, summary)
            continue

        existing = read_text(dest)
        if normalize_text_for_compare(existing) == normalize_text_for_compare(rendered):
            summary.append(f"  {'UNCHANGED':<35} {rel}")
            continue

        if rel.suffix.lower() == ".md":
            merged, template_update = merge_markdown(
                rel, rendered, existing, interactive, template_updates, summary
            )
        else:
            merged, template_update = merge_plain_text(
                rel, rendered, existing, interactive, template_updates, summary
            )

        if template_update is not None:
            write_template_update(abs_src, template_update, subs, dry_run, summary)
            rendered = render(read_text(abs_src), subs) if not dry_run else template_update
            if normalize_text_for_compare(rendered) != normalize_text_for_compare(merged):
                # The project may keep local-only sections that were not promoted.
                rendered = merged
        else:
            rendered = merged

        write_project_file(dest, rel, rendered, "MERGE", dry_run, no_backup, summary)


def iter_managed_project_files(target: Path) -> list[Path]:
    files: list[Path] = []
    for rel in sorted(MANAGED_TOP_LEVEL_FILES):
        if (target / rel).is_file():
            files.append(rel)
    for root_name in (".claude", ".agents"):
        root = target / root_name
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file() and ".bak." not in path.name:
                files.append(path.relative_to(target))
    return files


def choose_template_root_for_project_file(skill_root: Path, role: str, rel: Path) -> Path:
    if rel in MANAGED_TOP_LEVEL_FILES or rel == Path(".claude/settings.json"):
        return skill_root / "templates" / "common"
    first = rel.parts[0] if rel.parts else ""
    if first == ".claude":
        role_dir = "coder-claude" if role in {"claude-codes", "both"} else "coder-codex"
        return skill_root / "templates" / role_dir
    if first == ".agents":
        role_dir = "coder-codex" if role in {"codex-codes", "both"} else "coder-claude"
        return skill_root / "templates" / role_dir
    return skill_root / "templates" / "common"


def promote_project_only_files(
    target: Path,
    skill_root: Path,
    role: str,
    subs: dict[str, str],
    rendered_rels: set[Path],
    dry_run: bool,
    interactive: bool,
    template_updates: str,
    summary: list[str],
) -> None:
    for rel in iter_managed_project_files(target):
        if rel in rendered_rels:
            continue
        summary.append(f"  {'KEEP PROJECT-ONLY':<35} {rel}")
        promote = should_promote(
            f"Project-only file {rel} is not in the selected templates. Add it to the source templates?",
            template_updates,
            interactive,
        )
        if not promote:
            continue
        src_root = choose_template_root_for_project_file(skill_root, role, rel)
        src_rel = reverse_translate_path(rel)
        src = src_root / src_rel
        try:
            source_text = unrender(read_text(target / rel), subs)
        except UnicodeDecodeError:
            summary.append(f"  {'SKIP BINARY TEMPLATE':<35} {rel}")
            continue
        summary.append(f"  {'CREATE TEMPLATE':<35} {src.relative_to(skill_root)}")
        if not dry_run:
            write_text(src, source_text)


def has_top_section(text: str, title: str) -> bool:
    pattern = re.compile(rf"^##\s+{re.escape(title)}\s*$", re.IGNORECASE | re.MULTILINE)
    return bool(pattern.search(text))


def find_top_section_bounds(text: str, title: str) -> tuple[int, int] | None:
    pattern = re.compile(rf"^##\s+{re.escape(title)}\s*$", re.IGNORECASE | re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return None
    next_section = re.search(r"^##\s+", text[match.end() :], re.MULTILINE)
    end = match.end() + next_section.start() if next_section else len(text)
    return match.start(), end


def parse_phases(text: str) -> list[Phase]:
    matches = list(PHASE_RE.finditer(text))
    phases: list[Phase] = []
    for match in matches:
        title = (match.group(2) or "Untitled").strip()
        title = re.sub(r"\s+(?:✅|⚠️|⚠).*$", "", title).strip() or "Untitled"
        next_top_heading = re.search(r"^##\s+", text[match.end() :], re.MULTILINE)
        end = match.end() + next_top_heading.start() if next_top_heading else len(text)
        phases.append(Phase(int(match.group(1)), title, match.start(), end))
    return phases


def phase_flow_block(phases: list[Phase]) -> str:
    lines = ["## Phase Flow", "```mermaid", "flowchart TD"]
    ordered = sorted(phases, key=lambda p: p.number)
    if not ordered:
        lines.append("    P0[Phase 0: Initial implementation]")
    elif len(ordered) == 1:
        p = ordered[0]
        lines.append(f"    P{p.number}[Phase {p.number}: {p.title}]")
    else:
        for left, right in zip(ordered, ordered[1:]):
            lines.append(
                f"    P{left.number}[Phase {left.number}: {left.title}] "
                f"--> P{right.number}[Phase {right.number}: {right.title}]"
            )
    lines.extend(["```", ""])
    return "\n".join(lines)


def execution_order_block(phases: list[Phase]) -> str:
    lines = ["## Recommended Execution Order"]
    for idx, phase in enumerate(sorted(phases, key=lambda p: p.number), start=1):
        lines.append(f"{idx}. Phase {phase.number}: {phase.title}")
    if len(lines) == 1:
        lines.append("1. Phase 0: Initial implementation")
    lines.append("")
    return "\n".join(lines)


def plan_tail_block(title: str, body: str) -> str:
    return f"## {title}\n{body.rstrip()}\n\n"


def starter_phase_block() -> str:
    return (
        "## Phase 0: Initial implementation\n"
        "\n"
        "### Work\n"
        "- (List work items for this phase.)\n"
        "\n"
        "### Acceptance Criteria\n"
        "- (List acceptance criteria for this phase.)\n"
        "\n"
    )


def plan_skeleton(info: dict) -> str:
    project_name = info["project_name"]
    return (
        f"# {project_name} Implementation Plan\n"
        "\n"
        f"This is a starter implementation plan for {project_name}. Replace the placeholder bullets with the real scope before running an implementation command.\n"
        "\n"
        "## Phase Flow\n"
        "```mermaid\n"
        "flowchart TD\n"
        "    P0[Phase 0: Initial implementation]\n"
        "```\n"
        "\n"
        "## Recommended Execution Order\n"
        "1. Phase 0: Initial implementation\n"
        "\n"
        "## Automation Contract\n"
        f"- Build command: `{info['build_cmd']}`\n"
        f"- Test command: `{info['test_cmd']}`\n"
        "- (Document CI, environment, and secret assumptions here.)\n"
        "\n"
        "## Definition of Done\n"
        "- (List the exit criteria for the whole plan.)\n"
        "\n"
        + starter_phase_block()
        + "## Files to Create by Phase\n"
        "### Phase 0\n"
        "- (List files this phase creates.)\n"
        "\n"
        "## Test Plan\n"
        "### Phase 0\n"
        "- (List tests this phase ships or unblocks.)\n"
        "\n"
        "## Open Questions\n"
        "\n"
        "## Residual Risks\n"
    )


def insert_before_first_phase_or_append(text: str, block: str) -> str:
    first_phase = PHASE_RE.search(text)
    if first_phase:
        return text[: first_phase.start()] + block + text[first_phase.start() :]
    return text.rstrip() + "\n\n" + block


def ensure_phase_subsections(text: str) -> tuple[str, list[str]]:
    changes: list[str] = []
    phases = parse_phases(text)
    for phase in reversed(phases):
        block = text[phase.start : phase.end]
        updated = block
        if not re.search(r"^###\s+Work\s*$", updated, re.IGNORECASE | re.MULTILINE):
            line_end = updated.find("\n") + 1
            if line_end <= 0:
                line_end = len(updated)
            updated = (
                updated[:line_end]
                + "\n### Work\n- (List work items for this phase.)\n"
                + updated[line_end:]
            )
            changes.append(f"Added ### Work under Phase {phase.number}")
        if not re.search(
            r"^###\s+Acceptance Criteria\s*$",
            updated,
            re.IGNORECASE | re.MULTILINE,
        ):
            work_match = re.search(r"^###\s+Work\s*$", updated, re.IGNORECASE | re.MULTILINE)
            if work_match:
                next_heading = re.search(r"^###\s+", updated[work_match.end() :], re.MULTILINE)
                insert_at = (
                    work_match.end() + next_heading.start()
                    if next_heading
                    else len(updated)
                )
            else:
                insert_at = updated.find("\n") + 1
            updated = (
                updated[:insert_at].rstrip()
                + "\n\n### Acceptance Criteria\n- (List acceptance criteria for this phase.)\n"
                + updated[insert_at:]
            )
            changes.append(f"Added ### Acceptance Criteria under Phase {phase.number}")
        if updated != block:
            text = text[: phase.start] + updated + text[phase.end :]
    return text, changes


def ensure_phase_subblocks(
    text: str,
    section_title: str,
    phases: list[Phase],
    placeholder: str,
) -> tuple[str, list[str]]:
    changes: list[str] = []
    bounds = find_top_section_bounds(text, section_title)
    if not bounds:
        return text, changes

    start, end = bounds
    section = text[start:end]
    additions: list[str] = []
    for phase in sorted(phases, key=lambda p: p.number):
        if not re.search(
            rf"^###\s+Phase\s+{phase.number}\b",
            section,
            re.IGNORECASE | re.MULTILINE,
        ):
            additions.append(f"### Phase {phase.number}\n- {placeholder}\n")
            changes.append(f"Added ### Phase {phase.number} under ## {section_title}")
    if not additions:
        return text, changes
    insertion = "\n" + "\n".join(additions)
    return text[:end].rstrip() + insertion + "\n" + text[end:], changes


def repair_plan_text(text: str, info: dict) -> tuple[str, list[str]]:
    changes: list[str] = []
    if not text.strip():
        return plan_skeleton(info), ["Created starter plan"]

    if not re.match(r"\s*#\s+", text):
        text = f"# {info['project_name']} Implementation Plan\n\n" + text.lstrip()
        changes.append("Added top-level title")

    phases = parse_phases(text)
    if not phases:
        text = text.rstrip() + "\n\n" + starter_phase_block()
        changes.append("Added Phase 0 starter section")
        phases = parse_phases(text)

    pre_phase_blocks: list[str] = []
    if not has_top_section(text, "Phase Flow"):
        pre_phase_blocks.append(phase_flow_block(phases))
        changes.append("Added ## Phase Flow")
    if not has_top_section(text, "Recommended Execution Order"):
        pre_phase_blocks.append(execution_order_block(phases))
        changes.append("Added ## Recommended Execution Order")
    if not has_top_section(text, "Automation Contract"):
        pre_phase_blocks.append(
            plan_tail_block(
                "Automation Contract",
                "- (Document build, test, CI, environment, and secret assumptions here.)",
            )
        )
        changes.append("Added ## Automation Contract")
    if not has_top_section(text, "Definition of Done"):
        pre_phase_blocks.append(
            plan_tail_block(
                "Definition of Done",
                "- (List the exit criteria for the whole plan.)",
            )
        )
        changes.append("Added ## Definition of Done")
    if pre_phase_blocks:
        text = insert_before_first_phase_or_append(text, "\n".join(pre_phase_blocks))

    text, subsection_changes = ensure_phase_subsections(text)
    changes.extend(subsection_changes)
    phases = parse_phases(text)

    if not has_top_section(text, "Files to Create by Phase"):
        body = "".join(
            f"### Phase {phase.number}\n- (List files this phase creates.)\n\n"
            for phase in sorted(phases, key=lambda p: p.number)
        )
        text = text.rstrip() + "\n\n" + plan_tail_block("Files to Create by Phase", body)
        changes.append("Added ## Files to Create by Phase")
    if not has_top_section(text, "Test Plan"):
        body = "".join(
            f"### Phase {phase.number}\n- (List tests this phase ships or unblocks.)\n\n"
            for phase in sorted(phases, key=lambda p: p.number)
        )
        text = text.rstrip() + "\n\n" + plan_tail_block("Test Plan", body)
        changes.append("Added ## Test Plan")
    if not has_top_section(text, "Open Questions"):
        text = text.rstrip() + "\n\n## Open Questions\n"
        changes.append("Added ## Open Questions")
    if not has_top_section(text, "Residual Risks"):
        text = text.rstrip() + "\n\n## Residual Risks\n"
        changes.append("Added ## Residual Risks")

    phases = parse_phases(text)
    text, subblock_changes = ensure_phase_subblocks(
        text,
        "Files to Create by Phase",
        phases,
        "(List files this phase creates.)",
    )
    changes.extend(subblock_changes)
    text, subblock_changes = ensure_phase_subblocks(
        text,
        "Test Plan",
        phases,
        "(List tests this phase ships or unblocks.)",
    )
    changes.extend(subblock_changes)

    if text and not text.endswith("\n"):
        text += "\n"
    return text, changes


def ensure_plan_file(
    target: Path,
    info: dict,
    dry_run: bool,
    no_backup: bool,
    summary: list[str],
) -> None:
    rel = Path(info["plan_path"])
    path = target / rel
    if not path.exists():
        summary.append(f"  {'CREATE PLAN':<35} {rel}")
        if not dry_run:
            write_text(path, plan_skeleton(info))
        return

    original = read_text(path)
    repaired, changes = repair_plan_text(original, info)
    if normalize_text_for_compare(original) == normalize_text_for_compare(repaired):
        summary.append(f"  {'PLAN OK':<35} {rel}")
        return

    backup_name = backup_existing(path, dry_run, no_backup)
    action = "REPAIR PLAN"
    if backup_name:
        action = f"{action}  (backup: {backup_name})"
    summary.append(f"  {action:<35} {rel}")
    for change in changes:
        summary.append(f"    - {change}")
    if not dry_run:
        write_text(path, repaired)


def git_repo_root(target: Path) -> Path | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(target), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return None
    root = result.stdout.strip()
    return Path(root).resolve() if root else None


def git_path_tracked(repo_root: Path, abs_path: Path) -> bool:
    """True when git already has this path in the index/HEAD — i.e. the project
    deliberately version-controls it (it "existed previously and was not gitignored",
    and was committed). Untracked paths are deploy scaffolding."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "ls-files", "--error-unmatch", "--", str(abs_path)],
            capture_output=True, text=True,
        )
    except (FileNotFoundError, OSError):
        return False
    return result.returncode == 0


def gitignore_candidate_rels(skill_root: Path, role: str) -> list[Path]:
    """Translated target-relative paths the deploy writes that are agent scaffolding:
    everything under `.claude/` or `.agents/`, plus `AGENTS.md` / `CLAUDE.md`. The
    implementation plan and other project docs are intentionally excluded — they stay
    tracked."""
    roots = [skill_root / "templates" / "common"]
    if role in ("claude-codes", "both"):
        roots.append(skill_root / "templates" / "coder-claude")
    if role in ("codex-codes", "both"):
        roots.append(skill_root / "templates" / "coder-codex")
    rels: set[Path] = set()
    for root in roots:
        if not root.is_dir():
            continue
        for rel, _abs in iter_template_files(root):
            top = rel.parts[0] if rel.parts else ""
            if top in (".claude", ".agents") or rel in MANAGED_TOP_LEVEL_FILES:
                rels.add(rel)
    return sorted(rels)


def snapshot_gitignore_state(
    target: Path, repo_root: Path, rels: list[Path]
) -> dict[Path, bool]:
    """Capture, BEFORE any file is written, whether git already tracks each path.
    A tracked path is one the project version-controls on purpose — it must stay
    visible (never auto-ignored), regardless of what the deploy writes over it."""
    return {rel: git_path_tracked(repo_root, target / rel) for rel in rels}


def _strip_managed_block(text: str) -> str:
    if GITIGNORE_BEGIN not in text:
        return text
    start = text.index(GITIGNORE_BEGIN)
    end_marker = text.find(GITIGNORE_END)
    head = text[:start].rstrip("\n")
    if end_marker == -1:
        return (head + "\n") if head else ""
    rest = text[end_marker + len(GITIGNORE_END):]
    rest = rest[1:] if rest.startswith("\n") else rest
    if head and rest.strip():
        return head + "\n\n" + rest.lstrip("\n")
    if head:
        return head + "\n"
    return rest.lstrip("\n")


def update_gitignore(
    target: Path,
    repo_root: Path,
    rels: list[Path],
    snapshot: dict[Path, bool],
    dry_run: bool,
    summary: list[str],
) -> None:
    """Add deployed scaffolding paths to the repo-root `.gitignore` inside a managed
    block. A path is skipped when git already tracked it before this deploy — the
    project version-controls it on purpose, so it stays visible."""
    to_ignore: list[str] = []
    for rel in rels:
        if snapshot.get(rel, False):  # already git-tracked → leave it alone
            continue
        abs_path = (target / rel).resolve()
        try:
            pattern = "/" + abs_path.relative_to(repo_root).as_posix()
        except ValueError:
            continue
        to_ignore.append(pattern)
    to_ignore = sorted(set(to_ignore))

    gitignore_path = repo_root / ".gitignore"
    original = read_text(gitignore_path) if gitignore_path.exists() else ""
    stripped = _strip_managed_block(original)

    if to_ignore:
        block = "\n".join([GITIGNORE_BEGIN, *to_ignore, GITIGNORE_END]) + "\n"
        base = stripped.rstrip("\n")
        new_text = (base + "\n\n" if base else "") + block
    else:
        new_text = stripped if stripped.strip() else ""

    if normalize_text_for_compare(new_text) == normalize_text_for_compare(original):
        summary.append(f"  {'GITIGNORE OK':<35} .gitignore")
        return

    label = "GITIGNORE" if to_ignore else "GITIGNORE (cleared block)"
    detail = f" (+{len(to_ignore)} managed entries)" if to_ignore else ""
    summary.append(f"  {label:<35} .gitignore{detail}")
    if not dry_run:
        write_text(gitignore_path, new_text)


def main() -> int:
    ap = argparse.ArgumentParser(description="Deploy coding agents into a target project.")
    ap.add_argument("--target", required=True, help="Target project path.")
    ap.add_argument("--role", required=True, choices=sorted(ROLES),
                    help="Role assignment.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print what would happen; write nothing.")
    ap.add_argument("--no-backup", action="store_true",
                    help="Overwrite without backing up existing files.")
    ap.add_argument("--merge-existing", action="store_true",
                    help="Merge existing managed Markdown files instead of replacing them.")
    ap.add_argument("--template-updates", choices=("ask", "never", "always"), default="ask",
                    help="Whether project-only additions can update this skill's templates.")
    ap.add_argument("--interactive", choices=("auto", "always", "never"), default="auto",
                    help="Prompt for merge conflicts and template-promotion decisions.")
    ap.add_argument("--skip-plan", action="store_true",
                    help="Do not create or repair the detected implementation plan.")
    ap.add_argument("--no-gitignore", action="store_true",
                    help="Do not add deployed agent scaffolding to the repo .gitignore.")
    args = ap.parse_args()

    target = Path(args.target).resolve()
    if not target.is_dir():
        print(f"error: {target} is not a directory", file=sys.stderr)
        return 2

    skill_root = Path(__file__).resolve().parent.parent

    info = load_detection(target, skill_root)
    conventions_block = load_conventions(skill_root, info)
    subs = build_substitutions(info, conventions_block)
    interactive = resolve_interactive(args.interactive)

    print(f"Target:         {target}")
    print(f"Role:           {args.role}")
    print(f"Stack:          {info['stack']} — {info['stack_summary']}")
    print(f"Build command:  {info['build_cmd']}")
    print(f"Test command:   {info['test_cmd']}")
    print(f"Plan path:      {info['plan_path']}")
    print(f"Merge existing: {args.merge_existing}")
    print(f"Interactive:    {interactive}")
    print(f"Template edits: {args.template_updates}")
    print(f"Dry run:        {args.dry_run}")
    print()

    summary: list[str] = []
    rendered_rels: set[Path] = set()

    # Snapshot git state BEFORE any files are written so we can tell which deployed
    # paths are pre-existing tracked project files vs. new scaffolding.
    repo_root: Path | None = None
    gi_rels: list[Path] = []
    gi_snapshot: dict[Path, bool] = {}
    if not args.no_gitignore:
        repo_root = git_repo_root(target)
        if repo_root is not None:
            gi_rels = gitignore_candidate_rels(skill_root, args.role)
            gi_snapshot = snapshot_gitignore_state(target, repo_root, gi_rels)

    deploy_tree(skill_root / "templates" / "common", target, subs,
                args.dry_run, args.no_backup, args.merge_existing,
                interactive, args.template_updates, summary, rendered_rels)

    role_dirs = []
    if args.role in ("claude-codes", "both"):
        role_dirs.append("coder-claude")
    if args.role in ("codex-codes", "both"):
        role_dirs.append("coder-codex")
    for d in role_dirs:
        deploy_tree(skill_root / "templates" / d, target, subs,
                    args.dry_run, args.no_backup, args.merge_existing,
                    interactive, args.template_updates, summary, rendered_rels)

    if args.merge_existing:
        promote_project_only_files(
            target,
            skill_root,
            args.role,
            subs,
            rendered_rels,
            args.dry_run,
            interactive,
            args.template_updates,
            summary,
        )

    if not args.skip_plan:
        ensure_plan_file(target, info, args.dry_run, args.no_backup, summary)

    if not args.no_gitignore:
        if repo_root is None:
            summary.append(f"  {'GITIGNORE SKIPPED (not a git repo)':<35} {target}")
        else:
            update_gitignore(target, repo_root, gi_rels, gi_snapshot,
                             args.dry_run, summary)

    print("File operations:")
    if summary:
        for line in summary:
            print(line)
    else:
        print("  (no files written)")
    print()
    verb = "Would deploy" if args.dry_run else "Deployed"
    print(f"{verb} {len(summary)} operations for {target}")
    if not args.dry_run and not args.no_backup:
        print("Existing files were backed up with .bak.<timestamp> suffix; review with `git status`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
