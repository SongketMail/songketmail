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

This guide details the complete architecture of the documentation sync pipeline, analyzes common failure modes (such as missing `DOCS_REPO_TOKEN` secrets), and provides a step-by-step setup walkthrough for administrators and automated agents.

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
|  - Ephemeral GIT_ASKPASS Auth      |                                |
|  - Clones product-pages repo       |                                |
|  - Synchronizes docs-source/       |                                |
|  - Commits & Pushes updates -------|--------------------------------+
+------------------------------------+
```

### Components

1. **`docs-source/` Directory:** Contains the raw Mintlify documentation source files (`docs.json`, `index.mdx`, `quickstart.mdx`).
2. **`.github/workflows/sync-docs.yml`:** GitHub Actions workflow triggered on push events targeting `docs-source/**` on branch `main`.
3. **`scripts/sync_docs.py`:** Standalone, zero-dependency Python script that safely performs git clone, file synchronization, git commit, and git push using an isolated `GIT_ASKPASS` credential helper.
4. **`songketmail/songketmail-product-pages`:** Target repository that hosts the compiled Mintlify product documentation pages.

---

## 🚨 Root Cause Analysis: `ValueError: DOCS_REPO_TOKEN environment variable is not set`

### Error Traceback
When the workflow executes without `DOCS_REPO_TOKEN` configured in repository secrets, the build fails with the following log output:

```text
Traceback (most recent call last):
  File "/home/runner/work/songketmail/songketmail/scripts/sync_docs.py", line 86, in <module>
    main()
  File "/home/runner/work/songketmail/songketmail/scripts/sync_docs.py", line 30, in main
    raise ValueError("DOCS_REPO_TOKEN environment variable is not set")
ValueError: DOCS_REPO_TOKEN environment variable is not set
Error: Process completed with exit code 1.
```

### Cause & Mechanism
In `.github/workflows/sync-docs.yml`, the workflow passes `DOCS_REPO_TOKEN` into the environment via GitHub Secrets:

{% raw %}
```yaml
      - name: Sync docs
        env:
          DOCS_REPO_TOKEN: ${{ secrets.DOCS_REPO_TOKEN }}
        run: python scripts/sync_docs.py
```
{% endraw %}

If `DOCS_REPO_TOKEN` has not been added to the repository's **Settings -> Secrets and variables -> Actions**, `${{ secrets.DOCS_REPO_TOKEN }}` evaluates to an empty string. `scripts/sync_docs.py` detects this missing token during initialization and deliberately aborts execution before attempting any git operations:

```python
token = os.environ.get("DOCS_REPO_TOKEN")
if not token:
    raise ValueError("DOCS_REPO_TOKEN environment variable is not set")
```

---

## 🛠️ Step-by-Step Setup & Configuration Guide

To resolve this failure and enable seamless documentation synchronization, follow these configuration steps:

### Two-Token Model & Separation of Duties

To maintain strong operational security, the deployment architecture strictly distinguishes between two separate types of tokens:

1. **Admin / Bootstrap Credential (`ADMIN_SECRET_PAT`):** A temporary, high-privilege Personal Access Token used solely by an administrator or automated setup tool to manage repository secrets via the GitHub REST API (`/actions/secrets`). This credential is **never** stored inside repository secrets or passed into runtime workflow steps.
2. **Runtime Deployment Token (`DOCS_REPO_TOKEN`):** A dedicated, fine-grained Personal Access Token (or bot token) stored securely as a repository secret (`DOCS_REPO_TOKEN`). This token is injected into the runtime sync job and is strictly limited to content write permissions (`Contents: Read and write`) on the target repository (`songketmail/songketmail-product-pages`). It has zero access to manage secrets or access administrative settings in the core repository.

---

### Option A: Configuration via GitHub REST API (Automated)

#### Prerequisites & Dependency Installation
Before running the automated Python script, install the `PyNaCl` library (which binds libsodium for sealed-box public key encryption):

```bash
python3 -m pip install PyNaCl
```

> **🔒 Critical Security Directive:** Real tokens and credentials must **never** be hardcoded or committed to source control. In the script below, tokens are safely retrieved at runtime from environment variables (`ADMIN_SECRET_PAT` and `DEPLOYMENT_PAT`) or interactive user prompts using `getpass.getpass()`.

```python
import os
import json
import base64
import getpass
import urllib.request
from nacl import encoding, public

# 1. Retrieve Credentials safely from Environment Variables or Prompt (Never Hardcoded)
ADMIN_SECRET_PAT = os.environ.get("ADMIN_SECRET_PAT") or getpass.getpass("Enter Admin Secret Mgmt PAT: ")
DEPLOYMENT_PAT = os.environ.get("DEPLOYMENT_PAT") or getpass.getpass("Enter Deployment Fine-Grained PAT: ")
REPO = os.environ.get("GITHUB_REPOSITORY", "SongketMail/songketmail")

# 2. Fetch Repository Public Key using Admin Credential
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

# 3. Encrypt the Fine-Grained Deployment Token using libsodium / PyNaCl
public_key_obj = public.PublicKey(public_key.encode("utf-8"), encoding.Base64Encoder)
sealed_box = public.SealedBox(public_key_obj)
encrypted = sealed_box.encrypt(DEPLOYMENT_PAT.encode("utf-8"))
encrypted_value = base64.b64encode(encrypted).decode("utf-8")

# 4. Upload DOCS_REPO_TOKEN Secret using Admin Credential
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
   - Navigate to **GitHub Settings -> Developer Settings -> Personal Access Tokens -> Fine-grained tokens**.
   - Click **Generate new token**.
   - **Repository access:** Select **Only select repositories** -> `songketmail/songketmail-product-pages`.
   - **Permissions:** Under **Repository permissions**, set **Contents** to **Access: Read and write**.
   - Click **Generate token** and copy the resulting string (`github_pat_...`).

2. **Add Repository Secret in Core Repository:**
   - Go to `https://github.com/SongketMail/songketmail`.
   - Click **Settings** -> **Secrets and variables** -> **Actions**.
   - Click **New repository secret**.
   - **Name:** `DOCS_REPO_TOKEN`
   - **Secret:** Paste the fine-grained deployment token (`github_pat_...`).
   - Click **Add secret**.

3. **Re-run Failed Workflow:**
   - Go to **Actions** -> **Sync Docs**.
   - Select the failed workflow run (e.g., Run `#32564758784`).
   - Click **Re-run all jobs**.

---

## 🔒 Security Best Practices

1. **Credential Isolation via `GIT_ASKPASS`:**
   `scripts/sync_docs.py` avoids embedding tokens into git remote URLs (e.g., `https://token@github.com/...`) which can inadvertently expose secrets in shell logs or process lists. Instead, it dynamically generates an isolated temporary shell script and sets `GIT_ASKPASS`:
   ```python
   askpass_script = askpass_dir / "askpass.sh"
   with open(askpass_script, "w", encoding="utf-8") as f:
       f.write("#!/bin/sh\n")
       f.write(f'echo "{token}"\n')
   askpass_script.chmod(0o700)
   ```
   Upon execution, the temporary directory and credential script are securely removed in a `finally:` block.

2. **Least Privilege Principles:**
   Dedicated bot accounts (e.g., `bot@songketmail.com` / `Docs Sync Bot`) should be assigned fine-grained PAT tokens restricted strictly to contents write permissions on `songketmail/songketmail-product-pages`.

3. **Concurrency Control:**
   The GitHub Actions workflow includes concurrency controls (`group: sync-docs-{% raw %}${{ github.ref }}{% endraw %}`, `cancel-in-progress: true`) to prevent race conditions during rapid consecutive pushes.

---

## 💻 Local Mintlify Documentation Preview

Before committing changes to `docs-source/`, developers can run Mintlify locally to preview changes in real time:

```bash
cd docs-source
npm i -g mint
mint dev
```

The local preview server will run at [http://localhost:3000](http://localhost:3000).

---

## 🚫 Governance & Synchronisation Rules

To prevent broken builds, documentation drift, and lost changes across repositories, strictly observe these governance rules:

- ❌ **Do NOT edit files directly in `songketmail-product-pages`:** Manual edits in the product pages repository will be permanently overwritten by the automated sync script during the next pipeline execution.
- ❌ **Do NOT use the Mintlify Web Editor directly:** Web editor commits target `songketmail-product-pages` directly and will be overwritten on the next push from `docs-source/`.
- ✅ **Single Source of Truth:** Only edit documentation source files (`.mdx`, `docs.json`, assets) under `docs-source/` within the main application repository (`SongketMail/songketmail`).
- ✅ **Automated Build Trigger:** Pushing modifications to `main` under `docs-source/**` automatically triggers `.github/workflows/sync-docs.yml`, updates `songketmail-product-pages`, and triggers automatic deployment rebuilds on [https://songketmail.mintlify.app](https://songketmail.mintlify.app).

---

## 📊 Verification & Operational Summary

To confirm that the documentation sync pipeline is operating correctly:

1. **Check Repository Secret Presence via GitHub API:**
   ```bash
   curl -s -H "Authorization: token <YOUR_PAT>" \
        -H "Accept: application/vnd.github+json" \
        https://api.github.com/repos/SongketMail/songketmail/actions/secrets
   ```
   Output must show `DOCS_REPO_TOKEN` under the list of repository secrets.

2. **Verify Target Repository Commit History:**
   Check `https://github.com/songketmail/songketmail-product-pages/commits/main` for recent commits authored by `Docs Sync Bot` with commit message `Sync docs from app repo`.

---

*Deep State of Mind (DSOM) For My AI Protocol | Harisfazillah Jamel (LinuxMalaysia) | 2026-08-22*
*Standard: UK English | DBP-standard Bahasa Melayu Malaysia (Piawai) | GNU General Public License v3.0*
