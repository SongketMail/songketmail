---
okf_version: 0.1
type: documentation
title: "Ansible Playbook and Related Documents Map"
description: "A comprehensive map linking all automated Ansible playbooks to their corresponding operational, monitoring, and deployment documents."
resource: "file:///docs/ansible-playbook-map.md"
timestamp: 2026-07-25T14:00:00Z
topics: [ansible, playbook-map, deployment, monitoring, operations]
---

# 🤖 Ansible Playbook and Related Documents Map

This document establishes a unified, complete mapping of all **Ansible playbooks** within the SongketMail repository. By orchestrating our entire lifecycle—from secure OS hardening to local WSL developer telemetry—via declarative Ansible automation, we guarantee that all services are **Ansible-driven** across three critical pillars: **Deployment**, **Monitoring**, and **Operations**.

---

## 🗺️ Master Playbook and Document Matrix

The table below connects each automation playbook to its roles, managed services, operational scope, and corresponding documentation parts:

| Playbook | Purpose | Roles & Modules Utilized | Services Managed / Audited | Related Documentation |
|:---|:---|:---|:---|:---|
| **`site.yml`** | Primary Core Fabric Deployment | `host_prepare`<br>`podman_quadlet` | BunkerWeb, Postfix, Dovecot, PostgreSQL, RustFS, Roundcube, Rspamd, Smallstep CA | [Part 1](podman-rootless.md), [Part 2](ansible-fqcn.md), [Part 3](postfix-dovecot.md), [Part 4](s3-storage.md), [Part 5](webmail-clients.md), [Part 6](bunkerweb-proxy.md), [Part 7](architectural-blueprint.md), [Part 11](dockpod-integration.md), [Part 12](jules-planning.md), [Part 17](mail-web-app-verification.md), [Part 25](email-security-design.md) |
| **`asimp_hardening_playbook.yml`** | OS Security Hardening, Auditing & Compliance | `scripts/privilege_and_safety_test.py`<br>`asimp/play-localhost.yml`<br>`scripts/update_sidebars.py` | Host OS Kernel, systemd services, OpenSCAP, Lynis Auditing | [Part 13](asimp-hardening-report.md), [Part 14](SOP-KNOWLEDGE-FIRST-DISCOVERY.md), [Part 16](ANSIBLE-ADOPTION-REVIEW.md) |
| **`wsl_feedback_playbook.yml`** | WSL Developer Testing & Telemetry Feedback | `ansible.builtin.shell`<br>`ansible.builtin.uri`<br>`jules` CLI commands | Local WSL Platform, Podman Mappings, GitHub PR Comments | [Part 15](wsl-development-feedback.md) |
| **`playbooks/matrix_test.yml`** | Multi-OS Local Test Matrix Orchestration | `containers.podman`<br>`playbooks/tasks/run_distro.yml`<br>`feedback_collector` | Ubuntu 24.04, Ubuntu 26.04, AlmaLinux 9, Debian 12 | [Part 16](ANSIBLE-ADOPTION-REVIEW.md) |

---

## 🏗️ 1. Deployment: The `site.yml` Playbook

The **`site.yml`** playbook acts as the master orchestration baseline for the **SongketMail Email Server Fabric**. It implements the core deployment architecture by dividing responsibilities into two distinct phases (rootful host configuration vs. rootless application delivery).

### A. Host Preparation (`host_prepare` role)
Executes system-level configurations to bootstrap a secure, unprivileged environment:
*   **Package Provisioning**: Installs base utilities, Python packages, Podman 5, and Podman-Docker compatibility layers.
*   **Kernel Optimizations**: Modifies `/etc/sysctl.d/99-songketmail.conf` to set `net.ipv4.ip_unprivileged_port_start=25` (allowing rootless binding of SMTP/HTTP ports) and increases memory map limits for databases.
*   **Sovereign Storage Mapping**: Dynamically provisions 14 host-level directories under `/var/srv/songketmail/` with strict `0700` permissions, owned natively by the unprivileged user account (UID/GID `2001:2001`).
*   **User Management**: Sets up the non-root `songketmail` user and enables systemd linger (`loginctl enable-linger`) to persist background container lifecycles beyond active ssh sessions.

### B. Container Orchestration (`podman_quadlet` role)
Deploys the 8-service decoupled container mesh strictly in unprivileged space:
*   Generates native systemd-user **Quadlet files** (`.container`, `.pod`, `.network`) in `/home/songketmail/.config/containers/systemd/`.
*   Triggers the systemd user manager `systemctl --user daemon-reload` and enables the cluster services.
*   Enforces user namespace parity via `keep-id:uid=2001,gid=2001` on mapped storage mounts.

---

## 🛡️ 2. Operations & Security: The `asimp_hardening_playbook.yml` Playbook

The **`asimp_hardening_playbook.yml`** playbook handles host-level security audits and compliance enforcement. It guarantees that our production servers conform to baseline standards while remaining safe to use in unprivileged virtual containers or development sandboxes.

### A. Pre-Remediation Safety Gate
Runs the single-responsibility python verifier `scripts/privilege_and_safety_test.py` to identify risk factors before applying system changes:
*   Checks for active port usage conflicts to avoid binding failures.
*   Verifies SSH key files to prevent developer lockout.
*   Audits file-write capabilities across mapped storage paths.
*   Classifies environment privileges into either `full_privilege` or `limited_sandbox` (Google Jules).

### B. Automated Hardening & Reporting
*   **Dynamic Privilege Branching**: Automatically skips kernel-dependent or time-sync services (like `auditd` and `chrony`) on limited sandboxes to prevent playbook execution failures.
*   **Auditing Integrations**: Runs standard SCAP security guide scans and computed Lynis evaluations.
*   **OKF Report Compilations**: Dynamically templates results into compliance files (`docs/asimp-hardening-report.md` and `.html`) and invokes `scripts/update_sidebars.py` to keep documentation indexes unified.

---

## 📊 3. Monitoring & Feedback Loops

Continuous telemetry, validation, and feedback collection are driven entirely via Ansible's diagnostic playbooks.

### A. Multi-OS Matrix Validation (`playbooks/matrix_test.yml`)
Orchestrates an isolated testing matrix on local engines to verify playbook behavior across target Linux distributions (Ubuntu, AlmaLinux, Debian).
*   Utilizes loop tasks to spin up rootless distro containers.
*   Runs baseline test scripts internally to confirm package availability and Quadlet template compatibility.

### B. WSL Telemetry & GitHub feedback Loop (`wsl_feedback_playbook.yml`)
A development-gated playbook designed to integrate execution telemetry directly with developer feedback channels:
*   **System Integrity Checking**: Programmatically parses host OS releases, subuid mappings, and active Podman versions.
*   **Bi-directional Telemetry Stream**: Streams structured test outcomes directly to active Jules CLI sessions and issues API requests to comment on matching GitHub Pull Requests.
*   **Production Gate Security**: Strictly restricted via the `wsl_development_mode` toggle to prevent accidental executions in regular production clusters.

---

## 🔗 Related Documentation & Navigation Guide

Each playbook is supported by a rich, interactive suite of documents to provide deep, readable insights for human operators and AI agents:

*   **[Part 1: Podman Rootless & Quadlets](podman-rootless.md)**: Deep dive into systemd user-manager parameters (`XDG_RUNTIME_DIR`), linger setups, and unprivileged user mappings.
*   **[Part 2: Ansible Best Practices](ansible-fqcn.md)**: Details Ansible FQCN usage, YAML callback formatting, and SSH pipelining optimizations.
*   **[Part 7: Unified Architectural Blueprint](architectural-blueprint.md)**: Contains master container block diagrams, isolated network layouts, and mapped storage schemas.
*   **[Part 13: ASIMP Compliance Report](asimp-hardening-report.md)**: Houses generated compliance scores, risk matrices, and platform privilege reports.
*   **[Part 15: WSL Developer Feedback Loop](wsl-development-feedback.md)**: Outlines developer mode variables, telemetry formatting, and API comments configurations.
*   **[Part 17: Mail Web Ingress Verification](mail-web-app-verification.md)**: Programmatically verifies proxy port bindings (`25, 80, 443, 587, 993`) and Quadlet configuration templates.
*   **[Part 25: Email Security & JMAP Protocol](email-security-design.md)**: Details wire-to-mailbox transport encryption (DANE, MTA-STS, TLSRPT), Smallstep ACMEv2 CA, OpenPGP/S/MIME mailbox encryption at rest, JMAP web API integration, and security Ansible variables.

---
*Deep State of Mind (DSOM) For My AI Protocol | Harisfazillah Jamel (LinuxMalaysia) | 2026-07-25*
*Standard: UK English | DBP-standard Bahasa Melayu Malaysia (Piawai) | GNU General Public License v3.0*
