---
name: publish-to-source
description: Share your work with the team by merging the current branch into its source branch as one squashed commit, stripping the coding-agent overlay so teammates get your code but never your agent setup. Use when the user wants to share/publish their personal-branch changes to the team without leaking agent files.
---

# Publish to Source

Use `.agents/commands/publish-to-source.md` as the canonical workflow. Read it before touching any branch, then follow it exactly.

Require a clean working tree first (the user runs `/commit-and-sync` before this). Never publish the agent overlay (`.claude/`, `.agents/`, `.deployed-agents/`, and the plan-renderer runtime artifacts). Do not force-push, do not skip hooks, and always return the user to their original branch when done.
