#!/usr/bin/env python3
"""
Inspect a target project directory and emit JSON describing its stack so the
deploy script can fill template placeholders.

Output JSON shape:
{
  "project_name": "...",
  "stack": "dotnet|typescript|python|go|generic",
  "stack_summary": "human-readable one-liner",
  "build_cmd": "...",
  "test_cmd": "...",
  "lint_cmd": "...",      # may be ""
  "plan_path": "docs/implementation-plan.md",
  "conventions_file": "conventions/dotnet.md"
}
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def find_first(root: Path, names: list[str]) -> Path | None:
    """Return the first file in `names` that exists under `root` (non-recursive)."""
    for name in names:
        p = root / name
        if p.exists():
            return p
    return None


def detect_stack(root: Path) -> dict:
    project_name = root.name

    # Identify the language by signature files at the root.
    csproj = list(root.glob("*.csproj")) + list(root.glob("*.sln")) + list(root.glob("*.slnx"))
    package_json = root / "package.json"
    pyproject = root / "pyproject.toml"
    requirements = root / "requirements.txt"
    go_mod = root / "go.mod"
    cargo = root / "Cargo.toml"

    # Default
    info = {
        "project_name": project_name,
        "stack": "generic",
        "stack_summary": "Unknown stack",
        "build_cmd": "<add build command>",
        "test_cmd": "<add test command>",
        "lint_cmd": "",
        "plan_path": "docs/implementation-plan.md",
        "conventions_file": "conventions/generic.md",
    }

    if csproj:
        sln = next((p for p in csproj if p.suffix in {".sln", ".slnx"}), None)
        sln_name = sln.name if sln else None
        info.update(
            stack="dotnet",
            stack_summary=".NET (C#) — solution: " + (sln_name or "<add sln name>"),
            build_cmd=f"dotnet build {sln_name}" if sln_name else "dotnet build",
            test_cmd=f"dotnet test {sln_name}" if sln_name else "dotnet test",
            conventions_file="conventions/dotnet.md",
        )
    elif package_json.exists():
        # Look at scripts to pick build/test/lint
        try:
            pkg = json.loads(package_json.read_text(encoding="utf-8"))
        except Exception:
            pkg = {}
        scripts = pkg.get("scripts", {}) if isinstance(pkg, dict) else {}
        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})} if isinstance(pkg, dict) else {}
        stack_bits = []
        if "next" in deps:
            stack_bits.append("Next.js")
        if "react" in deps and "next" not in deps:
            stack_bits.append("React")
        if "typescript" in deps:
            stack_bits.append("TypeScript")
        else:
            stack_bits.append("Node.js")
        info.update(
            stack="typescript" if "typescript" in deps else "node",
            stack_summary=" / ".join(stack_bits),
            build_cmd="npm run build" if "build" in scripts else "<add build command>",
            test_cmd="npm test" if "test" in scripts else "<add test command>",
            lint_cmd="npm run lint" if "lint" in scripts else "",
            conventions_file="conventions/typescript.md",
        )
    elif pyproject.exists() or requirements.exists():
        info.update(
            stack="python",
            stack_summary="Python",
            build_cmd="python -m build" if pyproject.exists() else "<add build command>",
            test_cmd="pytest",
            lint_cmd="ruff check .",
            conventions_file="conventions/python.md",
        )
    elif go_mod.exists():
        info.update(
            stack="go",
            stack_summary="Go",
            build_cmd="go build ./...",
            test_cmd="go test ./...",
            lint_cmd="go vet ./...",
            conventions_file="conventions/go.md",
        )
    elif cargo.exists():
        info.update(
            stack="rust",
            stack_summary="Rust",
            build_cmd="cargo build",
            test_cmd="cargo test",
            lint_cmd="cargo clippy",
            conventions_file="conventions/generic.md",  # no dedicated template yet
        )

    # Detect plan path — first match wins
    candidates = [
        "docs/implementation-plan.md",
        "docs/implementation_plan.md",
        "Docs/implementation-plan.md",
        "Docs/implementation_plan.md",
        "docs/IMPLEMENTATION_PLAN.md",
    ]
    for c in candidates:
        if (root / c).exists():
            info["plan_path"] = c
            break

    return info


def main() -> int:
    ap = argparse.ArgumentParser(description="Detect stack of a target project.")
    ap.add_argument("target", help="Path to the target project root.")
    args = ap.parse_args()

    root = Path(args.target).resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2

    info = detect_stack(root)
    print(json.dumps(info, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
