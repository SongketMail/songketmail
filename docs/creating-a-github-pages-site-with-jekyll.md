---
okf_version: 0.1
type: documentation
title: "Creating a GitHub Pages Site with Jekyll"
description: "A comprehensive guide to creating, building, and configuring a GitHub Pages static site using Jekyll in a new or existing repository."
resource: "file:///docs/creating-a-github-pages-site-with-jekyll.md"
timestamp: 2026-07-04T12:00:00Z
topics: [jekyll, static-site, github-pages, guide]
---
# 🌐 Creating a GitHub Pages Site with Jekyll

This comprehensive guide provides an absolute, step-by-step walkthrough on how to create, build, and configure a **GitHub Pages** static site using the **Jekyll** static site generator in either a completely new or an existing repository.

Jekyll is a blog-aware, static site generator written in Ruby that integrates natively with GitHub Pages, allowing you to publish documentation, portfolios, and websites directly from your markdown source files.

---

## 🛠️ Step 1: Install Prerequisite Tools

Before you can run Jekyll locally, you must ensure that your system has Ruby, Bundler, Git, and Jekyll installed.

1. **Install Git**: Verify that you have Git installed:

   ```bash
   git --version
   ```

2. **Install Ruby**: Jekyll requires Ruby (version 2.5.0 or higher is recommended).
   - On Ubuntu/Debian:

     ```bash
     sudo apt-get install ruby-full build-essential zlib1g-dev
     ```

   - On macOS (using Homebrew):

     ```bash
     brew install ruby
     ```

3. **Install Bundler and Jekyll**: Bundler is a Ruby gem manager that helps keep dependency versions consistent.

   ```bash
   gem install jekyll bundler
   ```

---

## 📂 Step 2: Initialize Your Jekyll Site

You can initialize Jekyll in a completely new repository or inject it into an existing project.

### Case A: Creating a Site in a New Repository
1. Initialize a new local directory and Git repository:

   ```bash
   mkdir my-jekyll-site
   cd my-jekyll-site
   git init
   ```

2. Run the Jekyll creation command inside the root directory:

   ```bash
   jekyll new . --force
   ```

   *(The `--force` option is required if the directory contains initialized Git metadata).*

### Case B: Injecting Jekyll into an Existing Repository (e.g. SongketMail)
If you already have a repository and want to host your site from a specific folder (such as the `/docs` directory):
1. Navigate to your repository root or target directory.
2. Create a basic Jekyll directory structure. You can do this manually by creating:
   - `_config.yml` (Jekyll's configuration file)
   - `Gemfile` (Defining Ruby plugin dependencies)
   - `index.md` or `index.html` (Your home page)
   - `.nojekyll` (An empty file telling GitHub Pages not to ignore files prefixed with underscores)

---

## ⚙️ Step 3: Configure Gemfile & _config.yml

To align your site exactly with the GitHub Pages build server, you should utilize the official `github-pages` gem.

### 1. Update the `Gemfile`
Overwrite or create a `Gemfile` in the directory root with the following contents:

```ruby
source "https://rubygems.org"

gem "github-pages", group: :jekyll_plugins
```

### 2. Configure Jekyll Settings in `_config.yml`
Create or update your `_config.yml` file to configure metadata, themes, and exclusion lists:

```yaml
title: "SongketMail :: LAB"
description: "Secure Email Server Fabric // Podman 5+ & Systemd Quadlet"
theme: jekyll-theme-primer
markdown: kramdown
exclude:
  - Gemfile
  - Gemfile.lock
  - vendor/
  - .github/
  - roles/
  - group_vars/
  - inventory/
  - site.yml
  - ansible.cfg
  - LICENSE
  - README.md
```

---

## 🖥️ Step 4: Local Testing & Building

To run a local web server and preview your site before pushing it to GitHub, use the following commands:

1. **Install Dependencies Locally**:
   Run this once to install the exact gems specified in your `Gemfile`:

   ```bash
   bundle install
   ```

2. **Launch Jekyll Serve**:
   Start the local development server:

   ```bash
   bundle exec jekyll serve
   ```

   - By default, your site will be served locally at `http://localhost:4000/`.
   - The server dynamically watches for changes and rebuilds the site automatically on save.
   - If you want to build the site statically without launching a server:

     ```bash
     bundle exec jekyll build
     ```

---

## ⚠️ Step 5: Escaping Template Conflict Errors

Because Jekyll uses the Liquid templating engine, any code blocks containing Jinja2-style braces (e.g., `{ { ... } }` or `{ % ... % }` as commonly used in Ansible files) can trigger parsing exceptions during deployment on GitHub Pages.

### The Solution: Liquid Template Escaping
You must wrap any Jinja2-style code blocks inside `{ % raw % }` and `{ % endraw % }` tags.

For example, to prevent Jekyll from attempting to parse an Ansible variable:

```markdown
{% raw %}
- name: Set dynamic path
  ansible.builtin.copy:
    dest: "/opt/songketmail/{{ service_name }}/config"
{% endraw %}
```

---

## 📦 Step 6: Select Your Publishing Source

Once your repository has Jekyll configured, push it to GitHub and configure the deployment source.

### Option A: Direct Branch Deployment (`/docs` or `root`)
1. In your GitHub repository, navigate to **Settings** -> **Pages**.
2. Under **Build and deployment**, select **Deploy from a branch** as your source.
3. Choose your default branch (e.g., `main`), select either `/ (root)` or `/docs` as the directory folder, and click **Save**.

### Option B: Custom GitHub Actions (Recommended)
Configure a custom GitHub Actions workflow (such as `.github/workflows/deploy-pages.yml`) to automatically build and push Jekyll site assets securely to the `gh-pages` branch. This approach bypasses local build requirements and ensures high-speed pipeline updates.

---
*Deep State of Mind (DSOM) For My AI Protocol | Harisfazillah Jamel (LinuxMalaysia) | 2026-07-04*
*Standard: UK English | DBP-standard Bahasa Melayu Malaysia (Piawai) | GNU General Public License v3.0*
