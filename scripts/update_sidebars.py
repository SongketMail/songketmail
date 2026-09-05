#!/usr/bin/env python3
"""Update sidebar links in compiled HTML documentation files.

This module automates the insertion of the ASIMP Hardening Report link in the left-hand
navigation sidebar of all compiled HTML files inside the `docs/` folder. It locates
the link for the Google Jules operational planning document and appends the ASIMP
Hardening Report link directly below it.

Typical usage example:
    $ python3 scripts/update_sidebars.py
"""

import os
import re

# The directory containing compiled HTML documentation pages
html_dir = "docs"

# HTML anchor element for the ASIMP Hardening Report
regular_asimp_link = """                    <a href="asimp-hardening-report.html" class="flex items-center space-x-2 px-3 py-2 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700/50 text-sm transition font-medium">
                        <span>🛡️</span>
                        <span>13. ASIMP Hardening Report</span>
                    </a>"""

# Regular expression pattern targeting the Jules planning link
pattern = re.compile(
    r'(<a\s+href="jules-planning\.html"\s+class="[^"]+">[\s\S]*?<\/a>)'
)


def update_html_sidebars():
    """
    Add the ASIMP Hardening Report link to eligible HTML documentation sidebars.
    
    Processes HTML files in `docs/`, excluding the report itself, and inserts the
    link after the Jules planning link when it is not already present.
    """
    for filename in os.listdir(html_dir):
        if filename.endswith(".html") and filename != "asimp-hardening-report.html":
            filepath = os.path.join(html_dir, filename)
            with open(filepath, encoding="utf-8") as f:
                content = f.read()

            # Check if ASIMP link is already added to prevent duplicate insertion
            if 'asimp-hardening-report.html' in content:
                continue

            def replacer(match):
                """Callback function to append the ASIMP report link after the matched Jules link.

                Args:
                    match (re.Match): The regex match object containing the Jules planning anchor.

                Returns:
                    str: The original Jules planning anchor appended with the ASIMP report anchor.
                """
                matched_link = match.group(1)
                return matched_link + "\n" + regular_asimp_link

            new_content = pattern.sub(replacer, content)

            if new_content != content:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"Updated sidebar in {filename}")


if __name__ == "__main__":
    update_html_sidebars()
