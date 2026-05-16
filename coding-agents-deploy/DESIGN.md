# deploy-coding-agents Design

Canonical reference for the current `deploy-coding-agents` skill. This document describes the files the skill owns, the role model it deploys, the rendering contract, and the plan structure its workflows expect.

## Purpose

`deploy-coding-agents` installs a coordinated Claude + Codex coding-agent setup into a target project. Given a target path and role assignment, it renders or merges:

- `AGENTS.md`
- `CLAUDE.md`
- `.claude/` commands, agents, and settings
- `.agents/` commands, agents, skills, and skill manifests

The rendered output is tailored with detected stack information, build/test commands, the implementation-plan path, and stack-specific conventions.

When the target already has agent files, merge-aware deploys preserve project-only content, ask the user how to resolve same-section conflicts when interactive, and can promote reusable project ideas back into this repository's source templates before the target project is updated.

## Source Layout

```text
C:\vsprojects\jako-agents\
  README.md
  coding-agents-deploy\
    SKILL.md
    README.md
    DESIGN.md
    install.ps1
    scripts\
      detect_stack.py
      deploy.py
    templates\
      common\
        AGENTS.md
        CLAUDE.md
        _claude\settings.json
      coder-claude\
        _claude\agents\review-iterate.md
        _claude\commands\commit-and-sync.md
        _claude\commands\implement-fixes.md
        _claude\commands\implement-phase.md
        _claude\commands\review-and-fix.md
        _agents\skills\review-and-fix\
        _agents\skills\review-implementation\
      coder-codex\
        _agents\agents\review-iterate.md
        _agents\commands\commit-and-sync.md
        _agents\commands\implement-fixes.md
        _agents\commands\implement-phase.md
        _agents\commands\review-and-fix.md
        _agents\skills\commit-and-sync\
        _agents\skills\implement-fixes\
        _agents\skills\implement-phase\
        _agents\skills\review-and-fix\
        _agents\skills\review-iterate\
        _claude\commands\review-and-fix.md
        _claude\commands\review-implementation.md
    conventions\
      dotnet.md
      generic.md
      go.md
      python.md
      typescript.md
```

## Template Path Translation

Template directories named `_claude` and `_agents` deploy as `.claude` and `.agents`. `scripts/deploy.py` translates those path segments while writing files to the target project. The generated project never receives `_claude` or `_agents` paths.

## Role Model

The setup has two lanes: Claude and Codex. The coding lane gets the rich implementation workflow and an inner read-only reviewer. The non-coding lane gets the outer review entry point.

| Role | Coder lane | Reviewer lane |
|------|------------|---------------|
| `claude-codes` | `.claude/commands/{implement-phase,implement-fixes,commit-and-sync,review-and-fix}.md` and `.claude/agents/review-iterate.md` | `.agents/skills/{review-implementation,review-and-fix}/` |
| `codex-codes` | `.agents/commands/{implement-phase,implement-fixes,commit-and-sync,review-and-fix}.md`, `.agents/agents/review-iterate.md`, and `.agents/skills/<command>/` shims | `.claude/commands/{review-implementation,review-and-fix}.md` |
| `both` | Union of both coder lanes | Union of both reviewer lanes |

`review-and-fix` is present in both lanes for every role because plan creation and plan repair are shared operations.

## Deployed Workflows

| Workflow | Lane | Purpose |
|----------|------|---------|
| `implement-phase` | Coder only | Implement one or more plan phases, run the inner review loop, and commit locally. |
| `implement-fixes` | Coder only | Apply user-provided findings, run the inner review loop, and commit locally. |
| `commit-and-sync` | Coder only | Commit working-tree changes, push, and optionally create a semver release or explicit tag. |
| `review-iterate` | Coder inner reviewer | Read-only critical reviewer used inside implementation loops. Claude uses Sonnet; Codex uses `gpt-5.5` with medium reasoning effort. |
| `review-implementation` | Outer reviewer | Review one or more implementation phases, update plan status markers within its narrow write policy, and commit the review locally. |
| `review-and-fix` | Both lanes | Create a canonical implementation plan or repair structural gaps in an existing one. |

`AGENTS.md` is the shared instruction source. `CLAUDE.md` inherits it with `@AGENTS.md`.

## Deployment Flow

1. `SKILL.md` is invoked by a deployment request and resolves the target path and role.
2. `scripts/detect_stack.py <target>` emits stack, command, plan-path, and conventions metadata as JSON.
3. `scripts/deploy.py --target <path> --role <role>` loads that metadata and the selected conventions file.
4. The deploy script renders `templates/common/` plus the selected role template tree.
5. Placeholders in the form `{{var}}` are replaced with detected values.
6. Existing destination files are handled according to mode:
   - Default mode: move the existing destination to `<filename>.bak.<YYYYMMDD-HHMMSS>` unless `--no-backup` is supplied, then replace it.
   - `--merge-existing`: merge Markdown files by heading, preserve project-only sections, ask about conflicts when interactive, and optionally promote reusable project additions into `templates/`.
7. The deploy ensures the detected implementation plan exists unless `--skip-plan` is supplied. Missing plans get a starter canonical skeleton. Existing plans are backed up before structural repair unless `--no-backup` is supplied.
8. `--dry-run` prints the file operations without writing.

## Merge Contract

`scripts/deploy.py --merge-existing` is conservative:

- Existing project-only Markdown sections are preserved in the project.
- Same-heading conflicts default to the project version when non-interactive.
- Interactive conflicts ask whether to keep the project version, use the template version, or append the project body after the template body.
- Project-only sections/files and project-side conflict resolutions are promoted into source templates only when `--template-updates always` is supplied or the user answers yes under `--template-updates ask`.
- Non-Markdown conflicts are not structurally merged; the user chooses project or template when interactive, and non-interactive merge mode keeps the project file.
- Promoted content is best-effort "unrendered" by replacing current substitution values with `{{...}}` placeholders before writing under `templates/`.

## Substitution Variables

| Variable | Source | Example |
|----------|--------|---------|
| `{{project_name}}` | Target folder name | `drydoc` |
| `{{stack_summary}}` | Detector inference | `.NET (C#) - solution: DryDoc.slnx` |
| `{{build_cmd}}` | Detector inference | `dotnet build DryDoc.slnx` |
| `{{test_cmd}}` | Detector inference | `dotnet test DryDoc.slnx` |
| `{{lint_cmd}}` | Detector inference, may be empty | `npm run lint` |
| `{{plan_path}}` | First matching plan path, or default | `docs/implementation-plan.md` |
| `{{conventions_block}}` | Full text of `conventions/<stack>.md` | Multi-line markdown block |

## Stack Detection

`detect_stack.py` inspects the target root for signature files:

- `*.csproj`, `*.sln`, or `*.slnx` -> `dotnet`, using `conventions/dotnet.md`
- `package.json` -> `typescript` when TypeScript is installed, otherwise `node`, using `conventions/typescript.md`
- `pyproject.toml` or `requirements.txt` -> `python`, using `conventions/python.md`
- `go.mod` -> `go`, using `conventions/go.md`
- `Cargo.toml` -> `rust`, using `conventions/generic.md`
- No known signature -> `generic`, using `conventions/generic.md`

Plan path search order:

1. `docs/implementation-plan.md`
2. `docs/implementation_plan.md`
3. `Docs/implementation-plan.md`
4. `Docs/implementation_plan.md`
5. `docs/IMPLEMENTATION_PLAN.md`

If no candidate exists, the default is `docs/implementation-plan.md`. The detector does not guess source, test, or documentation directories; agents discover project layout by scanning the target project during their workflows.

## Behavior Contract

The deployed workflows share these rules:

- Severity levels are `BLOCKER`, `MAJOR`, `MINOR`, `NIT`, and `DOC`; reviewers may also tag shared-library suggestions with `[SHARED]`.
- Inner reviewers are read-only and do not edit files.
- Workflows survey git state before making or reviewing changes, including untracked files.
- Untracked implementation files are part of the review surface.
- Dirty worktrees are preserved; unrelated user changes are not reverted.
- Implementers read the target phase before coding and stop for user clarification when the phase contains unresolved ambiguity.
- Implementation loops have a three-cycle reviewer iteration cap.
- Repeated feedback for the same `file:line` is treated as priority work before unrelated cleanup.
- `git diff --check` is a standard verification step.
- Passing tests are necessary but not sufficient; reviewers check that tests prove the relevant acceptance criteria.
- Generic agents do not edit plan status markers. `review-implementation` is the explicit exception and may update markers under its plan write policy.
- `## Open Questions` is append-only. Existing entries are not edited, reordered, resolved, or removed by the agents.
- Final review output is terse and focused on outstanding work.

## Plan Contract

`review-and-fix` creates and repairs plans to this canonical structure:

```text
# <Project Name> Implementation Plan
<summary paragraph>

## Phase Flow
<mermaid flowchart>

## Recommended Execution Order
<numbered phase list>

## Automation Contract
<build/test/CI assumptions>

## Definition of Done
<overall exit criteria>

## Phase N: <Title>
<optional design narrative>

### Work
<bullets>

### Acceptance Criteria
<bullets>

## Files to Create by Phase
### Phase N
<bullets>

## Test Plan
### Phase N
<bullets>

## Open Questions
<numbered list, append-only>

## Residual Risks
<bullets>
```

Phase headings use `## Phase N: <Title>` as the canonical form. Phase numbering is contiguous. `review-and-fix` may add missing structural sections with placeholders, normalize supported style issues, and create a new skeleton plan. It does not rewrite existing non-placeholder content, status markers, or existing `## Open Questions` entries.

The deploy script also enforces a minimum plan skeleton:

- If no file exists at `{{plan_path}}`, deploy creates a starter implementation plan with one placeholder phase.
- If a plan exists, deploy repairs missing structural sections and per-phase `### Work` / `### Acceptance Criteria` blocks, preserving existing content.
- Existing plans are backed up before repair unless `--no-backup` is supplied.

Status markers are written by `review-implementation`:

- `✅` means complete.
- `⚠️` or `⚠` means partial and includes a concise bracketed reason.
- No marker means not started, not reviewed, or not status-marked yet.

## Frontmatter Conventions

Claude commands in `.claude/commands/X.md`:

```yaml
---
description: <prose summary including trigger phrases>
aliases: [shortname1, shortname2]
---
```

Claude agents in `.claude/agents/X.md`:

```yaml
---
name: X
description: <prose summary>
tools: Read, Glob, Grep, Bash
model: sonnet
---
```

Codex agents in `.agents/agents/X.md`:

```yaml
---
name: X
description: <prose summary>
model: gpt-5.5
reasoning_effort: medium
---
```

Codex skills in `.agents/skills/X/SKILL.md`:

```yaml
---
name: X
description: <prose summary including trigger phrases>
---
```

Codex skill manifests in `.agents/skills/X/agents/openai.yaml`:

```yaml
interface:
  display_name: "<Human Name>"
  short_description: "<one-liner>"
  default_prompt: "/X"
```
