---
description: Share your work with the team. Merges the CURRENT branch into its source branch as one squashed commit, while STRIPPING the entire coding-agent overlay (`.claude/`, `.agents/`, `.deployed-agents/`, and the plan-renderer runtime artifacts) so teammates get your code changes but never your agent setup. Your personal branch is left untouched.
aliases: [pts, share]
---

# /publish-to-source

Push your code to the team without pushing your agent overlay. This takes everything you have done on the **current** branch and lands it on its **source branch** (the branch you branched off, e.g. `main`) as a single clean commit, but with all the coding-agent files removed from that commit. The agent overlay is tracked on your personal branch so you keep it; the team's source branch never receives it, so it can't collide with their own agent setup.

This command DOES move to the source branch to build the shared commit, then returns you to your branch. That is the one exception to the "never switch branches" rule – it is a deliberate publish action, not a routine sync.

## What counts as "the agent overlay" (always excluded)

These paths are stripped from the commit that lands on the source branch:

- `.claude/`
- `.agents/`
- `.deployed-agents/`
- `{{plan_progress_path}}` (plan-renderer live overlay)
- `{{plan_html_path}}` (baked plan view)

Everything else – your actual code changes, and the implementation plan at `{{plan_path}}` itself – does go to the team. (If you also want the plan kept private, say so and exclude `{{plan_path}}` too.)

## Step 1 — Preconditions

1. `git status --short` – the working tree MUST be clean. If there are uncommitted changes, stop and tell the user to run `/commit-and-sync` first (or commit manually). Never publish a dirty tree.
2. `git branch --show-current` – this is `<current>`. If it is empty (detached HEAD), stop and report.
3. Determine `<source>`: git does not record it, so **ask the user which branch is the source branch** to publish into, offering the repo default as the suggested default:
   ```bash
   git symbolic-ref --quiet refs/remotes/origin/HEAD   # e.g. refs/remotes/origin/main
   ```
   If `<current>` equals `<source>`, stop – you are already on the source branch, there is nothing to publish.

## Step 2 — Sync both branches

```bash
git fetch origin
```

Make sure your current branch already contains the source branch's latest, so the publish is purely your additions and conflicts are unlikely. If `git rev-list --count <current>..origin/<source>` is greater than 0, stop and tell the user to run `/commit-and-sync` first (it merges the source branch into the current branch). Do not proceed until `<current>` is up to date with `origin/<source>`.

## Step 3 — Build the shared commit on the source branch

Switch to the source branch and fast-forward it to the remote:

```bash
git switch <source>
git merge --ff-only origin/<source>
```

If the fast-forward fails, the local source branch has diverged from the remote – stop and report; do not force anything.

Stage your branch's work as a single squashed change, then remove the agent overlay from what is staged:

```bash
git merge --squash <current>
```

- Conflicts here mean the source advanced in files you also changed: list them with `git diff --name-only --diff-filter=U`, resolve the trivial ones, and for non-trivial conflicts stop and report. (Running `/commit-and-sync` first usually prevents this.)

Now drop every agent-overlay path from the staged commit and from the source branch's working tree, so none of it lands on the source branch:

```bash
git restore --staged -- .claude .agents .deployed-agents {{plan_progress_path}} {{plan_html_path}}
git clean -fdq -- .claude .agents .deployed-agents
git checkout -- {{plan_progress_path}} {{plan_html_path}} 2>/dev/null || git clean -fq -- {{plan_progress_path}} {{plan_html_path}}
```

- `git restore --staged` unstages the overlay. For overlay paths the source branch already tracks (rare, e.g. a `.claude/settings.json` the team committed), this reverts them to the source's version – the team keeps theirs. For overlay paths the source never tracked, they become untracked and `git clean` removes them from the working tree.

Verify before committing:

```bash
git status --short
git diff --cached --name-only
```

The staged file list must contain **none** of the excluded paths. If any `.claude/`, `.agents/`, `.deployed-agents/`, `{{plan_progress_path}}`, or `{{plan_html_path}}` entry is still staged, stop and report rather than committing.

## Step 4 — Commit and push the source branch

Draft one subject line summarizing the code changes you are sharing (imperative mood, mirror `git log -5 --format="%s"` on the source branch). **Safety check**: if the staged diff contains likely secret material (`.env`, `*credentials*`, `*secret*`, key patterns), stop and ask first.

```bash
git commit -m "<subject>"
git push origin <source>
```

Never force-push. Never `--no-verify`. If there is nothing staged (your branch had no non-overlay changes over the source), skip the commit and report that there was nothing to publish.

## Step 5 — Return to your branch

```bash
git switch <current>
```

Confirm `git status` is clean and you are back on `<current>` with your agent overlay intact.

## Step 6 — Report

1-2 sentences:
- Which branch was published into which source branch, and the squashed commit subject + short SHA (or "nothing to publish").
- Confirmation that the agent overlay was excluded (it stays only on `<current>`).
- That you are back on `<current>`.

Do not paste full diff/status output.
