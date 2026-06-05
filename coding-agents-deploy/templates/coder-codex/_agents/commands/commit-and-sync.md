---
name: commit-and-sync
description: Commit local changes to the CURRENT branch, merge in the latest changes from its source branch (without switching branches), push the current branch, and optionally tag. Supports `release` to auto-bump semver from changes since the last release tag.
---

# commit-and-sync

Commit working-tree changes to the **current** branch, merge in whatever changed on its **source branch** (the branch this one was created from), then push the current branch. Never switch branches: stay on the current branch and only read from the source branch. Optionally tag.

## Optional arguments

- Explicit tag: `--tag v1.2.3`, `tag=v1.2.3`, `tag: v1.2.3`
- Auto-release tag: `release`, `--release`, `release=true`

Rules:
- If both an explicit tag and `release` are present, explicit tag wins.
- Release tags must use `v<major>.<minor>.<patch>`.

## Style to match

Inspect `git log -5 --format="%s"` and mirror that style. Default: single-line sentence-cased subjects, no body, no co-author trailer.

## Step 1 — Inspect state (parallel)

- `git status`
- `git diff HEAD`
- `git log -5 --format="%s"`
- `git branch --show-current` (current branch – everything commits here)

If no changes and no tag/release requested: still run Step 3 (merge source in) and Step 4 (push) – a sync pulls the source branch's latest into this branch even with nothing to commit. Skip Step 2 only.
If no changes but tag/release requested: skip commit, still merge + push, then tag.

## Step 2 — Draft message, stage, and commit (only when changes exist)

Commit to the current branch first, so the working tree is clean for the merge. Read the diff and write one subject line capturing intent. Avoid generic subjects and file-name laundry lists.

**Safety check**: if the diff contains likely secret material (`.env`, `*credentials*`, `*secret*`, private key / API key patterns), stop and ask before staging.

```bash
git add -A
git commit -m "<subject>"
```

## Step 3 — Merge the latest source-branch changes into the current branch

Git does not record a branch's source branch, so **ask the user which branch is the source** (the branch the current branch was branched off). Detect the repo default branch and offer it as the default:

```bash
git symbolic-ref --quiet refs/remotes/origin/HEAD   # e.g. refs/remotes/origin/main
```

Ask once (default to the detected branch) and use the answer as `<source>`. If the current branch *is* the source, skip to Step 4. Otherwise fetch and merge the source into the current branch **without switching branches** – merge the remote-tracking ref directly:

```bash
git fetch origin
git merge origin/<source> --no-edit
```

Up to date or clean merge: proceed. Conflicts: list with `git diff --name-only --diff-filter=U`; resolve trivial ones (`git add` + `git commit --no-edit`); for non-trivial conflicts, stop and report the conflicting files and hunks. This is a merge, not a rebase – history only moves forward, so the push never needs a force.

## Step 4 — Push the current branch

```bash
git push
```

No upstream? `git push -u origin <current-branch>`.

Never force-push. Never `--no-verify`.

## Step 5 — Resolve release tag (only for `release`, no explicit tag)

1. `git fetch --tags`
2. Latest semver release tag: `git tag --list "v[0-9]*.[0-9]*.[0-9]*" --sort=-version:refname | head -n 1`
3. Range: `<lastTag>..HEAD` (or `HEAD` from base `v0.0.0` if no tag exists).
4. Inspect changes:
   ```bash
   git log --format="%s%n%b" <range>
   git diff --name-status <range>
   ```
5. Bump level:
   - **major** if commit text contains `BREAKING CHANGE`, `breaking`, or conventional `!:`.
   - **minor** if no major and commit text contains `add`, `added`, `feature`, `support`, `introduce`, `new`.
   - **patch** otherwise.
6. Form `v<major>.<minor>.<patch>`.

## Step 6 — Validate and push tag

Validate not blank, not existing locally (`git rev-parse -q --verify "refs/tags/<tag>"`), not existing on origin (`git ls-remote --tags origin "refs/tags/<tag>"`).

```bash
git tag -a "<tag>" -m "<tag>"
git push origin "<tag>"
```

Never force-push tags.

## Step 7 — Report

1-2 sentences: commit subject + short SHA (or "no commit needed"); which source branch was merged in and whether anything came across (or "already up to date"); branch push status; tag name + push status (if used); for `release`, chosen bump level and previous tag baseline.

Do not paste full diff/status output.
