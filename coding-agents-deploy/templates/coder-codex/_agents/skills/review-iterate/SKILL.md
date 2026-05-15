---
name: review-iterate
description: Read-only review of one or more {{project_name}} implementation phases against {{plan_path}} and the current solution. Use for phase reviews, plan-drift reporting, or when the user invokes review-iterate.
---

# Review Iterate

Use `.agents/agents/review-iterate.md` as the canonical review workflow. Read it before reviewing a phase or phase range, then follow it exactly.

Stay read-only. Inspect code, diffs, docs, build output, and test output, but do not edit files or documentation, including `{{plan_path}}`.

Keep output concise. Report documentation changes as required user actions instead of suggesting that implementation agents edit docs.
