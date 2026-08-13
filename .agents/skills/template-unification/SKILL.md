---
okf_version: 0.1
type: agent_skill
title: "Template Unification & Layout Compilation Skill"
name: template-unification
description: "Instructs AI agents on executing 'scripts/unify_templates.py' to rebuild custom HTML documentation pages into a standardized, modern 12-column layout with light/dark/auto themes."
resource: "file:///.agents/skills/template-unification/SKILL.md"
timestamp: 2026-08-25T12:00:00Z
topics: [skills, template-unification, html, css, layout, docs]
---

# 🎨 Template Unification & Layout Compilation Skill

This skill teaches Google Antigravity and other AI agents how to manage, compile, and unify the documentation site’s layout across all custom HTML pages under the `docs/` directory.

---

## 🎯 When to use this skill
- Use this skill when adding new documentation pages to the site.
- Use this skill when modifying the common layout, global footer, left-sidebar navigation, or dark/light theme triggers.

---

## 🛠️ The Unification Script (`scripts/unify_templates.py`)

Rather than maintaining duplicated navigation headers and footer blocks across 23+ pages, we use a custom python automation compiler to inject unified elements:

### ⚠️ The Center Content Marker Rule
The template unification script relies on exact, unique occurrences of the following HTML comment to isolate and extract body content:
```html
<!-- Column 2: Center Main Content Area (span 6) -->
```
- **CRITICAL**: If this comment is missing or duplicated within any target HTML file, the python parser will crash or truncate layout compilation.

---

## 🗺️ Page-Specific Heading & TOC Generation

During compilation, the unification script:
1. Dynamically scans center-panel content for headings (`<h2>` and `<h3>` tags).
2. Sanitizes text strings into deduplicated, unique ID attributes.
3. Automatically injects those ID attributes as anchors.
4. Generates a hierarchical, sticky Table of Contents (TOC) inside the right-hand column (Column 3) for the page.

---

## 📝 Sync Requirements

- **Dual Updating**: Since our compiler does not compile Markdown (`.md`) to HTML (`.html`) on the fly, developers must manually update both source files in lockstep before executing the template compiler.
- **Verification**: Run `python scripts/unify_templates.py` and verify all internal links resolve perfectly using `python scripts/check_links.py`.

---
*Deep State of Mind (DSOM) For My AI Protocol | Harisfazillah Jamel (LinuxMalaysia) | 2026-08-25*
*Standard: UK English | DBP-standard Bahasa Melayu Malaysia (Piawai) | GNU General Public License v3.0*
