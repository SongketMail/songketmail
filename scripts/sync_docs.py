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
import tempfile
from pathlib import Path

SOURCE_DIR = Path("docs-source")
DOCS_REPO = "songketmail/songketmail-product-pages"
BRANCH = "main"


def run(cmd, cwd=None, env=None):
    """Executes a shell command or list of argument tokens using subprocess.run."""
    subprocess.run(cmd, cwd=cwd, env=env, check=True, shell=isinstance(cmd, str))


def main():
    """Main execution function for syncing docs-source to songketmail-product-pages."""
    token = os.environ.get("DOCS_REPO_TOKEN")
    if not token:
        raise ValueError("DOCS_REPO_TOKEN environment variable is not set")

    tmp = Path("/tmp/docs-repo")
    if tmp.exists():
        shutil.rmtree(tmp)

    # Set up GIT_ASKPASS script to avoid embedding tokens in git URLs or parameters
    askpass_dir = Path(tempfile.mkdtemp(prefix="git_askpass_"))
    askpass_script = askpass_dir / "askpass.sh"
    try:
        with open(askpass_script, "w", encoding="utf-8") as f:
            f.write("#!/bin/sh\n")
            f.write(f'echo "{token}"\n')
        askpass_script.chmod(0o700)

        git_env = dict(os.environ)
        git_env["GIT_ASKPASS"] = str(askpass_script)
        git_env["GIT_TERMINAL_PROMPT"] = "0"

        # Clone docs repo with clean URL
        url = f"https://github.com/{DOCS_REPO}.git"
        run(["git", "clone", "--branch", BRANCH, url, str(tmp)], env=git_env)

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
        elif result.returncode == 1:
            pass  # Staged diff exists; proceed to commit flow
        else:
            result.check_returncode()

        run(["git", "commit", "-m", "Sync docs from app repo"], cwd=tmp)
        run(["git", "push", "origin", BRANCH], cwd=tmp, env=git_env)
        print("Synced")
    finally:
        shutil.rmtree(askpass_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
