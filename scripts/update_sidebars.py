#!/usr/bin/env python3
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

for filename in os.listdir(html_dir):
    if filename.endswith(".html") and filename != "asimp-hardening-report.html":
        filepath = os.path.join(html_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Check if ASIMP link is already added to prevent duplicate insertion
        if 'asimp-hardening-report.html' in content:
            continue

        def replacer(match):
            matched_link = match.group(1)
            return matched_link + "\n" + regular_asimp_link

        new_content = pattern.sub(replacer, content)

        if new_content != content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"Updated sidebar in {filename}")
