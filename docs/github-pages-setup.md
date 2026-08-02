---
okf_version: 0.1
type: documentation
title: "Comprehensive Guide: Setting up GitHub Pages for SongketMail"
description: "Step-by-step instructions on activating, configuring, and automating deployments to GitHub Pages."
resource: "file:///docs/github-pages-setup.md"
timestamp: 2026-07-04T09:40:04Z
---
# 🌐 Comprehensive Guide: Setting up GitHub Pages for SongketMail

This guide provides explicit, step-by-step instructions on how to activate, configure, and automate the deployment of the SongketMail documentation site to **GitHub Pages**.

We support two distinct deployment approaches:
1. **Automated Deployment using GitHub Actions (Recommended)** — Automatically builds and deploys the page on every commit to the main branch.
2. **Direct Branch Deployment** — Serve documentation directly from a folder (e.g., `/docs`) on your target branch.

---

## 🛠️ Method 1: Automated GitHub Actions Deployment (Recommended)

This repository includes a predefined, production-ready workflow in `.github/workflows/deploy-pages.yml` that builds and deploys your static pages securely and natively via GitHub Actions.

### Step 1: Enable GitHub Actions Permissions
By default, GitHub Actions workflows might not have permission to deploy pages. You need to enable this:
1. Navigate to your GitHub repository.
2. Click on the **Settings** tab.
3. In the left sidebar, click on **Actions** -> **General**.
4. Scroll down to the **Workflow permissions** section.
5. Select **Read and write permissions**.
6. Click **Save**.

### Step 2: Configure GitHub Pages Source
1. Click on the **Settings** tab of your repository.
2. In the left sidebar under the "Code and automation" section, click on **Pages**.
3. Under **Build and deployment**, locate the **Source** dropdown menu.
4. Select **GitHub Actions** from the dropdown list. *(Note: You do not need to specify a branch here, as the Actions workflow manages the deployment target itself).*

### Step 3: Trigger the Workflow
Once the source is set to GitHub Actions, you can trigger the deploy:
- **Pushing code:** Simply push changes to your `main` or `master` branch.
- **Manual Trigger:**
  1. Navigate to the **Actions** tab of your repository.
  2. Click on **Deploy GitHub Pages** from the left sidebar.
  3. Click the **Run workflow** dropdown and click the green **Run workflow** button.

---

## 📦 Method 2: Direct Branch Deployment (`/docs` Folder)

If you prefer not to use GitHub Actions workflows and want GitHub to serve files directly from a static folder on your branch:

### Step 1: Push the `docs/` Folder
Ensure that the `docs/` folder containing `index.html` is committed and pushed to your GitHub repository on the main branch.

### Step 2: Configure Settings
1. Navigate to your GitHub repository.
2. Click on the **Settings** tab.
3. In the left sidebar, click on **Pages**.
4. Under **Build and deployment**, locate the **Source** dropdown menu and select **Deploy from a branch**.
5. Under **Branch**:
   - Select your target branch (e.g., `main` or `master`) in the first dropdown.
   - Select the **`/docs`** folder in the second directory folder dropdown.
6. Click **Save**.

---

## 🔍 How to Access Your Deployed Site

Once the build and deployment run successfully (which usually takes 1–2 minutes):
1. Navigate back to **Settings** -> **Pages**.
2. At the top of the Pages settings, you will see a banner displaying your live URL, formatted as:
   ```
   https://<your-username>.github.io/<your-repository-name>/
   ```
3. Click on the link to open your live interactive SongketMail Documentation dashboard!

---

## 🚀 Troubleshooting Tips

### ❌ Site returns a `404 Not Found`
- Ensure that you have an `index.html` file inside the root of your source directory (e.g., directly under `/docs`).
- Ensure the capitalization matches perfectly (GitHub Pages servers are case-sensitive).
- Wait up to 5 minutes, as CDN caches on GitHub Pages can occasionally take a moment to propagate.

### ❌ Action fails with `Permission Denied`
- Ensure you updated the **Workflow permissions** to **Read and write permissions** as described in Method 1, Step 1.

---
*Deep State of Mind (DSOM) For My AI Protocol | Harisfazillah Jamel (LinuxMalaysia) | 2026-07-04*
*Standard: UK English | DBP-standard Bahasa Melayu Malaysia (Piawai) | GNU General Public License v3.0*
