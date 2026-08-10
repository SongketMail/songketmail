#!/usr/bin/env python3
import os
import re

SIDEBAR_ITEMS = [
    { "href": "index.html", "icon": "🏠", "label": "Home", "section": "home" },
    { "header": "Deep Research Series", "section": "research" },
    { "href": "podman-rootless.html", "icon": "🐳", "label": "1. Podman Rootless", "section": "research" },
    { "href": "ansible-fqcn.html", "icon": "🤖", "label": "2. Ansible Best Practices", "section": "research" },
    { "href": "postfix-dovecot.html", "icon": "✉️", "label": "3. Postfix & Dovecot", "section": "research" },
    { "href": "s3-storage.html", "icon": "🪣", "label": "4. S3 Object Storage", "section": "research" },
    { "href": "webmail-clients.html", "icon": "📧", "label": "5. Webmail Integration", "section": "research" },
    { "href": "bunkerweb-proxy.html", "icon": "🌐", "label": "6. BunkerWeb Proxy", "section": "research" },
    { "href": "architectural-blueprint.html", "icon": "🏗️", "label": "7. SKM Blueprint", "section": "research" },
    { "href": "creating-a-github-pages-site-with-jekyll.html", "icon": "🌐", "label": "9a. Jekyll Site Creation", "section": "research" },
    { "href": "github-pages-setup.html", "icon": "⚙️", "label": "9b. GH Pages Automation", "section": "research" },
    { "href": "references.html", "icon": "📚", "label": "10. References & Resources", "section": "research" },
    { "href": "dockpod-integration.html", "icon": "📊", "label": "11. DockPod Integration", "section": "research" },
    { "href": "jules-planning.html", "icon": "📋", "label": "12. Jules Planning Document", "section": "research" },
    { "href": "asimp-hardening-report.html", "icon": "🛡️", "label": "13. ASIMP Hardening Report", "section": "research" },
    { "href": "SOP-KNOWLEDGE-FIRST-DISCOVERY.html", "icon": "🔍", "label": "14. Discovery Protocol", "section": "research" },
    { "href": "wsl-development-feedback.html", "icon": "💻", "label": "15. WSL Feedback Loop", "section": "research" },
    { "href": "ANSIBLE-ADOPTION-REVIEW.html", "icon": "⚙️", "label": "16. Ansible Adoption Review", "section": "research" },
    { "href": "mail-web-app-verification.html", "icon": "📧", "label": "17. Mail Web Ingress Verification", "section": "research" },
    { "href": "ansible-playbook-map.html", "icon": "🤖", "label": "18. Ansible Playbook Map", "section": "research" },
    { "header": "Laboratory Modules", "section": "lab" },
    { "href": "ai-dev.html", "icon": "🤖", "label": "AI Development", "section": "lab" }
]

TOPIC_MAP = {
    "index.html": ("[ REL: 5.0.0 ]", "[ STD: RFC_9116 ]", "[ ENV: PODMAN_5 ]", "[ VIEW: STANDARD ]"),
    "podman-rootless.html": ("[ TOPIC: 1 ]", "[ ORCH: QUADLET ]", "[ USER: ROOTLESS ]"),
    "ansible-fqcn.html": ("[ TOPIC: 2 ]", "[ STD: ANSIBLE_FQCN ]", "[ MODE: IDEMPOTENT ]"),
    "postfix-dovecot.html": ("[ TOPIC: 3 ]", "[ PROTO: SMTP_IMAP ]", "[ SECURE: TLS_MANDATORY ]"),
    "s3-storage.html": ("[ TOPIC: 4 ]", "[ OBJSTORE: S3_COMPAT ]", "[ POLICY: BACKUP_321 ]"),
    "webmail-clients.html": ("[ TOPIC: 5 ]", "[ CLIENTS: ROUNDCUBE_SNAPPY ]", "[ ENG: NGINX_PHP ]"),
    "bunkerweb-proxy.html": ("[ TOPIC: 6 ]", "[ PROXY: BUNKERWEB ]", "[ INGRESS: TLS_ACME ]"),
    "architectural-blueprint.html": ("[ TOPIC: 7 ]", "[ ARCH: PERSISTENCE_TRINITY ]", "[ SEC: ISOLATION_ZONE ]"),
    "creating-a-github-pages-site-with-jekyll.html": ("[ TOPIC: 9A ]", "[ FRAMEWORK: JEKYLL ]", "[ SITE: STATIC ]"),
    "github-pages-setup.html": ("[ TOPIC: 9B ]", "[ CI_CD: GH_ACTIONS ]", "[ DEPLOY: AUTOMATED ]"),
    "references.html": ("[ TOPIC: 10 ]", "[ DOCS: REFERENCE ]", "[ TYPE: INDEX ]"),
    "dockpod-integration.html": ("[ TOPIC: 11 ]", "[ DOCKPOD: PORTAINER ]", "[ ENG: API_MESH ]"),
    "jules-planning.html": ("[ TOPIC: 12 ]", "[ JULES: OPERATIONS ]", "[ STATE: VIRTUALIZED ]"),
    "asimp-hardening-report.html": ("[ TOPIC: 13 ]", "[ AUDIT: ASIMP_LYNIS ]", "[ SEC: HARDENED_85 ]"),
    "SOP-KNOWLEDGE-FIRST-DISCOVERY.html": ("[ TOPIC: 14 ]", "[ PROTOCOL: SOP_KNOWLEDGE ]", "[ ENG: OKF_METADATA ]"),
    "wsl-development-feedback.html": ("[ TOPIC: 15 ]", "[ DEV: WSL_UBUNTU_26 ]", "[ FEEDBACK: AUTOMATED ]"),
    "ANSIBLE-ADOPTION-REVIEW.html": ("[ TOPIC: 16 ]", "[ CONCEPTS: PIPELINING_CALLBACK ]", "[ AUDIT: COMPLIANCE ]"),
    "mail-web-app-verification.html": ("[ TOPIC: 17 ]", "[ AUDIT: MAIL_INGRESS ]", "[ PORTS: 25_80_443_587_993 ]"),
    "ansible-playbook-map.html": ("[ TOPIC: 18 ]", "[ MAP: PLAYBOOK_TO_DOC ]", "[ ENGINE: ANSIBLE_DRIVEN ]"),
    "ai-dev.html": ("[ LAB: AI_DEV ]", "[ MODEL: COGNITIVE_TWIN ]", "[ ENGINE: JULES_GEMINI ]")
}

SUBTITLE_MAP = {
    "index.html": "SECURE EMAIL SERVER FABRIC // PODMAN 5+ & SYSTEMD QUADLET",
    "podman-rootless.html": "Deep Research // Topic 1: Rootless Podman 5+ & Quadlet Orchestration",
    "ansible-fqcn.html": "Deep Research // Topic 2: Ansible Best Practices & FQCN",
    "postfix-dovecot.html": "Deep Research // Topic 3: Postfix & Dovecot SMTP/IMAP Fabric",
    "s3-storage.html": "Deep Research // Topic 4: S3 Object Storage & Backups",
    "webmail-clients.html": "Deep Research // Topic 5: Webmail Clients (Roundcube & SnappyMail)",
    "bunkerweb-proxy.html": "Deep Research // Topic 6: BunkerWeb Proxy & Protocol Handling",
    "architectural-blueprint.html": "Deep Research // Topic 7: Architectural Blueprint & Storage Layout",
    "creating-a-github-pages-site-with-jekyll.html": "Deep Research // Topic 9a: Jekyll GitHub Pages Site Creation",
    "github-pages-setup.html": "Deep Research // Topic 9b: GitHub Pages Deployment Automation",
    "references.html": "Deep Research // Topic 10: References, Guides & Resource Directory",
    "dockpod-integration.html": "Deep Research // Topic 11: DockPod Portainer Integration & API Mesh",
    "jules-planning.html": "Deep Research // Topic 12: Google Jules Agent Planning & Virtualization Limits",
    "asimp-hardening-report.html": "Deep Research // Topic 13: ASIMP Security Auditing & Hardening Report",
    "SOP-KNOWLEDGE-FIRST-DISCOVERY.html": "Deep Research // Topic 14: Local Knowledge-First & Metadata Discovery",
    "wsl-development-feedback.html": "Deep Research // Topic 15: WSL Ubuntu 26.04 Development & Jules Feedback",
    "ANSIBLE-ADOPTION-REVIEW.html": "Deep Research // Topic 16: Ansible Configuration Review and Adoption Assessment",
    "mail-web-app-verification.html": "Deep Research // Topic 17: Mail Web Application Ingress Verification",
    "ansible-playbook-map.html": "Deep Research // Topic 18: Ansible Playbook and Related Documents Map",
    "ai-dev.html": "Deep Research // Laboratory Module: AI Development Loop"
}

def parse_frontmatter(md_path):
    if not os.path.exists(md_path):
        return {}
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()
    parts = content.split('---')
    if len(parts) < 3:
        return {}
    fm_text = parts[1]
    metadata = {}
    for line in fm_text.strip().split('\n'):
        if ':' in line:
            key, val = line.split(':', 1)
            key = key.strip()
            val = val.strip()
            if val.startswith('[') and val.endswith(']'):
                val = [v.strip().strip('"').strip("'") for v in val[1:-1].split(',')]
            else:
                val = val.strip('"').strip("'")
            metadata[key] = val
    return metadata

def strip_html_tags(text):
    return re.sub(r'<[^>]+>', '', text)

def generate_slug(text):
    text = strip_html_tags(text).lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')

def inject_ids_and_collect_toc(content):
    headings = []
    slugs_seen = set()

    # Pattern to match h2 and h3 tags
    pattern = re.compile(r'<(h2|h3)\b([^>]*)>(.*?)</\1>', re.IGNORECASE | re.DOTALL)

    def repl(match):
        tag = match.group(1).lower()
        attrs = match.group(2)
        inner_content = match.group(3)

        plain_text = strip_html_tags(inner_content)
        plain_text = re.sub(r'\s+', ' ', plain_text).strip()
        if not plain_text:
            return match.group(0)

        slug = generate_slug(plain_text)
        if not slug:
            slug = f"section-{len(slugs_seen)}"

        base_slug = slug
        counter = 1
        while slug in slugs_seen:
            slug = f"{base_slug}-{counter}"
            counter += 1
        slugs_seen.add(slug)

        headings.append({
            "tag": tag,
            "text": plain_text,
            "slug": slug
        })

        if 'id=' in attrs:
            new_attrs = re.sub(r'id=["\'][^"\']*["\']', f'id="{slug}"', attrs)
        else:
            new_attrs = f' id="{slug}"' + attrs

        return f'<{tag}{new_attrs}>{inner_content}</{tag}>'

    new_content = pattern.sub(repl, content)
    return new_content, headings

def make_toc_card(headings):
    if not headings:
        return ""

    toc_items = []
    for h in headings:
        tag = h["tag"]
        text = h["text"]
        slug = h["slug"]

        if tag == "h2":
            toc_items.append(f"""                    <li class="pl-0">
                        <a href="#{slug}" class="text-slate-650 dark:text-slate-350 hover:text-violet-600 dark:hover:text-violet-400 transition font-semibold block">
                            {text}
                        </a>
                    </li>""")
        elif tag == "h3":
            toc_items.append(f"""                    <li class="pl-4 border-l border-slate-200 dark:border-slate-700">
                        <a href="#{slug}" class="text-slate-550 dark:text-slate-450 hover:text-violet-600 dark:hover:text-violet-400 transition text-xs block font-medium">
                            {text}
                        </a>
                    </li>""")

    toc_list_html = "\n".join(toc_items)

    return f"""
            <!-- Table of Contents Card -->
            <div class="bg-white dark:bg-slate-800 rounded-2xl p-5 border border-slate-200 dark:border-slate-700 shadow-sm space-y-3 sticky top-6">
                <h4 class="text-xs font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 mb-2">Table of contents</h4>
                <ul class="space-y-2 text-sm">
{toc_list_html}
                </ul>
            </div>
"""

def get_html_title(filename, fm):
    if filename == "index.html":
        return "SongketMail :: LAB — Secure Email Server Fabric"
    base_title = fm.get("title", "").strip().strip('"').strip("'")
    if not base_title:
        base_title = filename.replace(".html", "").replace("-", " ").title()
    return f"{base_title} — SongketMail :: LAB"

def make_sidebar(active_filename):
    sidebar_html = []
    for item in SIDEBAR_ITEMS:
        if "header" in item:
            sidebar_html.append(f"""
                    <!-- {item["header"]} Section -->
                    <div class="pt-4 pb-1 text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider px-3 border-t border-slate-200 dark:border-slate-700 mt-4 mb-2">
                        {item["header"]}
                    </div>""")
        else:
            is_active = (item["href"] == active_filename)
            if is_active:
                sidebar_html.append(f"""                    <a href="{item["href"]}" class="flex items-center space-x-2 px-3 py-2 rounded-lg bg-violet-50 dark:bg-violet-950/50 text-violet-600 dark:text-violet-400 font-bold text-sm transition">
                        <span>{item["icon"]}</span>
                        <span>{item["label"]}</span>
                    </a>""")
            else:
                sidebar_html.append(f"""                    <a href="{item["href"]}" class="flex items-center space-x-2 px-3 py-2 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700/50 text-sm transition font-medium">
                        <span>{item["icon"]}</span>
                        <span>{item["label"]}</span>
                    </a>""")
    return "\n".join(sidebar_html)

def build_unified_html(filename, fm, center_content, right_sidebar_inner):
    head_title = get_html_title(filename, fm)
    brand_subtitle = SUBTITLE_MAP.get(filename, "SECURE EMAIL SERVER FABRIC // PODMAN 5+ & SYSTEMD QUADLET")
    sidebar_nav_html = make_sidebar(filename)

    meta_pills = TOPIC_MAP.get(filename, ("[ REL: 5.0.0 ]", "[ STD: RFC_9116 ]", "[ ENV: PODMAN_5 ]", "[ VIEW: STANDARD ]"))
    meta_pills_html = "\n            <span>|</span>\n            ".join([f"<span>{pill}</span>" for pill in meta_pills])

    return f"""<!DOCTYPE html>
<html lang="en" x-data="{{
    theme: localStorage.getItem('theme') || 'auto',
    setTheme(val) {{
        this.theme = val;
        localStorage.setItem('theme', val);
    }},
    isDark() {{
        if (this.theme === 'dark') return true;
        if (this.theme === 'light') return false;
        return window.matchMedia('(prefers-color-scheme: dark)').matches;
    }}
}}" :class="{{ 'dark': isDark() }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{head_title}</title>
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Alpine.js -->
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
    <script>
        tailwind.config = {{
            darkMode: 'class',
            theme: {{
                extend: {{
                    colors: {{
                        brand: {{
                            purple: '#7c3aed',
                            green: '#10b981',
                            orange: '#f59e0b',
                            blue: '#2563eb',
                            red: '#dc2626',
                        }}
                    }}
                }}
            }}
        }}
    </script>
    <style>
        [x-cloak] {{ display: none !important; }}
        html {{
            scroll-behavior: smooth;
        }}
    </style>
</head>
<body class="bg-[#f8fafc] text-slate-800 dark:bg-slate-900 dark:text-slate-100 font-sans antialiased min-h-screen transition-colors duration-200">

    <!-- Top Bar / Header -->
    <header class="max-w-7xl mx-auto px-4 pt-6 pb-2">
        <div class="flex flex-col md:flex-row justify-between items-start md:items-center border-b border-slate-200 dark:border-slate-800 pb-4">
            <!-- Brand Logo Area -->
            <div>
                <div class="flex items-center space-x-2">
                    <span class="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">SongketMail</span>
                    <span class="text-2xl font-bold text-violet-600">::</span>
                    <span class="text-2xl font-bold text-slate-900 dark:text-white">LAB</span>
                </div>
                <div class="text-xs tracking-wider text-slate-500 dark:text-slate-400 mt-1 uppercase font-semibold">
                    {brand_subtitle}
                </div>
            </div>

            <!-- Mode Selector -->
            <div class="flex items-center space-x-3 mt-4 md:mt-0 bg-white dark:bg-slate-800 p-1.5 rounded-full shadow-sm border border-slate-200 dark:border-slate-700">
                <span class="text-xs font-bold text-slate-400 dark:text-slate-500 px-2 uppercase">Mode:</span>

                <!-- Light Mode Button -->
                <button @click="setTheme('light')"
                        :class="theme === 'light' ? 'bg-amber-100 text-amber-800 border-amber-200 shadow-sm' : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'"
                        class="px-3 py-1 rounded-full text-xs font-semibold flex items-center space-x-1.5 border border-transparent transition">
                    <span>☀️</span>
                    <span>LIGHT</span>
                </button>

                <!-- Dark Mode Button -->
                <button @click="setTheme('dark')"
                        :class="theme === 'dark' ? 'bg-slate-700 text-white border-slate-600 shadow-sm' : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'"
                        class="px-3 py-1 rounded-full text-xs font-semibold flex items-center space-x-1.5 border border-transparent transition">
                    <span>🌙</span>
                    <span>DARK</span>
                </button>

                <!-- Auto Mode Button -->
                <button @click="setTheme('auto')"
                        :class="theme === 'auto' ? 'bg-blue-100 text-blue-800 border-blue-200 shadow-sm' : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'"
                        class="px-3 py-1 rounded-full text-xs font-semibold flex items-center space-x-1.5 border border-transparent transition">
                    <span>💻</span>
                    <span>AUTO</span>
                </button>
            </div>
        </div>
    </header>

    <!-- Main Workspace -->
    <main class="max-w-7xl mx-auto px-4 py-6 grid grid-cols-1 lg:grid-cols-12 gap-8">

        <!-- Column 1: Left Navigation Sidebar (span 3) -->
        <aside class="lg:col-span-3">
            <div class="bg-white dark:bg-slate-800 rounded-2xl p-5 border border-slate-200 dark:border-slate-700 shadow-sm sticky top-6">
                <nav class="space-y-1">
{sidebar_nav_html}
                </nav>
            </div>
        </aside>

        <!-- Column 2: Center Main Content Area (span 6) -->
        <section class="lg:col-span-6 space-y-8">
{center_content}
        </section>

        <!-- Column 3: Right Sidebar (span 3) -->
        <aside class="lg:col-span-3 space-y-6">
{right_sidebar_inner}
        </aside>

    </main>

    <!-- Global Footer -->
    <footer class="max-w-7xl mx-auto px-4 py-8 mt-12 border-t border-slate-200 dark:border-slate-800 text-center space-y-4">
        <div class="text-xs text-slate-400 dark:text-slate-500 flex flex-wrap justify-center gap-3">
            <span>SongketMail Infrastructure: <a href="https://www.linuxmalaysia.com/" class="hover:text-violet-500 underline">linuxmalaysia.com</a></span>
            <span>•</span>
            <span>Copyright © 2005 - 2026 Harisfazillah Jamel</span>
        </div>
        <div class="text-[10px] tracking-wide text-slate-400 dark:text-slate-600 uppercase font-semibold flex flex-wrap justify-center gap-2">
{meta_pills_html}
        </div>
    </footer>

</body>
</html>"""

def clean_content(content):
    content = re.sub(r'CMSForNerd(\s*::\s*LAB)?', 'SongketMail :: LAB', content, flags=re.IGNORECASE)
    content = re.sub(r'CMSForNerd2', 'SongketMail', content, flags=re.IGNORECASE)
    content = re.sub(r'CmsForNerd Infrastructure', 'SongketMail Infrastructure', content, flags=re.IGNORECASE)
    return content

def main():
    docs_dir = "docs"
    html_files = [f for f in os.listdir(docs_dir) if f.endswith(".html")]

    for filename in sorted(html_files):
        html_path = os.path.join(docs_dir, filename)
        md_path = os.path.join(docs_dir, filename.replace(".html", ".md"))

        print(f"Processing {filename}...")

        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        fm = parse_frontmatter(md_path)

        center_content = ""

        col2_marker = "<!-- Column 2: Center Main Content Area (span 6) -->"
        col3_marker = "<!-- Column 3: Right Sidebar (span 3) -->"

        if col2_marker in html_content and col3_marker in html_content:
            parts = html_content.split(col2_marker)
            content_part = parts[1].split(col3_marker)[0].strip()

            sec_start = content_part.find(">")
            sec_end = content_part.rfind("</section>")
            if sec_start != -1 and sec_end != -1:
                center_content = content_part[sec_start+1:sec_end].strip()
            else:
                center_content = content_part

        elif "<article" in html_content:
            parts = html_content.split("<article")
            article_part = parts[1].split("</article>")[0]
            start_idx = article_part.find(">")
            center_content = article_part[start_idx+1:].strip()

            if "<footer" in center_content:
                center_content = center_content.split("<footer")[0].strip()

        elif "<main" in html_content:
            parts = html_content.split("<main")
            main_part = parts[1].split("</main>")[0]
            start_idx = main_part.find(">")
            center_content = main_part[start_idx+1:].strip()

            if "<footer" in center_content:
                center_content = center_content.split("<footer")[0].strip()
        else:
            print(f"WARNING: Unknown structure in {filename}, skipping content extraction")
            continue

        # Clean up any residual CMSForNerd branding from the center content
        center_content = clean_content(center_content)

        # Inject unique IDs into heading tags and extract TOC list
        center_content, headings = inject_ids_and_collect_toc(center_content)

        # Build dynamic Table of Contents Card
        right_sidebar_inner = make_toc_card(headings)

        # Build unified HTML content
        new_html = build_unified_html(filename, fm, center_content, right_sidebar_inner)

        # Write back to HTML file
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(new_html)

    print("Done! All templates unified successfully!")

if __name__ == "__main__":
    main()