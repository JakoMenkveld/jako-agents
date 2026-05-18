---
description: Fetch from origin, merge if needed, generate a commit message from the diff, stage everything, commit, and push to the tracked branch. Optionally tag with `release` to auto-bump semver, or `--tag vX.Y.Z` for an explicit tag.
aliases: [cns]
---

# /commit-and-sync

Fetch, merge, commit working-tree changes, and push. One-shot sync to the remote.

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

Then detect whether there are working-tree changes:
- No changes, no tag/release requested → stop and report "nothing to commit".
- No changes but tag/release requested → skip the commit steps; continue to tagging on current `HEAD`.

## Step 2 — Fetch and merge

```bash
git fetch origin
```

```bash
git rev-list HEAD..origin/<current-branch> --count
```

If incoming count > 0:

```bash
git merge origin/<current-branch> --no-edit
```

- Merge succeeds: proceed.
- Merge conflicts: `git diff --name-only --diff-filter=U` lists conflicted files. Resolve trivial conflicts (non-overlapping regions, unambiguous resolution) with `git add` + `git commit --no-edit`. For non-trivial conflicts, stop and report exactly which files conflict and what the conflicting hunks are.

## Step 3 — Draft commit message (only when changes exist)

Read the diff and write one subject line that captures the intent. Use imperative mood. Avoid generic subjects and file-name laundry lists. If there are many unrelated changes, describe the dominant theme.

**Safety check**: if the diff contains likely secret material (`.env`, `*credentials*`, `*secret*`, private key / API key patterns), stop and ask before staging.

## Step 4 — Stage, commit, push

```bash
git add -A
git commit -m "<subject>"
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
- Branch push status.
- Tag name + push status (when used).
- For `release`, include chosen bump level (major/minor/patch) and previous tag baseline.

Do not paste full diff/status output.
