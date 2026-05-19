---
name: review-and-fix
description: Create a new {{project_name}} implementation plan or audit-and-auto-fix the structure of an existing one at {{plan_path}}. Ensures the plan matches the canonical layout expected by implement-phase and review-implementation.
---

# Review and Fix

Use `.agents/commands/review-and-fix.md` as the canonical workflow. Read it before creating or repairing the plan, then follow it exactly.

Auto-fix mode is the default when `{{plan_path}}` exists. The skill silently fills missing structural sections (Phase Flow, Recommended Execution Order, Automation Contract, Definition of Done, Files to Create or Modify by Phase, Test Plan, Decisions, Open Questions, Residual Risks, per-phase Work and Acceptance Criteria blocks) with placeholder content the user fills in afterwards. A legacy `## Files to Create by Phase` heading is renamed in place to `## Files to Create or Modify by Phase`. It never touches existing non-placeholder content, status markers, or `## Open Questions` entries (append-only, user-owned), and never rewrites or reorders the `## Decisions` content (free-form and live – maintained by the user and `/review-implementation`, not this skill). It never flags either section as a defect when it is empty or just notes there are none.

Create mode runs when no plan file exists. It asks the user for a summary and a rough phase list, then writes a compliant skeleton.
