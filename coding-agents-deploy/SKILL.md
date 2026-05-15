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

## Workflow

### 1. Identify the target project path

Parse the user's request for a project path. If they said "go to my X project" with no full path, ask for the path. Confirm the folder exists with `ls` before continuing.

### 2. Confirm the role assignment

If the user already stated the role ("Claude codes, Codex reviews"), use it. Otherwise ask ONE question with options: `claude-codes` / `codex-codes` / `both`. Do not ask about anything else — the detector handles the rest.

### 3. Run the detector

Run `python scripts/detect_stack.py <target_path>` from this skill's directory (the Cowork bash runner can do this). The detector emits JSON describing the stack, build/test commands, plan path, and which `conventions/<stack>.md` to inject. Read the JSON before invoking the deploy.

### 4. Run the deploy

Run `python scripts/deploy.py --target <target_path> --role <role>` with optional flags:

- `--dry-run` — print what would happen, write nothing.
- `--no-backup` — overwrite without backing up (default: backup with `.bak.<timestamp>`).

The deploy script:
1. Calls the detector itself, so step 3 is informational for you (you can skip rerunning it).
2. Renders `templates/common/` plus the role-specific tree into the target.
3. For every existing file at a target path, moves it to `<path>.bak.<timestamp>` before writing the new content.
4. Prints a tree of what was created/replaced and a one-line summary of substitutions used.

### 5. Report to the user

Tell the user what was deployed, which files were backed up (if any), and what manual steps remain (e.g., reviewing `AGENTS.md`, deciding whether to commit). Suggest a `git status` so they can see the changes.

## Important

- **Never edit the templates from inside a deploy run.** If the user wants the templates changed, that's a separate task — edit `templates/` files in this repo, commit, then they're picked up by the next deploy.
- **Respect existing `AGENTS.md` / `CLAUDE.md`.** If the target already has one, back it up and write the new one — but mention to the user explicitly that the old content is in the `.bak` file so they can merge anything useful.
- **The detector is conservative.** If it can't identify the stack, it falls back to `conventions/generic.md`. The user can edit `AGENTS.md` afterwards to fill in specifics.
- **The skill is versioned in git** at `c:\vsprojects\jako-agents\coding-agents-deploy` (part of the [JakoMenkveld/jako-agents](https://github.com/JakoMenkveld/jako-agents) meta-repo for agentic work). Improvements to templates should be committed there.
