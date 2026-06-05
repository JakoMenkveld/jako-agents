---
name: write-spec
description: Write a precise, verifiable specification for {{project_name}} as a single markdown document with small, focused mermaid diagrams. Use when the user wants to spec a feature, endpoint, component, data model, or behavior change ("write a spec for X", "spec out Y", "draft a specification"). The produced doc keeps prose for intent and rationale, and pins every behavioral requirement to a machine-checkable assertion (precondition -> action -> postcondition) with a lifecycle status and a concrete way to verify it.
---

# Write Spec

Use `.agents/commands/write-spec.md` as the canonical workflow. Read it before writing the specification, then follow it exactly.

Keep prose for intent and rationale only; express every behavioral requirement as a single Boolean assertion (precondition -> action -> observable postcondition) pinned to a concrete verification, with a `draft` / `specified` / `verified` lifecycle status. Use small, single-purpose mermaid diagrams, state explicit non-goals, and leave genuinely undecided points in Open Questions rather than guessing.
