#!/usr/bin/env python3
"""
update_sidebars.py - Update all generated HTML files under docs/ to include the ASIMP Hardening Report link in sidebars.
Iterates through docs/ and inserts the link below the Google Jules operational planning document link.
"""

import os
import re

html_dir = "docs"

regular_asimp_link = """                    <a href="asimp-hardening-report.html" class="flex items-center space-x-2 px-3 py-2 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700/50 text-sm transition font-medium">
                        <span>🛡️</span>
                        <span>13. ASIMP Hardening Report</span>
                    </a>"""

pattern = re.compile(
    r'(<a\s+href="jules-planning\.html"\s+class="[^"]+">[\s\S]*?<\/a>)'
)


def update_html_sidebars():
    """
    Scans the HTML documentation directory and adds the ASIMP report link in the sidebar menu
    of each HTML file immediately below the Jules operational planning document link.
    """
    for filename in os.listdir(html_dir):
        if filename.endswith(".html") and filename != "asimp-hardening-report.html":
            filepath = os.path.join(html_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # Check if ASIMP link is already added to prevent duplicate insertion
            if 'asimp-hardening-report.html' in content:
                continue

            def replacer(match):
                """Callback function to append ASIMP report link to match."""
                matched_link = match.group(1)
                return matched_link + "\n" + regular_asimp_link

            new_content = pattern.sub(replacer, content)

            if new_content != content:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"Updated sidebar in {filename}")


if __name__ == "__main__":
    update_html_sidebars()
