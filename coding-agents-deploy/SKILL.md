---
name: deploy-coding-agents
description: Deploy a complete set of Claude + Codex coding-agent files into a target project. Use when the user says "deploy coding agents", "set up the coding agents", "deploy the agents to <project>", or names a role assignment like "Claude codes, Codex reviews" or "Codex codes, Claude reviews". Creates AGENTS.md, CLAUDE.md, .claude/, and .agents/ trees with project-specific build/test commands and conventions detected from the target's stack.
---

# Deploy Coding Agents

You are deploying a coordinated Claude+Codex coding-agent setup into a target project. The skill comes with two role configurations:

- **`claude-codes`** — Claude implements via the rich `.claude/commands/` set with an inner `review-iterate` Sonnet subagent; Codex hosts a single `.agents/skills/review-implementation/` for the outer review.
- **`codex-codes`** — Codex implements via the rich `.agents/commands/` + skill manifests with an inner `review-iterate` agent running on `gpt-5.5`; Claude hosts a single `.claude/commands/review-implementation.md` for the outer review.
- **`both`** — deploys both lanes so the project can switch coders ad-hoc.

**Every role also deploys `review-and-fix`** to BOTH lanes (Claude and Codex both get it, regardless of role). It creates new implementation plans or audits-and-auto-fixes existing ones so they comply with the structure the implementer and reviewer expect.

The deploy script is merge-aware. When a target project already has agent files, it preserves project-only content, asks about conflicts when interactive, and can promote useful project additions back into this skill's source templates before rendering the final project files.

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

The deploy script:
1. Calls the detector itself, so step 3 is informational for you (you can skip rerunning it).
2. Renders `templates/common/` plus the role-specific tree into the target.
3. Merges existing Markdown files by heading when `--merge-existing` is supplied:
   - Project-only sections are preserved in the project.
   - Conflicting sections ask whether to keep the project version, use the template version, or append the project body to the template version.
   - Project-only sections/files and chosen project-side conflict resolutions can be promoted into `templates/` when the user agrees.
4. Creates `{{plan_path}}` if it does not exist, or repairs missing canonical plan structure if it does. Existing plans are backed up before repair unless `--no-backup` is supplied.
5. Prints a tree of what was created, merged, repaired, promoted, or left unchanged.

### 5. Report to the user

Tell the user what was deployed, which files were backed up (if any), whether any template files were updated from project ideas, and what manual steps remain (e.g., reviewing `AGENTS.md`, filling plan placeholders, deciding whether to commit). Suggest a `git status` so they can see the changes.

## Important

- **Template promotion is opt-in.** If the deploy script asks whether a project-only idea should update this skill's templates, treat that as a product decision. Promote only when the idea should apply to future projects, not when it is project-specific.
- **Respect existing `AGENTS.md` / `CLAUDE.md`.** Use `--merge-existing` so project-specific sections survive. If a merge writes a changed file, the original is still backed up unless `--no-backup` is supplied.
- **Plans are managed during deploy.** The script creates a starter plan when missing and repairs missing structural sections in an existing plan. Existing plan content, status markers, and `## Open Questions` entries must not be deleted.
- **The detector is conservative.** If it can't identify the stack, it falls back to `conventions/generic.md`. The user can edit `AGENTS.md` afterwards to fill in specifics.
- **The skill is versioned in git** at `c:\vsprojects\jako-agents\coding-agents-deploy` (part of the [JakoMenkveld/jako-agents](https://github.com/JakoMenkveld/jako-agents) meta-repo for agentic work). Improvements to templates should be committed there.
