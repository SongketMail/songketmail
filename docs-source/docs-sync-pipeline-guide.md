---
okf_version: "0.1"
type: "documentation"
title: "Documentation Sync Pipeline & GitHub Actions Setup Guide"
description: "Comprehensive guide to configuring, troubleshooting, and maintaining the automated Mintlify documentation synchronization pipeline for SongketMail."
resource: "file:///docs/docs-sync-pipeline-guide.md"
timestamp: 2026-08-22T12:00:00Z
topics: [github-actions, mintlify, docs-sync, secrets, automation, songketmail]
---

# 📚 Part 27: Documentation Sync Pipeline & GitHub Actions Setup Guide

## 📋 Executive Overview

SongketMail maintains its public product and developer documentation using **Mintlify**. To preserve single-source-of-truth integrity, documentation source files (`.mdx` files and `docs.json`) are maintained directly within the core repository under `docs-source/`.

Whenever modifications are pushed to the `main` branch inside `docs-source/`, an automated GitHub Actions pipeline (`.github/workflows/sync-docs.yml`) executes `scripts/sync_docs.py`. This pipeline clones the target public product pages repository (`songketmail/songketmail-product-pages`), synchronizes the latest `.mdx` content, and automatically commits and pushes the updates.

This guide details the complete architecture of the documentation sync pipeline, analyzes common failure modes, documents the 2026-08-22 incident and recovery procedure, and provides the hardened v2 pipeline setup walkthrough.

---

## 🏗️ Pipeline Architecture

The documentation sync mechanism operates across two distinct GitHub repositories:

```text
+------------------------------------+          +--------------------------------------------+
|      SongketMail/songketmail       |          |  songketmail/songketmail-product-pages     |
|   (Core Application Repository)    |          |       (Mintlify Host Repository)           |
+------------------------------------+          +--------------------------------------------+
                  |                                                   ^
  Push to main    |                                                   |
  (docs-source/)  v                                                   |
+------------------------------------+                                |
|  .github/workflows/sync-docs.yml   |                                |
|  - Triggers Python Sync Pipeline   |                                |
|  - Injects DOCS_REPO_TOKEN         |                                |
+------------------------------------+                                |
                  |                                                   |
                  v                                                   |
+------------------------------------+                                |
|       scripts/sync_docs.py         |                                |
|  - Validates DOCS_REPO_TOKEN       |                                |
|  - Validates Guards A - E          |                                |
|  - Ephemeral GIT_ASKPASS Auth      |                                |
|  - Clones product-pages repo       |                                |
|  - Synchronizes docs-source/       |                                |
|  - Commits & Pushes updates -------|--------------------------------+
+------------------------------------+
```

### Components

1. **`docs-source/` Directory:** Contains the raw Mintlify documentation source files (`docs.json`, `index.mdx`, `quickstart.mdx`, and product pages).
2. **`.github/workflows/sync-docs.yml`:** GitHub Actions workflow triggered on push events targeting `docs-source/**` on branch `main` or manual `workflow_dispatch`.
3. **`scripts/sync_docs.py`:** Zero-dependency Python script that validates source integrity, navigation completeness, and deletion thresholds before performing git clone, synchronization, commit, and push via `GIT_ASKPASS`.
4. **`songketmail/songketmail-product-pages`:** Target repository that hosts the compiled Mintlify product documentation pages.

---

## 🚨 Incident Report: Unsafe Sync Wiped Pages (2026-08-22)

### What Happened
The initial implementation of `scripts/sync_docs.py` lacked pre-sync validation guards. When `docs-source/` was initially committed with only starter files, the sync script cloned the downstream `songketmail-product-pages` repository, wiped its working tree, and copied the partial `docs-source/` state over it. This deleted most `.mdx` files and emptied the navigation in `docs.json`.

### Root Cause
A naive "wipe target, copy source" script will delete downstream content if `docs-source/` is empty, partially populated, or missing navigation references.

### Recovery Procedure

If the downstream docs repository is ever wiped or corrupted, run the following recovery commands:

```bash
# 1. Clone downstream repository
git clone https://github.com/songketmail/songketmail-product-pages.git
cd songketmail-product-pages

# 2. Identify the bad sync commit and revert it
git log --oneline
git revert <bad-sync-commit-sha>
git push origin main

# 3. Restore docs-source/ in app repo, verify in dry-run mode, and re-run sync
python3 scripts/sync_docs.py --dry-run
```

---

## 🛡️ Multi-Layered Pipeline Safety Guards (v2)

To permanently prevent destructive syncs, `scripts/sync_docs.py` enforces five mandatory safety guards (Guards A–E):

| Guard | Validation Rule | Prevented Failure Mode |
|---|---|---|
| **Guard A: Source Exists** | Asserts `docs-source/` directory and valid `docs.json` exist. | Syncing against a missing or renamed folder |
| **Guard B: Minimum File Floor** | Asserts total file count meets or exceeds `MIN_MDX_FILES` (default 5). | Empty or half-populated `docs-source/` wiping downstream repo |
| **Guard C: Navigation Integrity** | Parses `docs.json` navigation and asserts every page path resolves to a file on disk. Warns on orphan pages. | Broken links, empty navigation groups, and missing pages |
| **Guard D: Deletion Cap Protection** | Computes file diffs and fails if deleted files exceed `MAX_DELETIONS` (default 10) unless `ALLOW_LARGE_DELETIONS=true` is set. | Mass-deletion accidents |
| **Guard E: Dry-Run Mode** | Supports `--dry-run` and `DRY_RUN=true` env var to validate source and preview diff without pushing. | Accidental downstream modifications during testing |

---

## 🛠️ Step-by-Step Setup & Configuration Guide

To configure the runtime sync token and workflow parameters:

### Two-Token Model & Separation of Duties

1. **Admin / Bootstrap Credential (`ADMIN_SECRET_PAT`):** A temporary, high-privilege Personal Access Token used solely by an administrator to configure secrets via the GitHub API (`/actions/secrets`).
2. **Runtime Deployment Token (`DOCS_REPO_TOKEN`):** A dedicated, fine-grained Personal Access Token stored securely as a repository secret (`DOCS_REPO_TOKEN`). This token is injected into the runtime sync job and is strictly limited to content write permissions (`Contents: Read and write`) on `songketmail/songketmail-product-pages`.

---

### Option A: Configuration via GitHub REST API (Automated)

```bash
python3 -m pip install PyNaCl
```

```python
import os
import json
import base64
import getpass
import urllib.request
from nacl import encoding, public

ADMIN_SECRET_PAT = os.environ.get("ADMIN_SECRET_PAT") or getpass.getpass("Enter Admin Secret Mgmt PAT: ")
DEPLOYMENT_PAT = os.environ.get("DEPLOYMENT_PAT") or getpass.getpass("Enter Deployment Fine-Grained PAT: ")
REPO = os.environ.get("GITHUB_REPOSITORY", "SongketMail/songketmail")

req = urllib.request.Request(
    f"https://api.github.com/repos/{REPO}/actions/secrets/public-key",
    headers={
        "Authorization": f"token {ADMIN_SECRET_PAT}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "SongketMail-DocsSync"
    }
)
with urllib.request.urlopen(req) as response:
    key_data = json.loads(response.read().decode())

public_key = key_data["key"]
key_id = key_data["key_id"]

public_key_obj = public.PublicKey(public_key.encode("utf-8"), encoding.Base64Encoder)
sealed_box = public.SealedBox(public_key_obj)
encrypted = sealed_box.encrypt(DEPLOYMENT_PAT.encode("utf-8"))
encrypted_value = base64.b64encode(encrypted).decode("utf-8")

data = json.dumps({"encrypted_value": encrypted_value, "key_id": key_id}).encode("utf-8")
put_req = urllib.request.Request(
    f"https://api.github.com/repos/{REPO}/actions/secrets/DOCS_REPO_TOKEN",
    data=data,
    headers={
        "Authorization": f"token {ADMIN_SECRET_PAT}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "SongketMail-DocsSync"
    },
    method="PUT"
)

with urllib.request.urlopen(put_req) as resp:
    print(f"Successfully configured secret DOCS_REPO_TOKEN (HTTP Status {resp.status})")
```

---

### Option B: Configuration via GitHub Web UI (Manual)

1. **Generate Fine-Grained Personal Access Token for Runtime Sync:**
   - Go to **GitHub Settings -> Developer Settings -> Personal Access Tokens -> Fine-grained tokens**.
   - Repository access: **Only select repositories** -> `songketmail/songketmail-product-pages`.
   - Permissions: **Contents -> Read and write**.
2. **Add Repository Secret in Core Repository:**
   - Go to `https://github.com/SongketMail/songketmail` -> **Settings** -> **Secrets and variables** -> **Actions**.
   - Create secret `DOCS_REPO_TOKEN` with the fine-grained token value.
3. **Re-run Workflow in Dry-Run Mode:**
   - Go to **Actions** -> **Sync Docs** -> **Run workflow** (dry_run: true).

---

## 🔒 Security Best Practices

1. **Credential Isolation via `GIT_ASKPASS`:** `scripts/sync_docs.py` avoids embedding tokens into git remote URLs. It dynamically generates an isolated temporary shell script and sets `GIT_ASKPASS`.
2. **Least Privilege Principles:** Runtime sync bot (`bot@songketmail.com`) is assigned a fine-grained PAT restricted strictly to contents write permissions on `songketmail/songketmail-product-pages`.
3. **Concurrency Control:** Workflow includes concurrency controls (`group: sync-docs-${{ github.ref }}`, `cancel-in-progress: true`) to prevent race conditions during rapid consecutive pushes.

---

## 💻 Local Mintlify Documentation Preview

Before committing changes to `docs-source/`, run local validation and preview:

```bash
# Validate sync guards locally in dry-run mode
python3 scripts/sync_docs.py --dry-run

# Run local Mintlify server
cd docs-source
npm i -g mint
mint dev
```

Local preview server runs at [http://localhost:3000](http://localhost:3000).

---

## 🚫 Governance & Synchronisation Rules

- ❌ **Do NOT edit files directly in `songketmail-product-pages`:** Manual edits will be permanently overwritten by the automated sync script.
- ❌ **Do NOT use the Mintlify Web Editor directly:** Web editor commits target `songketmail-product-pages` directly and will be overwritten on the next push.
- ✅ **Single Source of Truth:** Only edit documentation source files (`.mdx`, `docs.json`, assets) under `docs-source/` within the main application repository (`SongketMail/songketmail`).
- ✅ **Automated Build Trigger:** Pushing modifications to `main` under `docs-source/**` automatically triggers `.github/workflows/sync-docs.yml` and updates [https://songketmail.mintlify.app](https://songketmail.mintlify.app).

---

## 📊 Verification & Operational Summary

To confirm operational readiness:

1. **Test dry-run execution:**
   ```bash
   python3 scripts/sync_docs.py --dry-run
   ```
2. **Verify target repository commit history:** Check `https://github.com/songketmail/songketmail-product-pages/commits/main` for sync commits.

---

*Deep State of Mind (DSOM) For My AI Protocol | Harisfazillah Jamel (LinuxMalaysia) | 2026-08-22*
*Standard: UK English | DBP-standard Bahasa Melayu Malaysia (Piawai) | GNU General Public License v3.0*
