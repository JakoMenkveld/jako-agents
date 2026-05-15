---
name: implement-fixes
description: Apply a list of findings to {{project_name}}, review with review-iterate, iterate until clean, then commit locally. Use when the user invokes implement-fixes with a findings list.
---

# Implement Fixes

Use `.agents/commands/implement-fixes.md` as the canonical workflow. Read it before applying fixes, then follow it exactly, including its local commit policy.

Keep documentation read-only. If a fix exposes plan or supporting-doc drift, collect the required update and surface it in the final `Documentation Required` section.
