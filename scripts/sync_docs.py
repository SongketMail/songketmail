#!/usr/bin/env python3
"""
scripts/sync_docs.py - Documentation Sync Pipeline Script

Clones the target docs repository (songketmail/songketmail-product-pages),
validates source content and docs.json navigation integrity, wipes downstream
docs content while preserving the .git folder, copies updated Mintlify documentation
from docs-source/, and commits/pushes changes back.
"""

import argparse
import json
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


def extract_pages_from_nav(nav_data):
    """Recursively extracts page paths from docs.json navigation structure."""
    pages = []
    if isinstance(nav_data, list):
        for item in nav_data:
            pages.extend(extract_pages_from_nav(item))
    elif isinstance(nav_data, dict):
        if "pages" in nav_data and isinstance(nav_data["pages"], list):
            for page in nav_data["pages"]:
                if isinstance(page, str):
                    pages.append(page)
                else:
                    pages.extend(extract_pages_from_nav(page))
        for key, value in nav_data.items():
            if key != "pages":
                pages.extend(extract_pages_from_nav(value))
    return pages


def resolve_page_path(source_dir: Path, page: str) -> bool:
    """Checks if a page referenced in docs.json navigation exists on disk."""
    if page.startswith("http://") or page.startswith("https://"):
        return True

    candidates = [
        source_dir / f"{page}.mdx",
        source_dir / f"{page}.md",
        source_dir / page,
        source_dir / page / "index.mdx",
        source_dir / page / "index.md",
    ]
    return any(candidate.exists() for candidate in candidates)


def validate_source_docs(source_dir: Path, min_files: int = 5):
    """Validates source documentation directory, docs.json, file count, and navigation targets."""
    if not source_dir.exists() or not source_dir.is_dir():
        raise ValueError(f"Source directory '{source_dir}' does not exist or is not a directory.")

    docs_json_path = source_dir / "docs.json"
    if not docs_json_path.exists():
        raise ValueError(f"Required configuration file '{docs_json_path}' is missing.")

    files = [f for f in source_dir.rglob("*") if f.is_file()]
    if len(files) < min_files:
        raise ValueError(
            f"Source directory '{source_dir}' contains {len(files)} file(s), "
            f"which is fewer than the required minimum threshold of {min_files}."
        )

    try:
        with open(docs_json_path, "r", encoding="utf-8") as f:
            docs_data = json.load(f)
    except Exception as err:
        raise ValueError(f"Failed to parse '{docs_json_path}': {err}") from err

    nav_data = docs_data.get("navigation", [])
    referenced_pages = extract_pages_from_nav(nav_data)
    missing_pages = [page for page in referenced_pages if not resolve_page_path(source_dir, page)]

    if missing_pages:
        missing_str = ", ".join(f"'{p}'" for p in missing_pages)
        raise ValueError(
            f"Navigation in '{docs_json_path}' references page(s) that do not exist: {missing_str}"
        )

    return files


def parse_args(args=None):
    """Parses command-line arguments for sync_docs.py."""
    parser = argparse.ArgumentParser(description="Documentation Sync Pipeline Script")
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=SOURCE_DIR,
        help="Path to source docs directory (default: docs-source)",
    )
    parser.add_argument(
        "--target-repo",
        type=str,
        default=DOCS_REPO,
        help="Target docs GitHub repository (default: songketmail/songketmail-product-pages)",
    )
    parser.add_argument(
        "--branch",
        type=str,
        default=BRANCH,
        help="Target branch (default: main)",
    )
    parser.add_argument(
        "--min-files",
        type=int,
        default=5,
        help="Minimum required file count in source directory (default: 5)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate source and preview changes without modifying downstream repository",
    )
    return parser.parse_args(args)


def main(cli_args=None):
    """Main execution function for syncing source docs to target docs repo."""
    parsed_args = parse_args(cli_args)
    source_dir = parsed_args.source_dir
    target_repo = parsed_args.target_repo
    branch = parsed_args.branch
    min_files = parsed_args.min_files
    dry_run = parsed_args.dry_run

    # Safety Guard Validation Check
    source_files = validate_source_docs(source_dir, min_files=min_files)

    if dry_run:
        print("=== DRY RUN MODE ===")
        print(f"Source Directory: {source_dir} ({len(source_files)} files verified)")
        print(f"Target Repository: {target_repo} (branch: {branch})")
        print(f"Minimum File Floor Threshold: {min_files}")
        print("Safety guards passed successfully! No downstream modifications performed.")
        return

    token = os.environ.get("DOCS_REPO_TOKEN")
    if not token:
        raise ValueError("DOCS_REPO_TOKEN environment variable is not set")

    tmp = Path("/tmp/docs-repo")
    if tmp.exists():
        shutil.rmtree(tmp)

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

        url = f"https://github.com/{target_repo}.git"
        run(["git", "clone", "--branch", branch, url, str(tmp)], env=git_env)

        # Print Pre-Wipe Summary
        existing_items = [item for item in tmp.iterdir() if item.name != ".git"]
        print(f"Pre-wipe check: target repository has {len(existing_items)} top-level items.")
        print(f"Wiping target repository and copying {len(source_files)} files from {source_dir}...")

        # Wipe old docs content (keep .git)
        for item in tmp.iterdir():
            if item.name == ".git":
                continue
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()

        # Copy new content
        shutil.copytree(source_dir, tmp, dirs_exist_ok=True)

        # Commit and push
        run(["git", "config", "user.email", "bot@songketmail.com"], cwd=tmp)
        run(["git", "config", "user.name", "Docs Sync Bot"], cwd=tmp)
        run(["git", "add", "-A"], cwd=tmp)
        result = subprocess.run(["git", "diff", "--staged", "--quiet"], cwd=tmp)
        if result.returncode == 0:
            print("No changes")
            return
        elif result.returncode == 1:
            pass
        else:
            result.check_returncode()

        run(["git", "commit", "-m", "Sync docs from app repo"], cwd=tmp)
        run(["git", "push", "origin", branch], cwd=tmp, env=git_env)
        print("Synced")
    finally:
        shutil.rmtree(askpass_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
