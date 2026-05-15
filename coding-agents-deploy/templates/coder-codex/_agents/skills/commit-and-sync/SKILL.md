---
name: commit-and-sync
description: Commit working-tree changes and sync to the remote, with optional `release` semver auto-bump or `--tag` explicit tag. Use when the user wants a one-shot commit + push, or asks to release a new version.
---

# Commit and Sync

Use `.agents/commands/commit-and-sync.md` as the canonical workflow. Read it before staging anything, then follow it exactly.

Do not force-push. Do not skip hooks. Safety-check the diff for secret material before staging.
