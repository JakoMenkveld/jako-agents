#!/usr/bin/env python3
"""pack.py – refresh the embedded assets inside bake.py.

bake.py is the single self-contained script that ships to deployed projects.
It embeds the renderer JS, both stylesheets, and the HTML template as Python
string constants between `# >>> PACK <file> >>>` / `# <<< PACK <file> <<<`
marker lines. This script rewrites those marker blocks in place from the
sibling source files. Edit the source files (index.html, renderer.js,
styles.css, black-silver.css), then run this once to refresh bake.py.

Usage:
    python pack.py
"""

from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent

# (filename next to pack.py, name of the Python constant in bake.py)
ASSETS: list[tuple[str, str]] = [
    ("index.html",       "INDEX_HTML"),
    ("renderer.js",      "RENDERER_JS"),
    ("styles.css",       "STYLES_CSS"),
    ("black-silver.css", "BLACK_SILVER_CSS"),
]


def pack_block(filename: str, var: str, body: str, src: str) -> str:
    """Replace the lines between the `# >>> PACK <filename> >>>` and
    `# <<< PACK <filename> <<<` markers with a single `<var> = <repr(body)>`
    assignment. Markers themselves are preserved verbatim."""
    pattern = re.compile(
        rf"(# >>> PACK {re.escape(filename)} >>>\n)(.*?)(# <<< PACK {re.escape(filename)} <<<\n)",
        re.DOTALL,
    )
    new_body = f"{var} = {body!r}\n"
    replacement = lambda m: m.group(1) + new_body + m.group(3)
    new_src, n = pattern.subn(replacement, src)
    if n == 0:
        raise SystemExit(f"pack.py: no marker block found for {filename!r} in bake.py")
    if n > 1:
        raise SystemExit(f"pack.py: multiple marker blocks for {filename!r} in bake.py")
    return new_src


def main() -> None:
    bake_path = HERE / "bake.py"
    src = bake_path.read_text(encoding="utf-8")

    total = 0
    for filename, var in ASSETS:
        asset_path = HERE / filename
        if not asset_path.exists():
            raise SystemExit(f"pack.py: missing source asset {asset_path}")
        body = asset_path.read_text(encoding="utf-8")
        src = pack_block(filename, var, body, src)
        total += len(body)

    bake_path.write_bytes(src.encode("utf-8"))
    print(f"packed bake.py: {total} chars across {len(ASSETS)} assets")


if __name__ == "__main__":
    main()
