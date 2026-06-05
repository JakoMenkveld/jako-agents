---
name: deploy-coding-agents
description: Deploy a complete set of Claude + Codex coding-agent files into a target project. Use when the user says "deploy coding agents", "set up the coding agents", "deploy the agents to <project>", or names a role assignment like "Claude codes, Codex reviews" or "Codex codes, Claude reviews". Installs a non-invasive overlay — a tracked .deployed-agents/ source-of-truth plus .claude/ and .agents/ trees — with project-specific build/test commands and conventions detected from the target's stack. The overlay is tracked in git so it can live on a personal dev branch and is stripped from team-facing branches via /publish-to-source. It never writes or merges the project's own AGENTS.md / CLAUDE.md.
---

# Deploy Coding Agents

You are deploying a coordinated Claude+Codex coding-agent setup into a target project. The skill comes with two role configurations:

- **`claude-codes`** — Claude implements via the rich `.claude/commands/` set with an inner `review-iterate` Sonnet subagent; Codex hosts a single `.agents/skills/review-implementation/` for the outer review.
- **`codex-codes`** — Codex implements via the rich `.agents/commands/` + skill manifests with an inner `review-iterate` agent running on `gpt-5.5`; Claude hosts a single `.claude/commands/review-implementation.md` for the outer review.
- **`both`** — deploys both lanes so the project can switch coders ad-hoc.

**Every role also deploys `review-and-fix`** to BOTH lanes (Claude and Codex both get it, regardless of role). It creates new implementation plans, or audits existing ones — auto-fixing structural gaps and reviewing the plan's content (unfilled placeholders, vague or non-verifiable items, internal inconsistencies) as advisory findings — so they comply with what the implementer and reviewer expect.

**Every role also deploys `write-spec`** to BOTH lanes (Claude and Codex both get it, regardless of role). It writes a precise, verifiable specification as a single markdown document with small, single-purpose mermaid diagrams: prose carries intent and rationale, while every behavioral requirement is a machine-checkable assertion (precondition -> action -> postcondition) pinned to a concrete verification and a draft/specified/verified lifecycle status.

**The reviewer lane also gets `archive-plan`** (reviewer only, never the coder). It archives a fully-completed plan into a dated `archive/` file and starts a fresh, task-free plan that carries forward only durable context; it refuses to run while any task is outstanding and asks the user how to proceed.

**This is a non-invasive overlay.** The deploy never writes, reads, backs up, or merges the project's own root-level `AGENTS.md` / `CLAUDE.md`. The single source of truth for the deployed agents is `.deployed-agents/conventions.md` (a dot-dir owned by this deploy, tracked in git); every deployed command and skill points there. Conventions are therefore workflow-scoped — they apply when a deployed command runs, not ambiently in a plain Claude/Codex session — by design, so the developer's own setup is untouched.

The deploy script is merge-aware for its own scaffolding. When a target project already has *deployed* agent files (e.g. a prior `.deployed-agents/conventions.md` with filled-in self-config), it preserves project-only content, asks about conflicts when interactive, and can promote useful additions back into this skill's source templates before rendering the final files.

## Workflow

### 1. Identify the target project path

Parse the user's request for a project path. If they said "go to my X project" with no full path, ask for the path. Confirm the folder exists with `ls` before continuing.

### 2. Confirm the role assignment

If the user already stated the role ("Claude codes, Codex reviews"), use it. Otherwise ask one question with options: `claude-codes` / `codex-codes` / `both`.

### 3. Run the detector

Run `python scripts/detect_stack.py <target_path>` from this skill's directory (the Cowork bash runner can do this). The detector emits JSON describing the stack, build/test commands, plan path, and which `conventions/<stack>.md` to inject. Read the JSON before invoking the deploy.

### 4. Run the deploy

Run `python scripts/deploy.py --target <target_path> --role <role> --merge-existing` with optional flags:

- `--dry-run` — print what would happen, write nothing.
- `--no-backup` — overwrite without backing up (default: backup with `.bak.<timestamp>`).
- `--template-updates ask|never|always` — controls whether project-only additions can be written back to this skill's templates. Default is `ask`; use `never` for a purely project-local deploy.
- `--interactive auto|always|never` — controls conflict prompts. Default is `auto`.
- `--skip-plan` — skip implementation-plan creation/repair.
- `--gitignore-agents` — add the deployed agent scaffolding to the repo `.gitignore` in a managed block (off by default). Only use this for a project that does NOT want the personal-dev-branch / `/publish-to-source` workflow.
- `--no-gitignore` — do not touch the repo `.gitignore` at all (neither add nor remove the managed block).

The deploy script:
1. Calls the detector itself, so step 3 is informational for you (you can skip rerunning it).
2. Renders `templates/common/` plus the role-specific tree into the target.
3. Merges existing Markdown files by heading when `--merge-existing` is supplied:
   - Project-only sections are preserved in the project.
   - Conflicting sections ask whether to keep the project version, use the template version, or append the project body to the template version.
   - Project-only sections/files and chosen project-side conflict resolutions can be promoted into `templates/` when the user agrees.
4. Creates `{{plan_path}}` if it does not exist, or repairs missing canonical plan structure if it does. Existing plans are backed up before repair unless `--no-backup` is supplied.
5. Leaves the deployed agent scaffolding (`.claude/`, `.agents/`, `.deployed-agents/`) TRACKED by default, and removes any managed `.gitignore` block a previous deploy added (so existing projects get un-ignored on the next deploy). The agent files are meant to live on a personal dev branch and be stripped from team-facing branches by `/publish-to-source`. Pass `--gitignore-agents` to restore the old ignore-by-default behavior; `--no-gitignore` leaves `.gitignore` untouched entirely. Skipped when the target isn't a git repo.
6. Prints a tree of what was created, merged, repaired, promoted, gitignore-cleared, or left unchanged.

### 5. Report to the user

Tell the user what was deployed, which files were backed up (if any), whether any template files were updated from project ideas, and what manual steps remain (e.g., reviewing `.deployed-agents/conventions.md`, filling plan placeholders, deciding whether to commit). Note explicitly that the project's own `AGENTS.md` / `CLAUDE.md` were not touched. Suggest a `git status` so they can see the changes.

## Important

- **Template promotion is opt-in.** If the deploy script asks whether a project-only idea should update this skill's templates, treat that as a product decision. Promote only when the idea should apply to future projects, not when it is project-specific.
- **Never touch the project's `AGENTS.md` / `CLAUDE.md`.** This is an overlay: the deploy does not write, read, back up, or merge those files. The source of truth is `.deployed-agents/conventions.md`. `--merge-existing` only merges the deploy's own scaffolding (e.g. preserving filled-in self-config in a prior `.deployed-agents/conventions.md` across redeploys).
- **Plans are managed during deploy.** The script creates a starter plan when missing and repairs missing structural sections in an existing plan. Existing plan content, status markers, and `## Open Questions` entries must not be deleted (Open Questions is append-only, user-owned). `## Decisions` is a free-form, live section maintained by the user and `/review-implementation` (not by deploy or `review-and-fix`); deploy only ensures its heading exists. A legacy `## Files to Create by Phase` heading is renamed in place to `## Files to Create or Modify by Phase`. An empty `## Decisions` or `## Open Questions` is acceptable.
- **Scaffolding is tracked by default.** Agent files (`.claude/`, `.agents/`, `.deployed-agents/`) are tracked in git so they can live on the user's personal dev branch; sharing code with the team goes through `/publish-to-source`, which merges the work into the source branch while stripping the overlay. A default deploy also REMOVES any managed `.gitignore` block a previous (older) deploy added. Pass `--gitignore-agents` to keep the old ignore-by-default behavior. The implementation plan is always tracked.
- **The detector is conservative.** If it can't identify the stack, it falls back to `conventions/generic.md`. The user (or the first-run self-config) can edit `.deployed-agents/conventions.md` afterwards to fill in specifics.
- **The skill is versioned in git** at `c:\vsprojects\jako-agents\coding-agents-deploy` (part of the [JakoMenkveld/jako-agents](https://github.com/JakoMenkveld/jako-agents) meta-repo for agentic work). Improvements to templates should be committed there.
