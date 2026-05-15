#!/usr/bin/env python3
"""
Deploy the coding-agent template tree into a target project.

Usage:
    python deploy.py --target <path> --role <claude-codes|codex-codes|both>
                     [--dry-run] [--no-backup]

What it does:
  1. Runs detect_stack on the target.
  2. Reads conventions/<stack>.md and substitutes it into {{conventions_block}}.
  3. Walks templates/common/ and templates/coder-<role>/ (or both).
  4. For each template file, renders {{placeholders}} and writes to the target.
     If the target file already exists, it is moved to <path>.bak.<timestamp>
     before being replaced (unless --no-backup).
  5. Prints a tree of what changed plus a final one-line summary.

Placeholder syntax: {{var}} (no spaces, no jinja conditionals).
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROLES = {"claude-codes", "codex-codes", "both"}
SUB_RE = re.compile(r"\{\{\s*([a-z_][a-z0-9_]*)\s*\}\}", re.IGNORECASE)


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
        "key_paths": ", ".join(info["key_paths"]) if info["key_paths"] else "(none detected)",
        "conventions_block": conventions_block,
    }


def render(text: str, subs: dict[str, str]) -> str:
    def sub_fn(m: re.Match[str]) -> str:
        key = m.group(1).lower()
        return subs.get(key, m.group(0))
    return SUB_RE.sub(sub_fn, text)


def timestamp() -> str:
    return _dt.datetime.now().strftime("%Y%m%d-%H%M%S")


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


def iter_template_files(root: Path):
    """Yield (relative_path_in_target, absolute_path_in_template) for every file under root."""
    for p in sorted(root.rglob("*")):
        if p.is_file():
            rel = p.relative_to(root)
            yield translate_path(rel), p


def deploy_tree(template_root: Path, target: Path, subs: dict[str, str],
                dry_run: bool, no_backup: bool, summary: list[str]) -> None:
    """Render every file under template_root into target."""
    if not template_root.is_dir():
        return
    for rel, abs_src in iter_template_files(template_root):
        dest = target / rel
        text = abs_src.read_text(encoding="utf-8")
        rendered = render(text, subs)

        if dest.exists():
            if no_backup:
                action = "OVERWRITE"
            else:
                backup = dest.with_suffix(dest.suffix + f".bak.{timestamp()}")
                action = f"REPLACE  (backup: {backup.name})"
                if not dry_run:
                    shutil.move(str(dest), str(backup))
        else:
            action = "CREATE"

        summary.append(f"  {action:<35} {rel}")

        if not dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(rendered, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Deploy coding agents into a target project.")
    ap.add_argument("--target", required=True, help="Target project path.")
    ap.add_argument("--role", required=True, choices=sorted(ROLES),
                    help="Role assignment.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print what would happen; write nothing.")
    ap.add_argument("--no-backup", action="store_true",
                    help="Overwrite without backing up existing files.")
    args = ap.parse_args()

    target = Path(args.target).resolve()
    if not target.is_dir():
        print(f"error: {target} is not a directory", file=sys.stderr)
        return 2

    skill_root = Path(__file__).resolve().parent.parent

    info = load_detection(target, skill_root)
    conventions_block = load_conventions(skill_root, info)
    subs = build_substitutions(info, conventions_block)

    print(f"Target:         {target}")
    print(f"Role:           {args.role}")
    print(f"Stack:          {info['stack']} — {info['stack_summary']}")
    print(f"Build command:  {info['build_cmd']}")
    print(f"Test command:   {info['test_cmd']}")
    print(f"Plan path:      {info['plan_path']}")
    print(f"Dry run:        {args.dry_run}")
    print()

    summary: list[str] = []

    deploy_tree(skill_root / "templates" / "common", target, subs,
                args.dry_run, args.no_backup, summary)

    role_dirs = []
    if args.role in ("claude-codes", "both"):
        role_dirs.append("coder-claude")
    if args.role in ("codex-codes", "both"):
        role_dirs.append("coder-codex")
    for d in role_dirs:
        deploy_tree(skill_root / "templates" / d, target, subs,
                    args.dry_run, args.no_backup, summary)

    print("File operations:")
    if summary:
        for line in summary:
            print(line)
    else:
        print("  (no files written)")
    print()
    verb = "Would deploy" if args.dry_run else "Deployed"
    print(f"{verb} {len(summary)} files to {target}")
    if not args.dry_run and not args.no_backup:
        print("Existing files were backed up with .bak.<timestamp> suffix; review with `git status`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
