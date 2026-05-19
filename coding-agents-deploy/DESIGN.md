# deploy-coding-agents Design

Canonical reference for the current `deploy-coding-agents` skill. This document describes the files the skill owns, the role model it deploys, the rendering contract, and the plan structure its workflows expect.

## Purpose

`deploy-coding-agents` installs a coordinated Claude + Codex coding-agent setup into a target project as a **non-invasive overlay**. Given a target path and role assignment, it renders or merges:

- `.deployed-agents/conventions.md` — the single source of truth for the deployed agents
- `.claude/` commands and agents
- `.agents/` commands, agents, skills, and skill manifests

It deliberately writes **no** root-level files, and **no settings/config files**. The project's own `AGENTS.md` / `CLAUDE.md` are never read, written, backed up, or merged, and Claude/Codex settings (`.claude/settings*.json`, anything under `.codex/`) are never created, replaced, merged, promoted, or `.gitignore`-managed — they are owned by the user and project and left exactly as found. The overlay sits entirely within its own gitignored scaffolding dirs. Conventions are workflow-scoped (loaded when a deployed command runs) rather than ambient, which is the explicit trade-off for not touching the developer's setup.

The rendered output is tailored with detected stack information, build/test commands, the implementation-plan path, and stack-specific conventions.

When the target already has *deployed* agent files (e.g. a prior `.deployed-agents/conventions.md`), merge-aware deploys preserve project-only content, ask the user how to resolve same-section conflicts when interactive, and can promote reusable project ideas back into this repository's source templates before the target project is updated.

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
        _deployed-agents\conventions.md
        _claude\commands\commit-and-sync.md
      coder-claude\
        _claude\agents\review-iterate.md
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

Template directories named `_claude`, `_agents`, and `_deployed-agents` deploy as `.claude`, `.agents`, and `.deployed-agents`. `scripts/deploy.py` translates those path segments while writing files to the target project. The generated project never receives the underscore-prefixed paths.

## Role Model

The setup has two lanes: Claude and Codex. The coding lane gets the rich implementation workflow and an inner read-only reviewer. The non-coding lane gets the outer review entry point.

| Role | Coder lane | Reviewer lane |
|------|------------|---------------|
| `claude-codes` | `.claude/commands/{implement-phase,implement-fixes,review-and-fix}.md` and `.claude/agents/review-iterate.md` | `.agents/skills/{review-implementation,archive-plan,review-and-fix}/` |
| `codex-codes` | `.agents/commands/{implement-phase,implement-fixes,commit-and-sync,review-and-fix}.md`, `.agents/agents/review-iterate.md`, and `.agents/skills/<command>/` shims | `.claude/commands/{review-implementation,archive-plan,review-and-fix}.md` |
| `both` | Union of both coder lanes | Union of both reviewer lanes |

`review-and-fix` is present in both lanes for every role because plan creation and plan repair are shared operations.

`commit-and-sync` is deployed to the **Claude side for every role**, sourced from `templates/common/_claude/commands/commit-and-sync.md` (independent of which side codes). The Codex `commit-and-sync` command + skill shim is part of the Codex coder lane (`codex-codes` / `both`). All `commit-and-sync` files — both sides — are intentionally version-controlled, not added to the managed `.gitignore` block (see Gitignore Contract).

## Deployed Workflows

| Workflow | Lane | Purpose |
|----------|------|---------|
| `implement-phase` | Coder only | Implement one or more plan phases, run the inner review loop, and commit locally. |
| `implement-fixes` | Coder only | Apply user-provided findings, run the inner review loop, and commit locally. |
| `commit-and-sync` | Claude side every role; Codex coder lane | Commit working-tree changes, push, and optionally create a semver release or explicit tag. Version-controlled, not gitignored. |
| `review-iterate` | Coder inner reviewer | Read-only critical reviewer used inside implementation loops. Claude uses Sonnet; Codex uses `gpt-5.5` with medium reasoning effort. |
| `review-implementation` | Outer reviewer | Review one or more implementation phases, update the full plan status surface (headings, Work/Acceptance bullets, checkboxes, Phase Status table, per-phase Status lines, Phase Flow Mermaid node labels + class lines) in the plan's own legend within its narrow write policy, and commit the review locally. |
| `archive-plan` | Outer reviewer | Archive a fully-completed plan into a dated `archive/` file and start a fresh, task-free plan that carries forward only durable context. Refuses to run while any task is outstanding and asks the user how to proceed. |
| `review-and-fix` | Both lanes | Create a canonical implementation plan or repair structural gaps in an existing one. |

`.deployed-agents/conventions.md` is the shared instruction source for the deployed agents, referenced by every command and skill in both lanes. No root-level `AGENTS.md` / `CLAUDE.md` is deployed; the project's own copies (if any) are left untouched.

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
8. Unless `--no-gitignore` is supplied and the target is inside a git repository, the deployed agent scaffolding is added to the repo-root `.gitignore` inside a managed block (see Gitignore Contract).
9. `--dry-run` prints the file operations without writing.

## Gitignore Contract

The deploy keeps agent scaffolding out of version control by default:

- Scope: every file the deploy writes under `.claude/`, `.agents/`, or `.deployed-agents/`, **except intentionally-tracked workflows**. The overlay writes no root-level files, so the project's own `AGENTS.md` / `CLAUDE.md`, the implementation plan, and all other project files are out of scope and stay tracked.
- Tracked-workflow exception: `commit-and-sync` (its command file on the Claude and Codex sides, plus the Codex `.agents/skills/commit-and-sync/` shim) is deliberately omitted from the managed block so it becomes part of every dev's repo. Identified by path via `is_tracked_workflow`, independent of git state.
- Per-path exception: a path is **not** ignored when git already tracks it before the deploy (the project version-controls it on purpose — "it existed previously and was not gitignored"). Git-tracked status, not mere on-disk presence, is the signal, so wiping the managed block and redeploying self-heals instead of leaking scaffolding.
- The entries live in a single managed block (delimited by `# >>> coding-agents (managed by deploy.py) … >>>` / `# <<< … <<<`) at the repository root's `.gitignore`, with repo-root-relative anchored paths. The block is rewritten idempotently each deploy; content outside it is preserved.
- To start tracking a scaffolding file, `git add` it: the next deploy sees it tracked and drops it from the managed block.
- `--no-gitignore` disables the behavior; a non-git target is skipped with a reported note. `--dry-run` reports the change without writing.

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
- Inner reviewers are read-only and do not edit files. The inner reviewer (`review-iterate`) never commits, stages, or changes git state — committing is the calling implementer command's job.
- Outer reviewers commit locally when they finish. `review-implementation` commits whenever it changed the plan; `archive-plan` commits the archive move plus the fresh plan. Neither pushes. (An empty commit is never created when there was nothing to write.)
- Workflows survey git state before making or reviewing changes, including untracked files.
- Untracked implementation files are part of the review surface.
- Dirty worktrees are preserved; unrelated user changes are not reverted.
- Implementers read the target phase before coding and stop for user clarification when the phase contains unresolved ambiguity.
- Implementation loops have a three-cycle reviewer iteration cap.
- Repeated feedback for the same `file:line` is treated as priority work before unrelated cleanup.
- `git diff --check` is a standard verification step.
- Implementers run only the build (`{{build_cmd}}`); the test suite (`{{test_cmd}}`) is run exclusively by the reviewers (`review-iterate`, `review-implementation`). Implementers delegate testing by spawning `review-iterate` rather than running tests themselves — this avoids redundant suite runs on every implementer pass.
- Passing tests are necessary but not sufficient; reviewers check that tests prove the relevant acceptance criteria.
- Generic agents do not edit plan status markers. `review-implementation` is the explicit exception and may update markers under its plan write policy.
- `archive-plan` (reviewer lane) is the only operation that retires a plan: it refuses to run while any task is outstanding, moves the completed plan into a dated `archive/` file, and writes a fresh task-free plan carrying forward only durable context. The new plan contains no status markers.
- `## Open Questions` and `## Decisions` are append-only and user-owned. Existing entries are not edited, reordered, resolved, or removed by the agents — but `archive-plan` may carry still-relevant entries forward into a fresh plan (renumbered) and drop moot ones, since it is starting a new plan, not editing the live one. An empty section, or one whose only content is a note such as `None.` / `No open questions.`, is fully compliant: agents never flag it, treat it as incomplete, or fill it with placeholders. `## Decisions` is populated only when the user makes, confirms, or ratifies a decision during design or implementation.
- Final review output is terse and focused on outstanding work.

## Plan Contract

`review-and-fix` creates and repairs plans to this canonical structure:

```text
# <Project Name> Implementation Plan
<summary paragraph>

## Phase Flow
<mermaid flowchart — may carry per-node status via classDef/class lines>

## Phase Status
<optional status table — | Phase | Status | … |>

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

## Files to Create or Modify by Phase
### Phase N
<bullets — files the phase creates or modifies>

## Test Plan
### Phase N
<bullets>

## Decisions
<numbered list, append-only; may be empty or a "none" note>

## Open Questions
<numbered list, append-only; may be empty or a "none" note>

## Residual Risks
<bullets>
```

Phase headings use `## Phase N: <Title>` as the canonical form. Phase numbering is contiguous. `review-and-fix` may add missing structural sections with placeholders, normalize supported style issues, and create a new skeleton plan. A legacy `## Files to Create by Phase` heading is renamed in place to `## Files to Create or Modify by Phase` (a rename, not a duplicate section). It does not rewrite existing non-placeholder content, status markers, or existing `## Decisions` / `## Open Questions` entries, and an empty `## Decisions` or `## Open Questions` (or one that just notes there are none) is compliant — never flagged or auto-filled. `## Decisions` records decisions the user made, confirmed, or ratified during design or implementation; it sits immediately before `## Open Questions` and is append-only and user-owned, exactly like `## Open Questions`.

The deploy script also enforces a minimum plan skeleton:

- If no file exists at `{{plan_path}}`, deploy creates a starter implementation plan with one placeholder phase.
- If a plan exists, deploy repairs missing structural sections and per-phase `### Work` / `### Acceptance Criteria` blocks, preserving existing content.
- Existing plans are backed up before repair unless `--no-backup` is supplied.

Status markers are written **only** by `review-implementation`, which owns the *entire* status surface of a reviewed phase and updates every part of it consistently in a single local commit:

- Phase heading, `### Work` / `### Acceptance Criteria` bullets, and `## Recommended Execution Order` entries.
- Task/checklist checkboxes (`- [ ]` → `- [x]`) and file-inventory bullets.
- A per-phase `Status:` line and a `## Phase Status` table, when the plan has them.
- The `## Phase Flow` Mermaid graph — both the icon embedded in a node label and the `class <node> <className>` line, kept consistent with the diagram's `classDef` names.

It uses the plan's own legend when one is declared (a `Legend:` line, status-table legend, or Mermaid `classDef` names such as `done`/`inProgress`/`pending`/`blocked`). Only when the plan declares none does it default to:

- `✅` means complete.
- `⚠️` or `⚠` means partial and includes a concise bracketed reason.
- No marker means not started, not reviewed, or not status-marked yet.

The generic implementer/inner-reviewer agents (`implement-phase`, `implement-fixes`, `review-iterate`, `review-and-fix`) never touch or report any of these markers; stale status is not a finding for them.

`review-implementation` arguments are free-form: every token is interpreted as **either** a phase selector (number, range, comma/word list) **or** a plan-update suggestion, and a single invocation may carry both. Plan-update suggestions are verified against the code and folded into the status update, but never override the narrow Plan Write Policy. When no explicit phase selector is supplied — even alongside suggestions — `review-implementation` does not ask; it auto-detects and reviews every phase the plan marks in-progress (heading/`Status:`/Phase Status/`class … inProgress`), falling back to the lowest-numbered incomplete phase that has implementation on disk, and only asking once if that is still ambiguous. This mirrors `implement-phase`'s in-progress auto-detect.

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
