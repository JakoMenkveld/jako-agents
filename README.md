# jako-agents

Versioned home for [@JakoMenkveld](https://github.com/JakoMenkveld)'s agentic-work definitions — skills, commands, agents, and templates used to coordinate Claude Code, Codex, and Cowork across projects.

## Contents

- **[`coding-agents-deploy/`](coding-agents-deploy/)** — Cowork / Claude Code skill that deploys a coordinated Claude+Codex coding-agent setup into any project. Pick a role (Claude codes + Codex reviews, or vice versa, or both), and the skill renders the right `.claude/` + `.agents/` + `AGENTS.md` + `CLAUDE.md` tree, tailored to the target project's stack.

Future entries (separate sub-folders) will live alongside as new agentic patterns get distilled.

## Per-skill installation

Each sub-folder is self-contained and includes its own `install.ps1` for linking into `~/.claude/skills/`:

```powershell
cd c:\vsprojects\jako-agents\<sub-folder>
.\install.ps1            # symlink (recommended)
# or
.\install.ps1 -Copy      # copy if symlinks unavailable
```

See each sub-folder's README for skill-specific usage.
