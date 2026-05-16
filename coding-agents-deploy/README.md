# deploy-coding-agents

A Cowork / Claude Code skill that deploys a "best of breed" set of coding-agent files (`.claude/`, `.agents/`, `AGENTS.md`, `CLAUDE.md`) into a project, with the role assignment of your choice:

- **`claude-codes`** — Claude implements the plan, Codex does the outer review.
- **`codex-codes`** — Codex implements the plan, Claude does the outer review.
- **`both`** — deploy both lanes side-by-side.

Every role also deploys a **`review-and-fix`** skill to both Claude and Codex — it creates new implementation plans or audit-and-auto-fixes existing ones so they comply with the structure the implementer and reviewer agents expect.

## How it works

The skill scans a target project, detects its stack (build/test commands, framework conventions, plan file path), then renders a parameterized template tree into the project. Existing files are backed up with a timestamped `.bak.` suffix before being changed. In merge mode, existing Markdown agent files are merged by heading so project-specific sections survive, conflicts can be resolved interactively, and useful project-only additions can be promoted back into this repo's templates for future deployments.

The deploy also ensures an implementation plan exists. If the detected plan path is missing, it creates a starter canonical plan. If a plan exists, it backs it up and fills missing structural sections without deleting existing plan content.

## Invocation

In Cowork or Claude Code, say something like:

> Deploy the coding agents to `c:\vsprojects\my-new-project` with Claude coding and Codex reviewing.

or

> Go to my `swissinc/foo` project and deploy the coding agents — Codex codes, Claude reviews.

The skill will inspect the project, ask one question (role assignment, if not already given), and proceed.

## Layout

```
deploy-coding-agents/
  SKILL.md                  # entry point invoked by Claude / Cowork
  scripts/
    detect_stack.py         # inspects target project, emits JSON
    deploy.py               # renders/merges templates, manages plan file, prints summary
  templates/
    common/                 # AGENTS.md, CLAUDE.md, .claude/settings.json
    coder-claude/           # role: Claude codes, Codex reviews (+ review-and-fix in both lanes)
    coder-codex/            # role: Codex codes, Claude reviews (+ review-and-fix in both lanes)
  conventions/              # per-stack convention blocks (dotnet/typescript/python/go/generic)
```

## Substitution variables

Filled by the detector before templates are rendered:

| Variable | Example |
|----------|---------|
| `{{project_name}}` | `gold` |
| `{{stack_summary}}` | `.NET 10 / C# 12 / Blazor WASM / EF Core 10` |
| `{{build_cmd}}` | `dotnet build` |
| `{{test_cmd}}` | `dotnet test` |
| `{{lint_cmd}}` | `npm run lint` (or empty) |
| `{{plan_path}}` | `docs/implementation-plan.md` |
| `{{conventions_block}}` | injected from `conventions/<stack>.md` |

## Conventions captured from existing implementations

The templates baked these patterns in:

- **Severity tags** — `BLOCKER` / `MAJOR` / `MINOR` / `NIT` / `DOC` (Tuple) plus `[SHARED]` for shared-library suggestions (Gold).
- **Read-only inner reviewer** — no Write/Edit tools.
- **Fetch-first** — `git fetch && git status` before any work.
- **3-cycle implementer↔reviewer cap** — stop and surface to user.
- **No status-marker bookkeeping** — never report `[ ]`/`[x]` or phase `✅` flags as findings.
- **`AGENTS.md` is source of truth** — `CLAUDE.md` inherits via `@AGENTS.md`.
- **Append-only `## Open Questions`** in plan reviews.
- **Terse paragraph reports**, not bulleted task lists, for final review output.
- **`commit-and-sync` with optional `release` semver auto-bump** (from drydoc).

## The skills deployed

| Skill | Role | Lane | Purpose |
|-------|------|------|---------|
| `implement-phase` | coder | coder's lane only | Implement one or more plan phases, run inner review loop, commit locally. |
| `implement-fixes` | coder | coder's lane only | Apply a user-provided list of findings, review, iterate, commit. |
| `commit-and-sync` | coder | coder's lane only | Commit working tree, push, optional semver release tag. |
| `review-iterate` | coder's inner reviewer | coder's lane only | Read-only critical reviewer used inside the implementer's loop. |
| `review-implementation` | outer reviewer | reviewer's lane only | Human-driven outer review of a phase; updates plan status markers. |
| **`review-and-fix`** | **plan management** | **both lanes** | **Create a new plan or audit-and-auto-fix the structure of an existing one to match what implementers and reviewers expect.** |

## Local development

This repo is meant to be edited and refined over time. To link it into Claude Code as a skill, run from this folder:

```powershell
# Symlink (recommended — edits in this repo are picked up live)
.\install.ps1

# Or copy (no admin rights / no developer mode needed; you'll need to re-run install.ps1 to refresh)
.\install.ps1 -Copy
```

The script:
1. Creates `~/.claude/skills/` if missing.
2. Removes any existing `deploy-coding-agents` entry at that path.
3. Symlinks (or copies) this repo's root into `~/.claude/skills/deploy-coding-agents`.

The skill is picked up by Claude Code on the next session start.

Run the deploy tests after changing merge or plan-repair behavior:

```powershell
python -m unittest discover -s .\tests
```

## Repo context

This skill lives in the [`jako-agents`](https://github.com/JakoMenkveld/jako-agents) meta-repo, alongside other agentic-work definitions. Commit, push, and pull from the parent `c:\vsprojects\jako-agents` directory.

## Merge-aware deploy

For normal use, deploy with:

```powershell
python .\scripts\deploy.py --target C:\path\to\project --role codex-codes --merge-existing
```

Useful flags:

- `--template-updates ask|never|always` controls whether project-only ideas can update `templates/`.
- `--interactive auto|always|never` controls conflict prompts.
- `--skip-plan` leaves the implementation plan untouched.
- `--dry-run` prints planned operations without writing.

## Status

This is v1. The templates are skeletons derived from the `omnis/gold` (Claude-codes pattern) and `swissinc/tuple` (Codex-codes pattern) projects. Stack-specific content lives in `conventions/`; project-specific content is injected at deploy time, and broadly reusable project discoveries can be promoted into the templates through merge-aware deploys.
