---
okf_version: 0.1
type: agent_skill
title: "SongketMail Deployment Skill"
name: songketmail-deployment
description: "Guides AI agents through host preparation, Ansible FQCN compliance, rootless session variables, and Quadlet activation."
resource: "file:///.agents/skills/songketmail-deployment/SKILL.md"
timestamp: 2026-07-04T12:00:00Z
---

# 🚀 SongketMail Deployment Skill

This skill teaches Google Antigravity and other AI agents the step-by-step procedures for server host preparation, Ansible FQCN compliance, rootless session variables, and Quadlet activation.

## 🎯 When to use this skill
- Use this skill when deploying, updating, or maintaining SongketMail services via Ansible.
- Use this skill when configuring host-level network kernel modules or debugging rootless user systemd executions.

## 📋 Host-Level Environment Tuning
Before deploying the rootless container fabric, the host OS must be prepared. These operations require root privileges (`become: yes`):

1.  **Low-Port Binding**:
    By default, unprivileged users cannot bind to ports below `1024`. Because our proxy must bind to `25`, `80`, `443`, `587`, and `993`, configure sysctl:
    ```bash
    sysctl -w net.ipv4.ip_unprivileged_port_start=25
    ```
2.  **Kernel Networking & Memory Optimizations**:
    Ensure the `br_netfilter` module is loaded and packet forwarding is enabled to support container routing:
    ```bash
    modprobe br_netfilter
    sysctl -w net.ipv4.ip_forward=1
    sysctl -w vm.max_map_count=262144
    ```
3.  **Unprivileged User & Namespace Mapping**:
    Create the unprivileged service user account `songketmail` (UID/GID `2001:2001`) and ensure subordinate UIDs/GIDs are correctly configured in `/etc/subuid` and `/etc/subgid`:
    ```bash
    songketmail:100000:65536
    ```
4.  **Systemd User Session Lingering**:
    Activate systemd linger so that the user's services run continuously without requiring an active shell session:
    ```bash
    loginctl enable-linger songketmail
    ```

## ⚙️ Ansible Best Practices & Orchestration Rules
When creating or modifying Ansible tasks in this repository, agents must follow these guidelines:

1.  **Fully Qualified Collection Names (FQCN)**:
    - Never use legacy short modules (e.g., `copy`, `template`, `sysctl`).
    - Always use FQCN. For example:
      - `ansible.builtin.copy`
      - `ansible.builtin.template`
      - `ansible.posix.sysctl`
2.  **Rootless Systemd Execution Context**:
    When invoking user systemd tasks via Ansible for the rootless user, you must explicitly declare the session environment variables:
    {% raw %}
    ```yaml
    environment:
      XDG_RUNTIME_DIR: "/run/user/{{ songketmail_uid }}"
      DBUS_SESSION_BUS_ADDRESS: "unix:path=/run/user/{{ songketmail_uid }}/bus"
    ```
    {% endraw %}

## 📦 Quadlet Activation & User Systemd Management
Container definitions are deployed as systemd Quadlet files under:
`~/.config/containers/systemd/`

To apply changes or activate containers:
1.  Perform a systemd user daemon reload to parse the Quadlet configurations:
    ```bash
    systemctl --user daemon-reload
    ```
2.  Start and enable services natively under the unprivileged user scope:
    ```bash
    systemctl --user enable --now songketmail_pod-pod.service
    ```

---
*Deep State of Mind (DSOM) For My AI Protocol | Harisfazillah Jamel (LinuxMalaysia) | 2026-07-04*
*Standard: UK English | DBP-standard Bahasa Melayu Malaysia (Piawai) | GNU General Public License v3.0*
