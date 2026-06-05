---
description: Commit working-tree changes to the CURRENT branch, merge in the latest changes from the source branch it was branched off (without switching branches), and push the current branch. Optionally tag with `release` to auto-bump semver, or `--tag vX.Y.Z` for an explicit tag.
aliases: [cns]
---

# /commit-and-sync

Commit working-tree changes to the **current** branch, pull in whatever has changed on its **source branch** (the branch this one was created from) by merging that source into the current branch, then push. This never switches branches: you stay on the current branch the whole time, and the source branch is only ever read from, never checked out or modified.

## Optional arguments

- Explicit tag: `--tag v1.2.3`, `tag=v1.2.3`, or `tag: v1.2.3`
- Auto-release tag: `release`, `--release`, or `release=true`

Rules:
- If both an explicit tag and `release` are present, the explicit tag wins.
- Release tags must use `v<major>.<minor>.<patch>` format.

## Style to match

Inspect the last ~5 commit subjects with `git log -5 --format="%s"` and mirror that style. Default style: single-line sentence-cased subjects, no body, no co-author trailer.

## Step 1 — Inspect state

Run in parallel:
- `git status`
- `git diff HEAD`
- `git log -5 --format="%s"`
- `git branch --show-current` (the current branch – everything commits here)

Detect whether there are working-tree changes:
- Changes present → commit them in Step 2.
- No changes, no tag/release requested → skip Step 2 (nothing to commit) but STILL run Step 3 (merge the source branch in) and Step 4 (push), because the point of a sync is to pull the source branch's latest into this branch.
- No changes but tag/release requested → skip the commit, still merge + push, then tag on the resulting `HEAD`.

## Step 2 — Draft message, stage, and commit (only when changes exist)

Commit to the current branch. Do this **before** the merge so the working tree is clean when the source branch comes in.

Read the diff and write one subject line that captures the intent. Use imperative mood. Avoid generic subjects and file-name laundry lists. If there are many unrelated changes, describe the dominant theme.

**Safety check**: if the diff contains likely secret material (`.env`, `*credentials*`, `*secret*`, private key / API key patterns), stop and ask before staging.

```bash
git add -A
git commit -m "<subject>"
```

## Step 3 — Merge the latest source-branch changes into the current branch

Git does not record which branch a branch was created from, so **ask the user which branch is the source branch** (the branch the current branch was branched off and should track). Detect the repository's default branch and offer it as the suggested default:

```bash
git symbolic-ref --quiet refs/remotes/origin/HEAD   # e.g. refs/remotes/origin/main
```

Ask once, e.g. "Which branch should I merge the latest changes from? [default: `main`]", and use the user's answer as `<source>`. If the current branch *is* the source branch, there is nothing to merge in – say so and skip to Step 4.

Then fetch and merge the source branch into the current branch. **Do not check out or switch branches** – merge the remote-tracking ref directly into the branch you are already on:

```bash
git fetch origin
git merge origin/<source> --no-edit
```

- Merge succeeds (fast-forward or merge commit): proceed.
- Already up to date: proceed (nothing came in).
- Merge conflicts: `git diff --name-only --diff-filter=U` lists conflicted files. Resolve trivial conflicts (non-overlapping regions, unambiguous resolution) with `git add` + `git commit --no-edit`. For non-trivial conflicts, stop and report exactly which files conflict and what the conflicting hunks are – do not guess.

This is a plain merge, not a rebase: the current branch's history is preserved and only moves forward, so the push in Step 4 never needs a force.

## Step 4 — Push the current branch

```bash
git push
```

If the branch has no upstream:

```bash
git push -u origin <current-branch>
```

Never force-push. Never use `--no-verify`.

## Step 5 — Resolve release tag (only for `release`, no explicit tag)

1. `git fetch --tags`
2. Find latest semver release tag:
   ```bash
   git tag --list "v[0-9]*.[0-9]*.[0-9]*" --sort=-version:refname | head -n 1
   ```
3. Range: `<lastTag>..HEAD` (or `HEAD` from base `v0.0.0` if no tag exists).
4. Inspect changes since last release:
   ```bash
   git log --format="%s%n%b" <range>
   git diff --name-status <range>
   ```
5. Decide bump level (deterministic order):
   - **major** if commit text contains `BREAKING CHANGE`, `breaking`, or conventional `!:` marker.
   - **minor** if no major and commit text contains `add`, `added`, `feature`, `support`, `introduce`, `new`.
   - **patch** otherwise.
6. Increment semver and form `v<major>.<minor>.<patch>`.

## Step 6 — Validate and push tag

Let `<tag>` be the explicit or computed release tag.

Validate:
- Not blank.
- Does not exist locally: `git rev-parse -q --verify "refs/tags/<tag>"`
- Does not exist on origin: `git ls-remote --tags origin "refs/tags/<tag>"`

If the tag exists locally or remotely, stop and report.

Create and push:

```bash
git tag -a "<tag>" -m "<tag>"
git push origin "<tag>"
```

Never force-push tags.

## Step 7 — Report

1-2 sentences:
- Commit subject + short SHA (or "no commit needed").
- Which source branch was merged in and whether anything came across (or "already up to date").
- Branch push status.
- Tag name + push status (when used).
- For `release`, include chosen bump level (major/minor/patch) and previous tag baseline.

Do not paste full diff/status output.
