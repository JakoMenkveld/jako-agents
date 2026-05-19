---
description: Commit the working tree of the jako-agents repo and sync it to GitHub main. Fetches first, integrates remote work, generates a message from the diff, commits, and pushes. No feature branches – this repo commits directly to main.
aliases: [cns]
---

# /commit-and-sync

Commit the current working-tree changes in the **jako-agents** repo and push them to `origin/main`. One-shot sync.

## Repo facts (do not rediscover these)

- Remote: `git@github.com:JakoMenkveld/jako-agents.git`. Branch: **`main`**. Push target: `origin main`.
- **No feature branches.** Commit and sync directly to `main`. If you find yourself on another branch, stop and ask – do not create or switch branches.
- The primary repo at `c:/vsprojects/jako-agents` tracks the `coding-agents-deploy/` files directly. There is a separate nested `coding-agents-deploy/.git` clone of the same remote; **ignore it** – always run git from the `jako-agents` root, never `cd` into the nested repo.
- Test suite (run only if code under `coding-agents-deploy/` changed): `python -m unittest discover -s coding-agents-deploy/tests -q`.

## Style to match

Single-line, sentence-cased subject that captures the *why*. Mirror recent subjects: `git log -5 --format="%s"`. A short body is fine when the change spans themes; prefer none. Every commit ends with the trailer:

```
Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

Never use em dashes (`—`) in the message or anywhere – use an en dash (`–`) instead.

## Step 1 – Inspect state (parallel)

Run together via the Bash tool:

- `git status --short`
- `git diff HEAD`
- `git log -5 --format="%s"`

If there is nothing staged, unstaged, or untracked, stop and report "nothing to commit". Do not create an empty commit.

## Step 2 – Fetch and integrate

```bash
git fetch origin
git rev-list --count HEAD..origin/main
```

If the count is > 0, integrate before committing:

```bash
git pull --rebase origin main
```

- Rebase clean: continue.
- Conflicts: stop, report exactly which files conflict and the conflicting hunks. Do not force anything.

## Step 3 – Draft the message

Read the diff. Write one subject around the dominant change. If the test suite is relevant (any `coding-agents-deploy/` Python or template change), run it now and only commit if it passes; report failures instead of committing.

**Secret check:** if the diff touches anything that may hold a secret (`.env`, `*credentials*`, `*secret*`, API-key / token / private-key patterns), stop and ask before staging. (`.env`, `.venv/`, `__pycache__/`, `*.bak.*`, `scratch/` are gitignored – they should not appear; if they do, investigate rather than commit.)

## Step 4 – Stage, commit, push

```bash
git add -A
```

> `-A` is fine because Step 3 vetted the diff. If Step 3 flagged anything, stage explicitly by name instead.

Commit with a HEREDOC so the trailer is preserved:

```bash
git commit -m "$(cat <<'EOF'
<subject line>

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

If a pre-commit hook fails, do NOT `--amend`. Fix the cause, re-stage, make a new commit. Never `--no-verify`.

```bash
git push origin main
```

If the push is rejected as non-fast-forward, return to Step 2 (fetch + rebase), then push again. Never force-push.

## Step 5 – Report

One or two sentences: the commit subject, short SHA, push result (`<old>..<new> main -> main`), and the test outcome if the suite was run. Do not paste the full diff or status.
