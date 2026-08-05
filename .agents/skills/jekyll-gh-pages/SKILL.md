---
okf_version: 0.1
type: agent_skill
title: "Jekyll & GitHub Pages Skill"
name: jekyll-gh-pages
description: "Instructs AI agents on Liquid escaping within Jekyll code blocks, OKF v0.1 adoption, and static site publication configurations."
resource: "file:///.agents/skills/jekyll-gh-pages/SKILL.md"
timestamp: 2026-07-04T12:00:00Z
---

# 📝 Jekyll & GitHub Pages Skill

This skill teaches Google Antigravity and other AI agents the guidelines, requirements, and formatting rules for editing the Jekyll static site documentation and publishing to GitHub Pages.

## 🎯 When to use this skill
- Use this skill when creating, updating, or reviewing Markdown files (`*.md`) in the repository.
- Use this skill to prevent Jekyll build failures or Liquid rendering exceptions during deployment.

## 📖 Open Knowledge Format (OKF) Compliance
Every Markdown file in the repository must adopt the Google-inspired **Open Knowledge Format (OKF) v0.1** by including structured YAML frontmatter at the beginning of the file.

### Required Fields
- `okf_version`: Must be `0.1`
- `type`: Category of the resource (e.g., `documentation`, `planning`, `agent_skill`)
- `title`: Descriptive title of the file
- `description`: Succinct explanation of the file's contents
- `resource`: URI reference to the file (e.g., `file:///docs/README.md`)
- `timestamp`: Creation or last modified date in ISO-8601 format

## 🧩 Jekyll Template Escaping Rules
Because our repository contains Ansible templates and YAML configurations that use Jinja2-style curly brace expressions (e.g., `{{ variable_name }}`), Jekyll's Liquid compiler will throw parsing errors during build.

### Escaping Jinja2 Braces
All code blocks containing Jinja2-style braces must be wrapped in Liquid `{ % raw % }` and `{ % endraw % }` tags.
For example:

```markdown
{ % raw % }
```
```yaml
environment:
  XDG_RUNTIME_DIR: "/run/user/{{ songketmail_uid }}"
```
```markdown
{ % endraw % }
```

*(Note: In raw code blocks, remove the spaces between the curly braces and the percent signs: use `{% raw %}` and `{% endraw %}`)*

## 🌐 GitHub Pages Setup
- The site is compiled using Jekyll and automatically deployed via GitHub Actions (`.github/workflows/deploy-pages.yml`).
- A `_config.yml`, `Gemfile`, and `.nojekyll` are present both at the root and under `docs/` to configure correct build targets.
- Local Jekyll rendering can be verified inside the unprivileged environment:
  ```bash
  bundle config set path "vendor/bundle"
  bundle install
  bundle exec jekyll build
  ```

---
*Deep State of Mind (DSOM) For My AI Protocol | Harisfazillah Jamel (LinuxMalaysia) | 2026-07-04*
*Standard: UK English | DBP-standard Bahasa Melayu Malaysia (Piawai) | GNU General Public License v3.0*
