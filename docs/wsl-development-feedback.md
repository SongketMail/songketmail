---
okf_version: 0.1
type: documentation
title: "WSL Ubuntu 26.04 Development & Jules CLI Feedback Integration"
description: "Detailed system guidelines and architecture for running development-only testing in Windows WSL with Linux Ubuntu 26.04 and automated feedback loops to Jules and GitHub PRs."
resource: "file:///docs/wsl-development-feedback.md"
timestamp: 2026-08-07T12:00:00Z
topics: [wsl, ubuntu-26-04, testing, feedback-loop, development, jules-cli]
---

# 💻 WSL Ubuntu 26.04 Development & Jules CLI Feedback Integration

This document outlines the architecture, operating instructions, and execution details of the development-only testing harness designed for Windows Subsystem for Linux (WSL) running **Ubuntu 26.04 (Noble/Plucky)**. This environment runs real OS workloads outside of the Google Jules unprivileged container sandbox, enabling deep multi-environment testing and automated integration reporting back to Google Jules and active GitHub Pull Requests.

---

## 🎯 Architectural Intent & Boundary

To preserve stability and ease of deployment for end-users, this feedback and testing framework is **strictly limited to development sessions**.

```
┌─────────────────────────────────────────────────────────┐
│               Local WSL 2 (Ubuntu 26.04)                │
│  - Real OS host kernel                                  │
│  - Systemd user session manager running                  │
│  - Podman 5+ installed                                  │
└────────────────────────────┬────────────────────────────┘
                             │
                             ▼  [scripts/wsl_test_feedback.sh]
┌─────────────────────────────────────────────────────────┐
│              wsl_feedback_playbook.yml                  │
│  - Verifies WSL 2 systemd socket and Quadlet engine     │
│  - Executes decoupled 7-service mail fabric smoke tests │
│  - Queries Jules CLI + API for task instructions        │
│  - Posts runtime logs/debug diagnostics back to Jules  │
└────────────────────────────┬────────────────────────────┘
                             │
                             ├──────────────────────────────┐
                             ▼                              ▼
                 ┌───────────────────────┐      ┌───────────────────────┐
                 │       Jules CLI       │      │     GitHub PR API     │
                 │ (Interactive updates) │      │  (Debug / Test logs)  │
                 └───────────────────────┘      └───────────────────────┘
```

### 🚫 Restricted Mode Gate (Development Only)
These scripts, configurations, and playbooks are **explicitly bypassed** for regular users deploying in production or "use-only mode". This separation is enforced using two layers of safety guards:
1.  **Environment Variable Gate**: The bash runner `scripts/wsl_test_feedback.sh` terminates immediately unless `WSL_DEVELOPMENT_MODE` is explicitly set to `true`.
2.  **Ansible Playbook Gate**: The playbook `wsl_feedback_playbook.yml` performs a strict check against the `wsl_development_mode` variable (which defaults to `false` in normal runs) and gracefully exits if disabled.

---

## 🚀 Environment Setup on WSL (Ubuntu 26.04)

Ubuntu 26.04 provides full standard systemd support within WSL 2. To initialize this environment for SongketMail development:

### 1. Enable Systemd inside WSL
In your WSL instance, ensure `/etc/wsl.conf` has systemd enabled:
```ini
[boot]
systemd=true
```
*(Requires restarting WSL with `wsl.exe --shutdown` from Windows Command Prompt).*

### 2. Install Podman 5+ and Dependencies
Install the native packages on Ubuntu 26.04:
```bash
sudo apt update
sudo apt install -y podman podman-docker jq curl git ansible python3-pip
```

### 3. Configure Rootless SubUID/SubGID Mappings
Create the target development user mapping (e.g., for the user `songketmail` or your developer account with UID 2001):
```bash
sudo groupadd -g 2001 songketmail || true
sudo useradd -u 2001 -g 2001 -m -s /bin/bash songketmail || true
echo "songketmail:100000:65536" | sudo tee -a /etc/subuid
echo "songketmail:100000:65536" | sudo tee -a /etc/subgid
```

---

## 🔄 The Feedback Loop Mechanics

When testing locally inside WSL, the development harness automates communications with **Google Jules CLI** and **GitHub Pull Request APIs**.

### 1. Querying Jules CLI / API
The integration uses standard environmental triggers and commands:
- **Environment Variables**: `JULES_API_URL`, `JULES_TASK_ID`, and `GITHUB_TOKEN` are passed to the WSL workspace.
- **Jules CLI**: The tool invoking `jules task` or `jules comment` is wrapped inside local query loops to pull updated task targets or prompt updates.
- **API Fetching**: If direct CLI binaries are restricted, the script falls back to an HTTP API request:
  ```bash
  curl -s -H "Authorization: Bearer $JULES_API_TOKEN" \
       "$JULES_API_URL/tasks/$JULES_TASK_ID"
  ```

### 2. Reporting Back to GitHub PR & Jules
Detailed reports, test outcomes, error traces, and debugging information are collected dynamically. The dedicated playbook aggregates these diagnostics and posts them:
- **GitHub PR Comment Posting**:
  Using `gh pr comment` or direct REST API:
  ```bash
  curl -s -X POST \
       -H "Authorization: token $GITHUB_TOKEN" \
       -H "Accept: application/vnd.github.v3+json" \
       -d "{\"body\": \"### 🧪 WSL Ubuntu 26.04 Test Report\n\n**Status:** PASS\n**Logs:**\n\`\`\`\n$TEST_LOGS\n\`\`\`\"}" \
       "https://api.github.com/repos/$GITHUB_REPOSITORY/issues/$PR_NUMBER/comments"
  ```
- **Jules CLI Feedback**:
  ```bash
  jules feedback --task-id "$JULES_TASK_ID" --status "completed" --log-file "./data/wsl_run.log"
  ```

---

## 🛠️ The Core Development Suite

The suite consists of two newly-introduced assets in the workspace:

### 1. The Bash Script (`scripts/wsl_test_feedback.sh`)
Serves as the outer execution wrapper. It is responsible for:
- Confirming that the environment is indeed WSL (checking `/proc/sys/fs/binfmt_misc/WSL` or `/proc/version`).
- Confirming the OS version is Ubuntu 26.04.
- Checking that `WSL_DEVELOPMENT_MODE=true` is set.
- Bootstrapping dependencies, loading necessary WSL kernel variables (such as enabling unprivileged port binding), and calling the Ansible playbook.

### 2. The Ansible Playbook (`wsl_feedback_playbook.yml`)
The playbook coordinates:
- Validating rootless Podman 5+ compatibility.
- Deploying the mock or real SongketMail fabric inside the unprivileged user session.
- Simulating a mock client-IP mail session using BunkerWeb and Postfix.
- Pulling state updates and writing/posting the formatted markdown results to the GitHub PR and Jules.

---

*Deep State of Mind (DSOM) For My AI Protocol | Harisfazillah Jamel (LinuxMalaysia) | 2026-08-07*
*Standard: UK English | DBP-standard Bahasa Melayu Malaysia (Piawai) | GNU General Public License v3.0*
