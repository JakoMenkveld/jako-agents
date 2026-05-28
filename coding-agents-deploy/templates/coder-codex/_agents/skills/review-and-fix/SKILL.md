---
name: review-and-fix
description: Create a new {{project_name}} implementation plan, or audit and repair an existing one at {{plan_path}}. Auto-fixes structural gaps against the canonical layout expected by implement-phase and review-implementation, and reviews section content – flagging unfilled placeholders, vague or non-verifiable items, and internal inconsistencies as advisory findings without rewriting your prose.
---

# Review and Fix

Use `.agents/commands/review-and-fix.md` as the canonical workflow. Read it before creating or repairing the plan, then follow it exactly.

Auto-fix mode is the default when `{{plan_path}}` exists. The skill silently fills missing structural sections (Phase Flow, Recommended Execution Order, Automation Contract, Definition of Done, Files to Create or Modify by Phase, Test Plan, Decisions, Open Questions, Residual Risks, per-phase Work and Acceptance Criteria blocks) with placeholder content the user fills in afterwards. A legacy `## Files to Create by Phase` heading is renamed in place to `## Files to Create or Modify by Phase`. It never touches existing non-placeholder content, status markers, or `## Open Questions` entries (append-only, user-owned), and never rewrites or reorders the `## Decisions` content (free-form and live – maintained by the user and `/review-implementation`, not this skill). It never flags either section as a defect when it is empty or just notes there are none.

Beyond the structural audit, the skill also reviews the **content** of the sections that exist: it surfaces unfilled placeholders, vague or non-actionable work items, non-verifiable acceptance criteria, and internal inconsistencies (e.g. Phase Flow nodes that don't match the actual phases) as advisory findings. Content review is report-only – the skill flags the gaps and the user fills them in; it never rewrites the user's prose.

Create mode runs when no plan file exists. It asks the user for a summary and a rough phase list, then writes a compliant skeleton.
