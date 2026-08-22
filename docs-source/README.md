---
okf_version: "0.1"
type: "documentation"
title: "SongketMail Documentation Sync Architecture & Workflow Guide"
timestamp: "2026-08-22T20:45:00Z"
topics:
  - "mintlify"
  - "docs-source"
  - "github-actions"
  - "sync-pipeline"
---

# SongketMail Product Documentation Source

This directory (`docs-source/`) in [SongketMail/songketmail](https://github.com/SongketMail/songketmail) is the primary source of truth for the product pages documentation hosted on [songketmail.mintlify.app](https://songketmail.mintlify.app).

> ⚠️ **Important:** Do not edit the downstream `songketmail/songketmail-product-pages` repository directly or via the Mintlify web editor. All edits must be made inside `docs-source/` in this repository.

## Pipeline Overview

When changes under `docs-source/**` are pushed to `main`, `.github/workflows/sync-docs.yml` triggers `scripts/sync_docs.py` to validate source integrity and synchronize files to `songketmail/songketmail-product-pages`. Mintlify then automatically rebuilds the live site.

```text
SongketMail/songketmail (App Repo)
  └── docs-source/                     ← Primary source of truth
       ├── *.mdx
       └── docs.json
  └── .github/workflows/sync-docs.yml
  └── scripts/sync_docs.py

     ↓ (on push to main / workflow_dispatch)

songketmail/songketmail-product-pages (Downstream Repo)
  └── *.mdx
  └── docs.json

     ↓ (Mintlify webhook trigger)

https://songketmail.mintlify.app
```

## Safety Guards in `scripts/sync_docs.py`

`scripts/sync_docs.py` includes multi-tier safety checks before making downstream modifications:

- **Guard A (Source & Config Existence):** Fails fast if `docs-source/` or `docs-source/docs.json` is missing or invalid.
- **Guard B (Minimum File Threshold):** Fails fast if total file count is below `MIN_MDX_FILES` (default 5).
- **Guard C (Navigation Integrity & Orphan Warnings):** Validates every page string in `docs.json` navigation resolves to an actual `.mdx`/`.md` file. Warns on orphan `.mdx` files not referenced in navigation.
- **Guard D (Deletion Cap Protection):** Computes file diffs and fails fast if deleted files exceed `MAX_DELETIONS` (default 10) unless `ALLOW_LARGE_DELETIONS=true` is set.
- **Guard E (Dry-Run Mode):** Supports `--dry-run` and `DRY_RUN=true` to validate source integrity and preview changes without modifying downstream git state.
- **Credential Security:** Authenticates via fine-grained PAT `DOCS_REPO_TOKEN` using `GIT_ASKPASS` to prevent token exposure in git URLs or execution logs.

## Local Testing

To validate documentation changes locally before pushing:

```bash
# Run local dry-run sync validation
python3 scripts/sync_docs.py --dry-run

# Local Mintlify preview (if Mintlify CLI is installed)
cd docs-source
mint dev
```

## Recovery Procedure

If the downstream docs repository is ever corrupted or accidentally wiped:

```bash
# 1. Clone downstream docs repository
git clone https://github.com/songketmail/songketmail-product-pages.git
cd songketmail-product-pages

# 2. Identify the bad commit SHA and revert it
git log --oneline
git revert <bad-sync-commit-sha>
git push origin main

# 3. Verify docs-source/ in app repo, run dry-run, and re-trigger sync
python3 scripts/sync_docs.py --dry-run
```

---

*SongketMail Product Documentation Architecture // DSOM AI Protocol Compliant*
