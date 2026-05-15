---
name: commit-and-sync
description: Stage local changes, draft a commit message from the diff, commit, push to the tracked branch, and optionally tag. Supports `release` to auto-bump semver from changes since the last release tag.
---

# commit-and-sync

Commit working-tree changes and sync to the remote. Optionally tag.

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

If no changes and no tag/release requested: stop, report "nothing to commit".
If no changes but tag/release requested: skip commit, continue to tagging.

## Step 2 — Draft commit message (only when changes exist)

Read the diff and write one subject line capturing intent. Avoid generic subjects and file-name laundry lists.

**Safety check**: if the diff contains likely secret material (`.env`, `*credentials*`, `*secret*`, private key / API key patterns), stop and ask before staging.

## Step 3 — Stage, commit, push

```bash
git add -A
git commit -m "<subject>"
git push
```

No upstream? `git push -u origin <current-branch>`.

Never force-push. Never `--no-verify`.

## Step 4 — Resolve release tag (only for `release`, no explicit tag)

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

## Step 5 — Validate and push tag

Validate not blank, not existing locally (`git rev-parse -q --verify "refs/tags/<tag>"`), not existing on origin (`git ls-remote --tags origin "refs/tags/<tag>"`).

```bash
git tag -a "<tag>" -m "<tag>"
git push origin "<tag>"
```

Never force-push tags.

## Step 6 — Report

1-2 sentences: commit subject + short SHA (or "no commit needed"); branch push status; tag name + push status (if used); for `release`, chosen bump level and previous tag baseline.

Do not paste full diff/status output.
