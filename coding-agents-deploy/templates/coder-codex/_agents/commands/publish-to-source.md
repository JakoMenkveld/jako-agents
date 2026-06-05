---
name: publish-to-source
description: Share your work with the team. Merges the CURRENT branch into its source branch as one squashed commit while STRIPPING the entire coding-agent overlay (`.claude/`, `.agents/`, `.deployed-agents/`, plan-renderer artifacts), so teammates get your code but never your agent setup. Leaves your personal branch untouched.
---

# publish-to-source

Land everything from the **current** branch onto its **source branch** (the branch you branched off, e.g. `main`) as a single clean commit, with all coding-agent files removed from that commit. The overlay stays tracked on your personal branch; the team's source branch never receives it. This command moves to the source branch to build the shared commit, then returns you to your branch – the one deliberate exception to "never switch branches".

## Excluded overlay paths (always stripped from the shared commit)

- `.claude/`
- `.agents/`
- `.deployed-agents/`
- `{{plan_progress_path}}`
- `{{plan_html_path}}`

Everything else, including the plan at `{{plan_path}}`, goes to the team. (Ask the user if they also want `{{plan_path}}` excluded.)

## Step 1 — Preconditions

1. `git status --short` – working tree MUST be clean. If dirty, stop: tell the user to run `/commit-and-sync` first.
2. `git branch --show-current` → `<current>`. Empty (detached HEAD) → stop.
3. Ask the user which branch is `<source>`, defaulting to the repo default (`git symbolic-ref --quiet refs/remotes/origin/HEAD`). If `<current>` == `<source>`, stop – nothing to publish.

## Step 2 — Sync first

```bash
git fetch origin
```

Require `<current>` to already contain the source's latest: if `git rev-list --count <current>..origin/<source>` > 0, stop and tell the user to run `/commit-and-sync` first. Do not proceed until current is up to date with `origin/<source>`.

## Step 3 — Build the shared commit on the source branch

```bash
git switch <source>
git merge --ff-only origin/<source>     # diverged local source -> stop, report
git merge --squash <current>            # stage current's work as one squash; no commit yet
```

Conflicts (`git diff --name-only --diff-filter=U`): resolve trivial ones; stop and report non-trivial. Then strip the overlay from the staged set and the working tree:

```bash
git restore --staged -- .claude .agents .deployed-agents {{plan_progress_path}} {{plan_html_path}}
git clean -fdq -- .claude .agents .deployed-agents
git checkout -- {{plan_progress_path}} {{plan_html_path}} 2>/dev/null || git clean -fq -- {{plan_progress_path}} {{plan_html_path}}
```

Verify: `git diff --cached --name-only` must contain **none** of the excluded paths. If any overlay path is still staged, stop and report instead of committing.

## Step 4 — Commit and push the source branch

Draft one subject line summarizing the shared code (imperative; mirror `git log -5 --format="%s"` on source). Safety-check the staged diff for secret material (`.env`, `*credentials*`, `*secret*`, key patterns) – stop and ask if present.

```bash
git commit -m "<subject>"
git push origin <source>
```

Nothing staged (no non-overlay changes) → skip commit, report "nothing to publish". Never force-push. Never `--no-verify`.

## Step 5 — Return to your branch

```bash
git switch <current>
```

Confirm clean tree, back on `<current>`, overlay intact.

## Step 6 — Report

1-2 sentences: which branch published into which source + squashed commit subject + short SHA (or "nothing to publish"); confirmation the overlay was excluded; that you are back on `<current>`. No full diff/status dumps.
