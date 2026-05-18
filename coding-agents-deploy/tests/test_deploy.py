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
            "# Coding-agent conventions - Alpha\n"
            "\n"
            "## Project\n"
            "Template project guidance.\n"
            "\n"
            "## Build\n"
            "Template build guidance.\n"
        )
        existing = (
            "# Coding-agent conventions - Alpha\n"
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
            Path(".deployed-agents/conventions.md"),
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
            Path(".deployed-agents/conventions.md"),
            rendered_template,
            existing,
            interactive=False,
            template_updates="always",
            summary=summary,
        )

        self.assertIsNotNone(template_update)
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "templates" / "common" / "_deployed-agents" / "conventions.md"
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


class GitignoreTests(unittest.TestCase):
    @staticmethod
    def _git(repo: Path, *args: str) -> None:
        import subprocess
        subprocess.run(["git", "-C", str(repo), *args], check=True,
                        capture_output=True, text=True)

    def _repo(self, tmp: str) -> Path:
        repo = Path(tmp)
        self._git(repo, "init")
        self._git(repo, "config", "user.email", "t@t")
        self._git(repo, "config", "user.name", "t")
        return repo

    def test_new_scaffolding_is_ignored_tracked_files_are_not(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._repo(tmp)
            # A scaffolding file the project deliberately committed stays visible.
            (repo / ".deployed-agents").mkdir(parents=True)
            (repo / ".deployed-agents/conventions.md").write_text(
                "# pre-existing\n", encoding="utf-8")
            self._git(repo, "add", ".deployed-agents/conventions.md")
            self._git(repo, "commit", "-m", "init")

            rels = [Path(".deployed-agents/conventions.md"),
                    Path(".deployed-agents/suggestions.md"),
                    Path(".claude/agents/review-iterate.md")]
            snapshot = deploy.snapshot_gitignore_state(repo, repo, rels)
            (repo / ".deployed-agents/suggestions.md").write_text("x\n", encoding="utf-8")
            (repo / ".claude/agents").mkdir(parents=True)
            (repo / ".claude/agents/review-iterate.md").write_text("x\n", encoding="utf-8")

            summary: list[str] = []
            deploy.update_gitignore(repo, repo, rels, snapshot,
                                    dry_run=False, summary=summary)
            gi = (repo / ".gitignore").read_text(encoding="utf-8")

            self.assertNotIn("/.deployed-agents/conventions.md", gi)   # tracked → stays visible
            self.assertIn("/.deployed-agents/suggestions.md", gi)      # new scaffolding → ignored
            self.assertIn("/.claude/agents/review-iterate.md", gi)
            self.assertIn(deploy.GITIGNORE_BEGIN, gi)

    def test_managed_block_is_idempotent_and_self_healing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._repo(tmp)
            rels = [Path(".claude/commands/implement-phase.md")]
            snap = deploy.snapshot_gitignore_state(repo, repo, rels)

            s1: list[str] = []
            deploy.update_gitignore(repo, repo, rels, snap, False, s1)
            first = (repo / ".gitignore").read_text(encoding="utf-8")

            s2: list[str] = []
            deploy.update_gitignore(repo, repo, rels, snap, False, s2)
            self.assertEqual(first, (repo / ".gitignore").read_text(encoding="utf-8"))
            self.assertTrue(any("GITIGNORE OK" in line for line in s2))

            # User wipes the managed block; a later deploy must restore it.
            (repo / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
            s3: list[str] = []
            deploy.update_gitignore(repo, repo, rels, snap, False, s3)
            healed = (repo / ".gitignore").read_text(encoding="utf-8")
            self.assertIn("node_modules/", healed)
            self.assertIn("/.claude/commands/implement-phase.md", healed)


class TrackedWorkflowTests(unittest.TestCase):
    SKILL_ROOT = Path(__file__).resolve().parents[1]

    def test_is_tracked_workflow_matches_commit_and_sync_both_sides(self) -> None:
        for rel in (
            Path(".claude/commands/commit-and-sync.md"),
            Path(".agents/commands/commit-and-sync.md"),
            Path(".agents/skills/commit-and-sync/SKILL.md"),
            Path(".agents/skills/commit-and-sync/agents/openai.yaml"),
        ):
            self.assertTrue(deploy.is_tracked_workflow(rel), rel)
        for rel in (
            Path(".claude/commands/implement-phase.md"),
            Path(".agents/commands/review-and-fix.md"),
            Path(".deployed-agents/conventions.md"),
        ):
            self.assertFalse(deploy.is_tracked_workflow(rel), rel)

    def test_commit_and_sync_excluded_from_gitignore_candidates_every_role(self) -> None:
        for role in ("claude-codes", "codex-codes", "both"):
            rels = deploy.gitignore_candidate_rels(self.SKILL_ROOT, role)
            self.assertTrue(rels, role)
            self.assertFalse(
                any("commit-and-sync" in rel.as_posix() for rel in rels),
                f"commit-and-sync leaked into gitignore candidates for {role}",
            )
            # Other scaffolding is still ignored.
            self.assertTrue(
                any(rel.name == "implement-phase.md" for rel in rels), role
            )

    def test_claude_commit_and_sync_deployed_for_every_role(self) -> None:
        common_claude = (
            self.SKILL_ROOT
            / "templates" / "common" / "_claude" / "commands" / "commit-and-sync.md"
        )
        self.assertTrue(common_claude.is_file())
        # The redundant coder-claude copy is gone (common covers claude-codes too).
        stale = (
            self.SKILL_ROOT
            / "templates" / "coder-claude" / "_claude" / "commands" / "commit-and-sync.md"
        )
        self.assertFalse(stale.exists())


if __name__ == "__main__":
    unittest.main()
