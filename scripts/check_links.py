#!/usr/bin/env python3
"""Recursive relative link check validation on local files.

This module scans both Markdown (`.md`) and HTML (`.html`) files inside the
`docs/` folder to recursively parse, extract, and verify that all internal
references (excluding external schemas like http/https or mailto addresses)
correctly resolve to valid files or paths on the filesystem. It guarantees
0 broken navigation linkages across compiled project books.

Typical usage example:
    $ python3 scripts/check_links.py
"""

import os
import re
import sys

# Directory containing target files for link validation checks
docs_dir = "docs"

# Regex pattern targeting href attributes in HTML layout
html_href_pattern = re.compile(r'href=["\']([^"\']+)["\']')

# Regex pattern targeting reference parenthesis in Markdown files
markdown_link_pattern = re.compile(r'\[[^\]]+\]\(([^)]+)\)')


def is_external_or_special(link):
    """Determines if a parsed link is external, mailto, or special.

    Args:
        link (str): The raw link text extracted from target file.

    Returns:
        bool: True if external, mailto, anchor-only, or system link; False otherwise.
    """
    link_lower = link.strip().lower()
    if not link_lower:
        return True
    if (link_lower.startswith("http://") or
        link_lower.startswith("https://") or
        link_lower.startswith("mailto:") or
        link_lower.startswith("tel:") or
        link_lower.startswith("file:") or
        link_lower.startswith("#") or
        link_lower.startswith("javascript:")):
        return True
    return False


def check_all_links():
    """Scans the docs/ folder and verifies all local references resolve successfully.

    Recursively walks through target folders, parses all anchor lines, computes relative
    resolutions, and flags any non-existent reference targets.

    Returns:
        bool: True if zero broken relative links are detected; False otherwise.

    Raises:
        OSError: If opening files for scanning encounters filesystem issues.
    """
    broken_links = []
    total_checked = 0

    if not os.path.isdir(docs_dir):
        print(f"Error: {docs_dir} directory not found.")
        sys.exit(1)

    for root, dirs, files in os.walk(docs_dir):
        for file in files:
            if file.endswith((".html", ".md")):
                filepath = os.path.join(root, file)
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                # Choose correct regex based on file extension
                if file.endswith(".html"):
                    links = html_href_pattern.findall(content)
                else:
                    links = markdown_link_pattern.findall(content)

                for link in links:
                    if is_external_or_special(link):
                        continue

                    # Strip any anchor part
                    base_link = link.split("#")[0]
                    if not base_link:
                        # It was a link containing only an anchor or query string, which we skip
                        continue

                    total_checked += 1
                    # Resolve path relative to the file containing the link
                    file_dir = os.path.dirname(filepath)
                    target_path = os.path.normpath(os.path.join(file_dir, base_link))

                    if not os.path.exists(target_path):
                        broken_links.append({
                            "source_file": filepath,
                            "link_value": link,
                            "resolved_path": target_path
                        })

    print(f"--- Link Checker Report ---")
    print(f"Total internal links checked: {total_checked}")
    if broken_links:
        print(f"❌ Found {len(broken_links)} broken link(s):")
        for b in broken_links:
            print(f"  - In file '{b['source_file']}': Link '{b['link_value']}' -> Resolved to '{b['resolved_path']}' which does not exist.")
        return False
    else:
        print("✅ No broken links found!")
        return True


if __name__ == "__main__":
    success = check_all_links()
    if not success:
        sys.exit(1)
    sys.exit(0)
