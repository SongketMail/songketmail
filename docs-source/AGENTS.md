---
okf_version: "0.1"
type: "instructions"
title: "SongketMail Documentation Source AGENTS Instructions"
timestamp: "2026-08-22T20:45:00Z"
topics:
  - "mintlify"
  - "docs-source"
  - "songketmail"
  - "ai-instructions"
---

# SongketMail Documentation Source Instructions

## About this project

- This directory (`docs-source/`) is the single source of truth for SongketMail product documentation built on [Mintlify](https://mintlify.com).
- Documentation pages are written in MDX (`.mdx`) with YAML frontmatter.
- Site navigation and configuration live in `docs-source/docs.json`.
- Changes are automatically synchronized downstream to `songketmail/songketmail-product-pages` via `.github/workflows/sync-docs.yml` and `scripts/sync_docs.py`.

## Rules for AI Agents and Developers

- Always make documentation edits under `docs-source/` in this repository.
- Never edit the downstream `songketmail-product-pages` repository directly.
- Before committing changes to `docs-source/`, run `python3 scripts/sync_docs.py --dry-run` locally to verify navigation integrity and dry-run validation.
- When adding a new page to `docs.json` navigation, ensure the corresponding `.mdx` file exists under `docs-source/` in the same commit.

## Style Preferences

- Use active voice and second person ("you").
- Keep sentences concise and clear.
- Use sentence case for headings.
- Use bold for UI elements: Click **Settings**.
- Use code formatting for file names, commands, paths, and code references.

---

*SongketMail Documentation Architecture // DSOM AI Protocol Compliant*
