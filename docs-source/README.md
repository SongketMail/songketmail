# Songketmail Docs Repo

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
2. **Add `scripts/sync_docs.py`:**
   ```python
   import os
   import shutil
   import subprocess
   from pathlib import Path
   SOURCE_DIR = Path("docs-source")
   DOCS_REPO = "songketmail/songketmail-product-pages"
   BRANCH = "main"
   TOKEN = os.environ["DOCS_REPO_TOKEN"]
   def run(cmd, cwd=None):
       subprocess.run(cmd, cwd=cwd, check=True, shell=isinstance(cmd, str))
   def main():
       tmp = Path("/tmp/docs-repo")
       if tmp.exists():
           shutil.rmtree(tmp)
       # Clone docs repo
       url = f"https://x-access-token:{TOKEN}@github.com/{DOCS_REPO}.git"
       run(["git", "clone", "--branch", BRANCH, url, str(tmp)])
       # Wipe old docs content (keep .git)
       for item in tmp.iterdir():
           if item.name == ".git":
               continue
           if item.is_dir():
               shutil.rmtree(item)
           else:
               item.unlink()
       # Copy new content
       shutil.copytree(SOURCE_DIR, tmp, dirs_exist_ok=True)
       # Commit and push
       run(["git", "config", "user.email", "bot@songketmail.com"], cwd=tmp)
       run(["git", "config", "user.name", "Docs Sync Bot"], cwd=tmp)
       run(["git", "add", "-A"], cwd=tmp)
       result = subprocess.run(["git", "diff", "--staged", "--quiet"], cwd=tmp)
       if result.returncode == 0:
           print("No changes")
           return
       run(["git", "commit", "-m", "Sync docs from app repo"], cwd=tmp)
       run(["git", "push", "origin", BRANCH], cwd=tmp)
       print("Synced")
   if __name__ == "__main__":
       main()
   ```
3. **Add `.github/workflows/sync-docs.yml`:**
   ```yaml
   name: Sync Docs
   on:
     push:
       branches: [main]
       paths:
         - "docs-source/**"
   jobs:
     sync:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - uses: actions/setup-python@v5
           with:
             python-version: "3.11"
         - name: Sync docs
           env:
             DOCS_REPO_TOKEN: ${{ secrets.DOCS_REPO_TOKEN }}
           run: python scripts/sync_docs.py
   ```
4. **Create a fine-grained Personal Access Token:**
   - Go to [https://github.com/settings/tokens](https://github.com/settings/tokens) → **Fine-grained tokens** → **Generate new token**
   - Repository access: `songketmail/songketmail-product-pages`
   - Permissions: **Contents: Read and write**
   - Copy the token
5. **Add token as a secret in the app repo:**
   - `SongketMail/songketmail` → **Settings → Secrets and variables → Actions → New repository secret**
   - Name: `DOCS_REPO_TOKEN`
   - Value: paste token
6. **Test the pipeline:**
   - Make a small edit to a file under `docs-source/` in the app repo
   - Commit and push to `main`
   - Watch the workflow run in **Actions** tab
   - Confirm this repo receives the sync commit
   - Confirm [https://songketmail.mintlify.app](https://songketmail.mintlify.app) rebuilds

## Rules

- ❌ Do NOT edit files in this repo (`songketmail-product-pages`) directly
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

Any AI coding agent (Claude Code, Cursor, Copilot, etc.) should work against the **app repo only**:

1. Clone `SongketMail/songketmail`
2. Read `docs-source/` to understand current docs structure
3. Edit files under `docs-source/` only — never touch this repo (`songketmail-product-pages`) directly
4. Commit and push to `main` on the app repo
5. GitHub Actions auto-syncs `docs-source/` → this repo → Mintlify rebuilds

### Prompt to give an AI agent for docs tasks

```text
The docs for this project live in `docs-source/` in this repo.
Edit files there only. Do not touch any other docs repo.
When done, commit and push to main — a GitHub Actions workflow syncs
changes to the Mintlify deployment automatically.
```

## Reusable prompt for other projects

To set up the same pipeline for another Mintlify project, give this prompt to an AI coding agent (Claude Code, Cursor, etc.):

```text
I have two GitHub repos:
- App repo: <OWNER>/<APP_REPO> (where I write code and want to also edit docs)
- Docs repo: <OWNER>/<DOCS_REPO> (connected to Mintlify, auto-deploys to <SUBDOMAIN>.mintlify.app)

I want a one-way sync pipeline: when I push changes to `docs-source/` in the app repo,
a GitHub Actions workflow should copy those files into the docs repo's root on `main`,
so Mintlify rebuilds automatically.

Please do the following:

1. In the app repo, create `docs-source/` and copy the current contents of the docs
   repo into it as the starting point (all .mdx files, docs.json, images, logo, favicon).

2. Create `scripts/sync_docs.py` in the app repo that:
   - Clones the docs repo using a token from env var DOCS_REPO_TOKEN
   - Wipes existing content (keeping .git)
   - Copies everything from `docs-source/` into the clone
   - Commits with message "Sync docs from app repo" and pushes to main
   - Exits cleanly if there are no changes

3. Create `.github/workflows/sync-docs.yml` in the app repo that:
   - Triggers on push to `main` when files under `docs-source/**` change
   - Runs on ubuntu-latest with Python 3.11
   - Runs the sync script with DOCS_REPO_TOKEN from repository secrets

4. Update the docs repo's README.md to explain:
   - This repo is auto-synced and should NOT be edited directly
   - Where to edit docs (app repo, docs-source/ folder)
   - The full setup checklist (script, workflow, token, secret)
   - Include the sync_docs.py and workflow YAML inline for reference
   - Rules: don't edit docs repo directly, don't edit in Mintlify editor

5. Tell me the manual steps I still need to do:
   - Create a fine-grained GitHub Personal Access Token scoped to the docs repo
     with Contents: Read and write
   - Add it as secret `DOCS_REPO_TOKEN` in the app repo
   - Test the pipeline with a small edit

Constraints:
- Do NOT edit the docs repo directly (only via the sync pipeline once set up)
- Use fine-grained PAT, not classic tokens
- Sync should be idempotent (safe to re-run)
```

### Placeholders to swap per project

| Placeholder | Example |
| --- | --- |
| `<OWNER>/<APP_REPO>` | `SongketMail/songketmail` |
| `<OWNER>/<DOCS_REPO>` | `songketmail/songketmail-product-pages` |
| `<SUBDOMAIN>` | `songketmail` |

### Tips

- If the docs live in a subfolder of the docs repo (not root), tell the agent: "docs repo content directory is `docs/`, not root."
- If you use a branch other than `main`, specify it in the prompt.
- Two-way sync (edit either place) is not recommended — merge conflicts get ugly.

## Resources

- [Mintlify documentation](https://mintlify.com/docs)
- [Live site](https://songketmail.mintlify.app)
- [App repo (edit docs here)](https://github.com/SongketMail/songketmail)