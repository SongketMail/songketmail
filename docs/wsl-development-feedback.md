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

This document outlines the architecture, operating instructions, and execution details of the development-only testing harness designed for Windows Subsystem for Linux (WSL) running **Ubuntu 26.04 (Resolute Raccoon)**. This environment runs real OS workloads outside of the Google Jules unprivileged container sandbox, enabling deep multi-environment testing and automated integration reporting back to Google Jules and active GitHub Pull Requests.

---

## 🎨 Architectural Intent & Boundary

To preserve stability and ease of deployment for end-users, this feedback and testing framework is **strictly limited to development sessions**.

```
┌─────────────────────────────────────────────────────────┐
│               Local WSL 2 (Ubuntu 26.04)                │
│  - Real OS host kernel                                  │
│  - Systemd user session manager running                 │
│  - Podman 5+ installed                                  │
└────────────────────────────┬────────────────────────────┘
                             │
                             ▼  [scripts/jules_gh_feedback.sh]
┌─────────────────────────────────────────────────────────┐
│              playbooks/matrix_test.yml                  │
│  - Verifies WSL 2 systemd socket and Quadlet engine     │
│  - Executes parallel multi-distro container matrix test  │
│  - Captures failure logs, exit codes, and diff analysis │
│  - Serializes report to /tmp/jules_telemetry.json       │
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
1.  **Environment Variable Gate**: The bash runner `scripts/jules_gh_feedback.sh` terminates immediately unless `EXECUTION_MODE` is explicitly set to `dev`.
2.  **Ansible Playbook Gate**: The playbook `playbooks/matrix_test.yml` performs a strict check against the `execution_mode` variable (which defaults to `user` in normal runs) and gracefully skips testing if disabled.

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

### 3. Install Version-Pinned Ansible Collection
To run tasks involving containers.podman cleanly, install the requirements collection first:
```bash
# Verify the playbooks/requirements.yml configuration
cat playbooks/requirements.yml

# Execute the installation command
ansible-galaxy collection install -r playbooks/requirements.yml
```

### 4. Configure Rootless SubUID/SubGID Mappings
Create the target development user mapping (e.g., for the user `songketmail` or your developer account with UID 2001):
```bash
sudo groupadd -g 2001 songketmail || true
sudo useradd -u 2001 -g 2001 -m -s /bin/bash songketmail || true
echo "songketmail:100000:65536" | sudo tee -a /etc/subuid
echo "songketmail:100000:65536" | sudo tee -a /etc/subgid
```

---

## 🔄 Human-in-the-Loop Developer Workflow

The telemetry-driven engineering cycle coordinates local execution and cloud sessions:

```
+-----------------------------------------------------------+
| 1. Human asks Jules to fix an issue / generate code      |
+-----------------------------------------------------------+
                             |
                             v
+-----------------------------------------------------------+
| 2. Jules pushes branch and submits a GitHub Pull Request   |
+-----------------------------------------------------------+
                             |
                             v
+-----------------------------------------------------------+
| 3. Human executes Ansible matrix runner locally:          |
|    EXECUTION_MODE=dev ansible-playbook \                  |
|          playbooks/matrix_test.yml                        |
+-----------------------------------------------------------+
                             |
                             v
+-----------------------------------------------------------+
| 4. Multi-OS test matrix runs inside rootless Podman;      |
|    extracts exit status, logs, & outputs diagnostics JSON|
+-----------------------------------------------------------+
                             |
                             v
+-----------------------------------------------------------+
| 5. Runner script dispatches feedback:                     |
|    - Appends Markdown tables to active GitHub PR comment  |
|    - Streams diagnostics back to Google Jules CLI / API   |
+-----------------------------------------------------------+
                             |
                             v
+-----------------------------------------------------------+
| 6. Human reviews test telemetry inside Jules CLI, then    |
|    directs Jules on the subsequent refactoring steps      |
+-----------------------------------------------------------+
```

1.  **Command Execution**: Run the testing playbook:
    ```bash
    # Enforces development environment execution mode triggering the telemetry block
    EXECUTION_MODE=dev ansible-playbook playbooks/matrix_test.yml
    ```
2.  **Dispatching Telemetry**:
    ```bash
    export EXECUTION_MODE=dev JULES_TASK_ID="task-123" GITHUB_TOKEN="ghp_***" GITHUB_PR_NUMBER="1" GITHUB_REPOSITORY="SongketMail/songketmail"
    ./scripts/jules_gh_feedback.sh
    ```

---

## 🔄 The Feedback Loop Mechanics

When testing locally inside WSL, the development harness automates communications with **Google Jules CLI** and **GitHub Pull Request APIs**.

### 1. Querying Jules CLI / API
The integration uses standard environmental triggers and commands:
- **Environment Variables**: `JULES_API_URL`, `JULES_TASK_ID`, and `GITHUB_TOKEN` are passed to the WSL workspace.
- **Jules CLI**: The tool invoking `jules chat` is wrapped inside local query loops to pull updated task targets or prompt updates.
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

*Deep State of Mind (DSOM) For My AI Protocol | Harisfazillah Jamel (LinuxMalaysia) | 2026-08-07*
*Standard: UK English | DBP-standard Bahasa Melayu Malaysia (Piawai) | GNU General Public License v3.0*
