from __future__ import annotations

import contextlib
import io
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


DEPLOY_PATH = Path(__file__).resolve().parents[1] / "scripts" / "deploy.py"
SPEC = importlib.util.spec_from_file_location("deploy", DEPLOY_PATH)
assert SPEC is not None
deploy = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = deploy
SPEC.loader.exec_module(deploy)


class MergeMarkdownTests(unittest.TestCase):
    def test_project_only_section_stays_near_original_neighbor(self) -> None:
        rendered_template = (
            "# AGENTS.md - Alpha\n"
            "\n"
            "## Project\n"
            "Template project guidance.\n"
            "\n"
            "## Build\n"
            "Template build guidance.\n"
        )
        existing = (
            "# AGENTS.md - Alpha\n"
            "\n"
            "## Project\n"
            "Project-specific guidance.\n"
            "\n"
            "### Local Notes\n"
            "Keep this local section near Project.\n"
            "\n"
            "## Build\n"
            "Template build guidance.\n"
        )
        summary: list[str] = []

        merged, template_update = deploy.merge_markdown(
            Path("AGENTS.md"),
            rendered_template,
            existing,
            interactive=False,
            template_updates="never",
            summary=summary,
        )

        self.assertIsNone(template_update)
        self.assertIn("Project-specific guidance.", merged)
        self.assertLess(merged.index("## Project"), merged.index("### Local Notes"))
        self.assertLess(merged.index("### Local Notes"), merged.index("## Build"))
        self.assertIn(
            "Project-only section ### Local Notes: kept in project",
            "\n".join(summary),
        )

    def test_interactive_conflict_can_choose_template_version(self) -> None:
        rendered_template = "# Command\n\n## Workflow\nUse the template workflow.\n"
        existing = "# Command\n\n## Workflow\nUse the project workflow.\n"
        summary: list[str] = []

        with (
            patch("builtins.input", return_value="t"),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            merged, template_update = deploy.merge_markdown(
                Path(".agents/commands/example.md"),
                rendered_template,
                existing,
                interactive=True,
                template_updates="never",
                summary=summary,
            )

        self.assertIsNone(template_update)
        self.assertIn("Use the template workflow.", merged)
        self.assertNotIn("Use the project workflow.", merged)
        self.assertIn("Conflict at ## Workflow: used template version", "\n".join(summary))

    def test_promoted_project_idea_is_unrendered_before_template_write(self) -> None:
        subs = {
            "project_name": "Alpha",
            "stack_summary": "Python",
            "build_cmd": "python -m build",
            "test_cmd": "pytest",
            "lint_cmd": "ruff check .",
            "plan_path": "docs/implementation-plan.md",
            "conventions_block": "Use Python conventions.",
        }
        template_text = "# {{project_name}}\n\n## Project\nTemplate guidance.\n"
        rendered_template = deploy.render(template_text, subs)
        existing = (
            rendered_template
            + "\n"
            + "## New Idea\n"
            + "Use the {{project_name}} cache path only in docs.\n"
            + "Alpha should enable remote cache.\n"
        )
        summary: list[str] = []

        _merged, template_update = deploy.merge_markdown(
            Path("AGENTS.md"),
            rendered_template,
            existing,
            interactive=False,
            template_updates="always",
            summary=summary,
        )

        self.assertIsNotNone(template_update)
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "templates" / "common" / "AGENTS.md"
            src.parent.mkdir(parents=True)
            src.write_text(template_text, encoding="utf-8")
            deploy.write_template_update(src, template_update, subs, dry_run=False, summary=summary)
            updated_template = src.read_text(encoding="utf-8")

        self.assertIn("{{project_name}} should enable remote cache.", updated_template)
        self.assertIn("Use the {{project_name}} cache path only in docs.", updated_template)


class PlanRepairTests(unittest.TestCase):
    def test_repair_plan_handles_multiple_phases_and_preserves_tail_sections(self) -> None:
        info = {
            "project_name": "Alpha",
            "build_cmd": "npm run build",
            "test_cmd": "npm test",
        }
        original = (
            "# Existing Plan\n"
            "\n"
            "Existing summary.\n"
            "\n"
            "## Phase 0: Setup\n"
            "Design narrative.\n"
            "\n"
            "### Work\n"
            "- Existing setup work.\n"
            "\n"
            "## Phase 1: Build\n"
            "Build narrative.\n"
            "\n"
            "## Open Questions\n"
            "1. Keep this question exactly.\n"
            "\n"
            "## Custom Notes\n"
            "Keep this tail section.\n"
        )

        repaired, changes = deploy.repair_plan_text(original, info)

        self.assertIn("## Phase Flow", repaired)
        self.assertIn("## Recommended Execution Order", repaired)
        self.assertIn("## Automation Contract", repaired)
        self.assertIn("## Definition of Done", repaired)
        self.assertIn("## Files to Create by Phase", repaired)
        self.assertIn("## Test Plan", repaired)
        self.assertIn("### Phase 0", repaired)
        self.assertIn("### Phase 1", repaired)
        self.assertIn("1. Keep this question exactly.", repaired)
        self.assertIn("## Custom Notes\nKeep this tail section.", repaired)
        self.assertLess(
            repaired.index("### Acceptance Criteria", repaired.index("## Phase 1")),
            repaired.index("## Open Questions"),
        )
        self.assertNotIn(
            "### Acceptance Criteria\n- (List acceptance criteria for this phase.)\n\n## Custom Notes",
            repaired,
        )
        self.assertIn("Added ### Acceptance Criteria under Phase 1", changes)


if __name__ == "__main__":
    unittest.main()
