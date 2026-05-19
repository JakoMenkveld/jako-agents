---
description: Commit the working tree of the jako-agents repo and sync it to GitHub. Fetches first, integrates remote work, generates a message from the diff, commits, and pushes the current branch to its upstream. Commits to whatever branch is checked out unless explicitly told otherwise.
aliases: [cns]
---

# /commit-and-sync

Commit the current working-tree changes in the **jako-agents** repo and push them to the remote. One-shot sync.

## Branch policy

- **Commit and push to the branch that is currently checked out.** Resolve it once with `git rev-parse --abbrev-ref HEAD` and use that everywhere below as `<branch>`.
- Do **not** switch, create, rebase onto, or push to a different branch (including `main`) unless the user explicitly tells you to in this invocation. There is no hard "everything goes to main" rule.
- `main` is simply the most common working branch here; it gets no special treatment beyond being the default checkout. If `<branch>` is something else, sync that.

## Repo facts (do not rediscover these)

- Remote: `git@github.com:JakoMenkveld/jako-agents.git` (`origin`).
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

- `git rev-parse --abbrev-ref HEAD` – this is `<branch>`.
- `git status --short`
- `git diff HEAD`
- `git log -5 --format="%s"`

If there is nothing staged, unstaged, or untracked, stop and report "nothing to commit". Do not create an empty commit.

## Step 2 – Fetch and integrate

```bash
git fetch origin
git rev-list --count HEAD..origin/<branch>
```

(If `origin/<branch>` does not exist yet, skip integration – this branch has no upstream yet; it will be created on push in Step 4.)

If the count is > 0, integrate before committing:

```bash
git pull --rebase origin <branch>
```

- Rebase clean: continue.
- Conflicts: stop, report exactly which files conflict and the conflicting hunks. Do not force anything.

## Step 3 – Draft the message

Read the diff. Write one subject around the dominant change. If any `coding-agents-deploy/` Python or template changed, run the test suite now and only commit if it passes; report failures instead of committing.

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
git push origin <branch>
```

If `<branch>` has no upstream, `git push -u origin <branch>` to create and track it. If the push is rejected as non-fast-forward, return to Step 2 (fetch + rebase), then push again. Never force-push.

## Step 5 – Report

One or two sentences: the branch, the commit subject, short SHA, push result (`<old>..<new> <branch> -> <branch>`), and the test outcome if the suite was run. Do not paste the full diff or status.
