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

# SongketMail Docs Repo

This repository (`songketmail/songketmail-product-pages`) is the **Mintlify docs deployment source** for [songketmail.mintlify.app](https://songketmail.mintlify.app).

> ⚠️ **Do not edit files in this repo directly.** This repo is auto-synced from the app repo. Manual changes here will be overwritten on the next sync.

## Where to edit docs

Edit docs in the app repo: [**SongketMail/songketmail**](https://github.com/SongketMail/songketmail) under the `docs-source/` folder.

On every push to `main` that touches `docs-source/`, a GitHub Actions workflow copies the contents into this repo and pushes to `main` here. Mintlify then rebuilds automatically.

```text
SongketMail/songketmail (app repo)
  └── docs-source/                    ← edit here
       ├── *.mdx
       └── docs.json
  └── .github/workflows/sync-docs.yml
  └── scripts/sync_docs.py

     ↓ (on push to main, paths: docs-source/**)

songketmail/songketmail-product-pages (this repo, auto-synced)
  └── *.mdx
  └── docs.json

     ↓ (Mintlify GitHub app watches main)

https://songketmail.mintlify.app
```

## Setup checklist

### ✅ Done

- Mintlify deployment `songketmail-email-services` created
- Git source connected: `songketmail/songketmail-product-pages` on `main`
- Live site: [https://songketmail.mintlify.app](https://songketmail.mintlify.app)

### ⬜ To do (in app repo `SongketMail/songketmail`)

1. **Create `docs-source/` folder** and copy the current contents of this repo into it (all `.mdx` files, `docs.json`, `logo/`, `favicon.svg`, etc.) as the starting point.
2. **Add `scripts/sync_docs.py`** with safety guards (Guard A–E, deletion cap, and navigation integrity checks).
3. **Add `.github/workflows/sync-docs.yml`** with `workflow_dispatch` inputs.
4. **Create a fine-grained Personal Access Token:**
   - Go to [https://github.com/settings/tokens](https://github.com/settings/tokens) → **Fine-grained tokens** → **Generate new token**
   - Repository access: `songketmail/songketmail-product-pages`
   - Permissions: **Contents: Read and write**
5. **Add token as a secret in the app repo:** `DOCS_REPO_TOKEN`
6. **Test the pipeline:** Run `python3 scripts/sync_docs.py --dry-run` and confirm validation passes.

## Rules

- ❌ Do NOT edit files in `songketmail-product-pages` directly
- ❌ Do NOT edit in the Mintlify web editor (changes will be overwritten)
- ✅ Only edit `docs-source/` in `SongketMail/songketmail`
- ✅ Push to `main` → auto-sync → Mintlify rebuild

## Local preview (in app repo)

```bash
cd docs-source
npm i -g mint
mint dev
```

Preview at [http://localhost:3000](http://localhost:3000).

## How AI agents work with this setup

Any AI coding agent (Claude Code, Cursor, Copilot, Jules, etc.) should work against the **app repo only**:

1. Clone `SongketMail/songketmail`
2. Read `docs-source/` to understand current docs structure
3. Edit files under `docs-source/` only — never touch `songketmail-product-pages` directly
4. Commit and push to `main` on the app repo
5. GitHub Actions auto-syncs `docs-source/` → `songketmail-product-pages` → Mintlify rebuilds

### Prompt to give an AI agent for docs tasks

```text
The docs for this project live in `docs-source/` in this repo.
Edit files there only. Do not touch any other docs repo.
When done, commit and push to main — a GitHub Actions workflow syncs
changes to the Mintlify deployment automatically.
```

## Incident: unsafe sync wiped pages (2026-08-22)

**What happened:** The first version of the sync pipeline had no safety guards. When `docs-source/` in the app repo was empty or partially populated, the workflow mirrored that empty state into the docs repo, deleting most `.mdx` files and emptying navigation in `docs.json`.

**Lesson:** A naive "wipe target, copy source" script will happily destroy the downstream repo if the source is not complete. The pipeline below (v2) adds mandatory safety guards.

**Recovery when this happens:**

```bash
git clone https://github.com/songketmail/songketmail-product-pages.git
cd songketmail-product-pages
git log --oneline
git revert <bad-sync-commit-sha>
git push origin main
```

Then fix `docs-source/` in the app repo and re-run the sync in dry-run mode before pushing.

## Reusable prompt for other projects (v2, hardened)

To set up the same pipeline for another Mintlify project WITHOUT the failure mode above, give this prompt to an AI coding agent:

```text
Set up a one-way docs sync pipeline between two GitHub repos with strict safety guards
so an empty or half-populated source can NEVER destroy the downstream docs repo.

REPOS
- App repo (source of truth, you work here):  <OWNER>/<APP_REPO>
- Docs repo (Mintlify-connected, downstream): <OWNER>/<DOCS_REPO>
- Mintlify subdomain:                         <SUBDOMAIN>.mintlify.app
- Branch on both repos:                       main
- Source folder in app repo:                  docs-source/
- Target in docs repo:                        repo root

GOAL
On push to main in the app repo that touches docs-source/**, sync docs-source/ into the
docs repo root. Mintlify rebuilds automatically. Sync is one-way. The docs repo is never
edited by humans or by other agents.

DELIVERABLES

1. docs-source/ folder in the app repo, seeded with the CURRENT contents of the docs
   repo (clone the docs repo first, copy every file including docs.json, .mdx pages,
   images, logo, favicon, .mintignore, README if any). Verify by running a recursive
   diff — docs-source/ and the docs repo root must be identical before any workflow
   runs for the first time.

2. scripts/sync_docs.py in the app repo. It MUST include all of the following safety
   guards. Any failed guard exits non-zero BEFORE touching the docs repo:

   Guard A — Source exists:
     - Fail if docs-source/ does not exist.
     - Fail if docs-source/docs.json is missing or not valid JSON.

   Guard B — Source is not suspiciously small:
     - Count .mdx files under docs-source/. Fail if count is below a floor.
     - Floor is read from an env var MIN_MDX_FILES (default 5). Print the count.

   Guard C — Navigation integrity:
     - Parse docs-source/docs.json. Walk navigation.tabs[].groups[].pages and
       navigation.groups[].pages (support both shapes, and nested groups).
     - For every page path referenced, assert that docs-source/<path>.mdx exists.
     - Fail with the list of missing files if any are missing.
     - Also warn (do not fail) on .mdx files present in docs-source/ but not
       referenced in navigation, so orphans are visible.

   Guard D — Diff preview:
     - Clone the docs repo to a temp dir using DOCS_REPO_TOKEN.
     - Compute the file-level diff between docs-source/ and the docs repo working
       tree: files_added, files_modified, files_deleted.
     - Print the three lists. Print counts.
     - Fail if files_deleted exceeds env var MAX_DELETIONS (default 10) UNLESS
       env var ALLOW_LARGE_DELETIONS=true is explicitly set. This catches the
       "wipe everything" failure mode.

   Guard E — Dry-run mode:
     - Support a --dry-run flag and a DRY_RUN=true env var. In dry-run, run
       guards A–D and print the plan, but do not commit or push.

   Only after all guards pass:
     - Wipe the docs repo working tree (keep .git).
     - Copy docs-source/ into it.
     - git add -A. If no staged changes, exit 0 with "No changes".
     - Commit with message "Sync docs from app repo @ <short-sha-of-app-repo>".
     - Push to main.

   Other requirements:
     - Use a fine-grained PAT from env var DOCS_REPO_TOKEN.
     - Configure git user "Docs Sync Bot" <bot@<subdomain>.com>.
     - Idempotent and safe to re-run.
     - Never force-push.
     - Print a final summary: files added / modified / deleted / total copied.

3. .github/workflows/sync-docs.yml in the app repo:

   - Trigger on push to main with paths filter docs-source/**.
   - Also expose a workflow_dispatch trigger with inputs:
       dry_run (boolean, default true)
       allow_large_deletions (boolean, default false)
       min_mdx_files (string, default "5")
       max_deletions (string, default "10")
   - Ubuntu-latest, Python 3.11.
   - Runs scripts/sync_docs.py.
   - Passes DOCS_REPO_TOKEN from repository secrets.
   - Passes DRY_RUN, ALLOW_LARGE_DELETIONS, MIN_MDX_FILES, MAX_DELETIONS from
     workflow_dispatch inputs (with sensible defaults on push events).
   - On failure, prints a clear message pointing at the failed guard.

4. Branch protection recommendation (tell the user to enable manually):
   - Protect main on the docs repo.
   - Allow pushes only from the sync bot / PAT owner.
   - This prevents accidental hand-edits that the next sync would overwrite anyway.

5. README.md in the DOCS repo:
   - State clearly: this repo is auto-synced from <APP_REPO>/docs-source/, do not
     edit here, do not edit in the Mintlify web editor.
   - Link to the app repo.
   - Include the recovery procedure.

6. AI agent instructions (add to app repo AGENTS.md or CONTRIBUTING.md):
   - Docs live in docs-source/ in this repo.
   - Never edit the downstream docs repo directly.
   - Never edit in the Mintlify web editor.
   - Before committing docs changes, run scripts/sync_docs.py --dry-run locally
     and confirm the diff looks correct.
   - If a docs.json navigation entry is added, the corresponding .mdx file must
     exist under docs-source/ in the same commit.

7. Recovery procedure (document in both READMEs):
   - If the docs repo is ever wiped or corrupted, revert the bad sync commit on
     the docs repo's main:
         git clone https://github.com/<OWNER>/<DOCS_REPO>.git
         cd <DOCS_REPO>
         git log --oneline
         git revert <bad-sync-sha>
         git push origin main
   - Then fix docs-source/ in the app repo and re-run the sync in dry-run mode
     before pushing.

MANUAL STEPS FOR THE USER

- Create a fine-grained Personal Access Token (Read/Write Contents for docs repo).
- Add it as repository secret DOCS_REPO_TOKEN in the app repo.
- Run the workflow manually with dry_run=true first, confirm the plan.
- Then run with dry_run=false to perform the first real sync.
- Enable branch protection on the docs repo main.
```

### Placeholders to swap per project

| Placeholder | Example |
| --- | --- |
| `<OWNER>/<APP_REPO>` | `SongketMail/songketmail` |
| `<OWNER>/<DOCS_REPO>` | `songketmail/songketmail-product-pages` |
| `<SUBDOMAIN>` | `songketmail` |

### What the guards prevent

| Guard | Prevents |
| --- | --- |
| A: Source exists | Sync running against a missing or renamed folder |
| B: Minimum file count | Empty or half-populated `docs-source/` wiping the docs repo |
| C: Navigation integrity | Broken links, empty groups, missing pages after sync |
| D: Deletion cap | Mass-delete accidents (the failure mode we already hit) |
| E: Dry-run | Anyone can preview a sync before it destroys anything |

## Resources

- [Mintlify documentation](https://mintlify.com/docs)
- [Live site](https://songketmail.mintlify.app)
- [App repo (edit docs here)](https://github.com/SongketMail/songketmail)
