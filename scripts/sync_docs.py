#!/usr/bin/env python3
"""
scripts/sync_docs.py - Documentation Sync Pipeline Script

Clones the target docs repository (songketmail/songketmail-product-pages),
wipes old docs content while preserving the .git folder, copies updated
Mintlify documentation from docs-source/, and commits/pushes changes back.
"""

import os
import shutil
import subprocess
from pathlib import Path

SOURCE_DIR = Path("docs-source")
DOCS_REPO = "songketmail/songketmail-product-pages"
BRANCH = "main"


def run(cmd, cwd=None):
    """Executes a shell command or list of argument tokens using subprocess.run."""
    subprocess.run(cmd, cwd=cwd, check=True, shell=isinstance(cmd, str))


def main():
    """Main execution function for syncing docs-source to songketmail-product-pages."""
    token = os.environ.get("DOCS_REPO_TOKEN")
    if not token:
        raise ValueError("DOCS_REPO_TOKEN environment variable is not set")

    tmp = Path("/tmp/docs-repo")
    if tmp.exists():
        shutil.rmtree(tmp)

    # Clone docs repo
    url = f"https://x-access-token:{token}@github.com/{DOCS_REPO}.git"
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
