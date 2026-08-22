#!/usr/bin/env python3
"""
scripts/sync_docs.py - Documentation Sync Pipeline Script

Clones the target docs repository (songketmail/songketmail-product-pages),
validates source content and docs.json navigation integrity, checks deletion caps,
wipes downstream docs content while preserving the .git folder, copies updated
Mintlify documentation from docs-source/, and commits/pushes changes back.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SOURCE_DIR = Path("docs-source")
DOCS_REPO = "songketmail/songketmail-product-pages"
BRANCH = "main"


def run(cmd, cwd=None, env=None):
    """Executes a shell command or list of argument tokens using subprocess.run."""
    subprocess.run(cmd, cwd=cwd, env=env, check=True, shell=isinstance(cmd, str))


def extract_pages_from_nav(nav_data):
    """
    Collect page references from a nested documentation navigation structure.
    
    Parameters:
        nav_data: Navigation data containing nested lists and dictionaries.
    
    Returns:
        list: Page reference strings found in the navigation structure.
    """
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
    """Determine whether a navigation page reference resolves to an existing source file."""
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
    """
    Validate the source documentation directory and its navigation configuration.
    
    Parameters:
    	source_dir (Path): Directory containing the source documentation and `docs.json`.
    	min_files (int): Minimum number of files required in the source directory.
    
    Returns:
    	files (list[Path]): Files found recursively in the source directory.
    
    Raises:
    	ValueError: If the source directory, configuration file, or navigation targets are invalid, if `docs.json` cannot be parsed, or if the file count is below `min_files`.
    """
    if not source_dir.exists() or not source_dir.is_dir():
        raise ValueError(f"Source directory '{source_dir}' does not exist or is not a directory.")

    docs_json_path = source_dir / "docs.json"
    if not docs_json_path.exists():
        raise ValueError(f"Required configuration file '{docs_json_path}' is missing.")

    files = [f for f in source_dir.rglob("*") if f.is_file()]
    mdx_files = [f for f in files if f.suffix == ".mdx"]

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

    # Orphan .mdx detection warning
    referenced_set = set()
    for p in referenced_pages:
        referenced_set.add(p)
        referenced_set.add(f"{p}.mdx")

    for mdx_file in mdx_files:
        rel_path = mdx_file.relative_to(source_dir)
        rel_str = str(rel_path)
        stem_str = str(rel_path.with_suffix(""))
        if rel_str not in referenced_set and stem_str not in referenced_set:
            print(f"Warning: Orphan MDX file found (not referenced in docs.json navigation): {rel_path}")

    return files


def compute_file_diff(target_dir: Path, source_dir: Path):
    """
    Compare source and target files and identify additions, modifications, and deletions.
    
    Parameters:
    	target_dir (Path): Directory containing the existing target files.
    	source_dir (Path): Directory containing the source files.
    
    Returns:
    	tuple: Lists of relative paths for added, modified, and deleted files, respectively.
    """
    target_files = {
        f.relative_to(target_dir): f
        for f in target_dir.rglob("*")
        if f.is_file() and ".git" not in f.parts
    }
    source_files = {
        f.relative_to(source_dir): f
        for f in source_dir.rglob("*")
        if f.is_file()
    }

    files_added = [rel for rel in source_files if rel not in target_files]
    files_deleted = [rel for rel in target_files if rel not in source_files]
    files_modified = []

    for rel in source_files:
        if rel in target_files:
            try:
                if source_files[rel].read_bytes() != target_files[rel].read_bytes():
                    files_modified.append(rel)
            except Exception:
                files_modified.append(rel)

    return files_added, files_modified, files_deleted


def parse_args(args=None):
    """
    Parse command-line options for the documentation synchronization pipeline.
    
    Parameters:
        args (list[str] | None): Argument values to parse; uses command-line arguments when omitted.
    
    Returns:
        argparse.Namespace: Parsed synchronization configuration.
    """
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
        default=int(os.environ.get("MIN_MDX_FILES") or os.environ.get("MIN_FILES") or "5"),
        help="Minimum required file count in source directory (default: 5 or MIN_MDX_FILES env)",
    )
    parser.add_argument(
        "--max-deletions",
        type=int,
        default=int(os.environ.get("MAX_DELETIONS") or "10"),
        help="Maximum allowed deletion count before requiring explicit override (default: 10 or MAX_DELETIONS env)",
    )
    parser.add_argument(
        "--allow-large-deletions",
        action="store_true",
        default=os.environ.get("ALLOW_LARGE_DELETIONS", "").lower() in ("true", "1", "yes"),
        help="Override deletion cap when deleting more than max-deletions files",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=os.environ.get("DRY_RUN", "").lower() in ("true", "1", "yes"),
        help="Validate source and preview changes without modifying downstream repository",
    )
    return parser.parse_args(args)


def main(cli_args=None):
    """
    Synchronize validated source documentation with the configured target repository.
    
    Parameters:
        cli_args: Optional command-line arguments used to configure the synchronization.
    
    Raises:
        ValueError: If the repository token is missing or the deletion limit is exceeded.
    """
    parsed_args = parse_args(cli_args)
    source_dir = parsed_args.source_dir
    target_repo = parsed_args.target_repo
    branch = parsed_args.branch
    min_files = parsed_args.min_files
    max_deletions = parsed_args.max_deletions
    allow_large_deletions = parsed_args.allow_large_deletions
    dry_run = parsed_args.dry_run

    # Guard A, B, C Validation Checks
    source_files = validate_source_docs(source_dir, min_files=min_files)

    if dry_run:
        print("=== DRY RUN MODE ===")
        print(f"Source Directory: {source_dir} ({len(source_files)} files verified)")
        print(f"Target Repository: {target_repo} (branch: {branch})")
        print(f"Minimum File Floor Threshold: {min_files}")
        print(f"Max Allowed Deletions Threshold: {max_deletions} (Allow Large Deletions: {allow_large_deletions})")
        print("Safety guards A, B, C passed successfully! No downstream modifications performed.")
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

        # Guard D: Diff Preview & Deletion Cap Check
        added, modified, deleted = compute_file_diff(tmp, source_dir)
        print(f"Diff Summary: {len(added)} added, {len(modified)} modified, {len(deleted)} deleted.")
        if added:
            print(f"Files to add ({len(added)}):", [str(a) for a in added[:5]])
        if modified:
            print(f"Files to modify ({len(modified)}):", [str(m) for m in modified[:5]])
        if deleted:
            print(f"Files to delete ({len(deleted)}):", [str(d) for d in deleted[:5]])

        if len(deleted) > max_deletions and not allow_large_deletions:
            raise ValueError(
                f"Deletion cap exceeded: {len(deleted)} file(s) would be deleted, "
                f"which exceeds the maximum allowed threshold of {max_deletions}. "
                "Set ALLOW_LARGE_DELETIONS=true to override."
            )

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
