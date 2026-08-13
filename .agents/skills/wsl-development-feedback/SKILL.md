---
okf_version: 0.1
type: agent_skill
title: "WSL Ubuntu 26.04 & Jules CLI Feedback Loop Skill"
name: wsl-development-feedback
description: "Instructs AI agents on executing sequential multi-distro container tests, capturing telemetry, and dispatching feedback to Google Jules CLI and GitHub Pull Requests."
resource: "file:///.agents/skills/wsl-development-feedback/SKILL.md"
timestamp: 2026-08-25T12:00:00Z
topics: [skills, wsl, ubuntu-26-04, feedback-loop, telemetry, jules-cli]
---

# 💻 WSL Ubuntu 26.04 & Jules CLI Feedback Loop Skill

This skill teaches Google Antigravity and other AI agents the guidelines and operational workflows for running container-orchestrated multi-distro test matrices under Windows WSL (Ubuntu 26.04) and streaming diagnostic telemetry back to Google Jules CLI and GitHub Pull Requests.

---

## 🎯 When to use this skill
- Use this skill during active development sessions to verify playbook portability across multiple operating systems.
- Use this skill when troubleshooting container engine socket activation or verifying telemetry reporting endpoints.

---

## 🚫 Strictly Enforced Development Gate

To guarantee security and runtime isolation, this telemetry integration is heavily gated:
- **Bash Gating**: `scripts/jules_gh_feedback.sh` terminates immediately unless the environment variable `EXECUTION_MODE` is set to `dev`.
- **Ansible Gating**: `playbooks/matrix_test.yml` checks that the variable `wsl_development_mode` is set to `true`.

---

## ⚙️ WSL 2 & Podman 5+ Environment Setup

Ubuntu 26.04 fully supports systemd, which is required for unprivileged user-level Quadlet and daemon management.

### 1. Enabling Systemd inside WSL
Add the boot section inside `/etc/wsl.conf` and restart the WSL instance:
```ini
[boot]
systemd=true
```

### 2. Version-Pinned Collection Installation
Prior to executing matrix playbooks, ensure requirements collections are installed locally:
```bash
ansible-galaxy collection install -r playbooks/requirements.yml
```

---

## 📊 Telemetry Aggregation & API Integration

The multi-OS matrix targets Ubuntu 24.04, Ubuntu 26.04, AlmaLinux 9, and Debian 12 sequentially. The execution reports are summarized and dispatched:

### 1. Telemetry Storage Format (`data/jules_telemetry.json`)
Saves essential system state, failure logs, and differential analysis results for the agent.

### 2. Interactive Reporting Loop (`scripts/jules_gh_feedback.sh`)
Refactored to standardize API operations and securely stream reports:
- **Jules CLI Integration**: Appends telemetry to active cloud workspace tasks:
  ```bash
  jules remote new --task-id "$JULES_TASK_ID" --report-file "./data/jules_telemetry.json"
  ```
- **GitHub PR Comment Integration**: Standardizes curl headers and posts diagnostic comments directly onto active pull requests using a unified `github_api_request` function with precise timeouts and error handling.

---
*Deep State of Mind (DSOM) For My AI Protocol | Harisfazillah Jamel (LinuxMalaysia) | 2026-08-25*
*Standard: UK English | DBP-standard Bahasa Melayu Malaysia (Piawai) | GNU General Public License v3.0*
