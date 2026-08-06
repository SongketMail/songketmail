---
okf_version: 0.1
type: agent_skill
title: "Google Jules Sandbox & Virtualization Limitations Skill"
name: jules-sandbox-mode
description: "Detailed documentation of Google Jules sandbox and virtualization constraints, dynamic privilege levels, and Pre-Remediation Safety checks."
resource: "file:///.agents/skills/jules-sandbox-mode/SKILL.md"
timestamp: 2026-08-06T22:30:00Z
topics: [skills, jules, sandbox, virtualization, privilege, asimp, security]
---

# 🕵️‍♂️ Google Jules Sandbox & Virtualization Limitations Skill

This skill documents the engineering constraints, dynamic privilege model, and validation gates required for autonomous AI agents (such as Google Jules) executing security hardening, auditing, and rootless container deployment tasks within container-isolated or virtualization-restricted unprivileged environments.

---

## 🎯 When to use this skill
- Use this skill when evaluating system administrative rights on target nodes (`node1.songketmail.internal`, `node2.songketmail.internal`, `jump_host`).
- Use this skill when executing the ASIMP security hardening playbooks or designing automated safety gates to prevent OS or SSH configuration breakages.

---

## 🧪 Jules Sandbox & Virtualization Constraints

When running inside an unprivileged sandbox or lightweight container virtualization (such as Google Jules, Docker, or rootless LXC environments), several severe operating system constraints exist:

1.  **No Genuine Superuser Capability**:
    - Privilege escalation (`become: yes`) is completely blocked or simulated without actual OS-level write access to root-only domains.
2.  **Inaccessible Host Service Manager**:
    - Systemd is not running as PID 1. Thus, standard service management commands (`systemctl start`, `systemctl restart` or the Ansible `ansible.builtin.service` module) targeting host daemons like `auditd`, `chrony`, or `sshd` will crash or throw execution exceptions.
3.  **Kernel Parameters and ProcFs Restrictions**:
    - Writing to `/proc/sys/` (using tools like `sysctl` or `ansible.posix.sysctl`) or loading kernel modules (such as `modprobe br_netfilter`) is blocked.
4.  **Disabled System Package Managers**:
    - Standard system package repositories (e.g. `apt-get`, `yum`, `dnf`) are read-only or restricted due to lack of real root privileges, preventing package addition/removal on the host.

---

## ⚡ Dynamic Privilege Detection & Flow Control

To operate gracefully across both highly constrained sandboxes and production-grade bare-metal/VM machines, we employ dynamic privilege level auto-detection:

### 1. Privilege Level Auto-Detection
The python gate check script (`scripts/privilege_and_safety_test.py`) tests passwordless sudo, systemctl connection, and procfs writeability to assign the host one of two distinct privilege values:

- **`limited_sandbox`**: Representing a limited sandbox/ordinary user.
- **`full_privilege`**: Representing a full-privilege system (root or passwordless sudo).

This variable (`asimp_privilege_level`) is saved in `data/privilege_and_safety_report.json` and loaded as an Ansible fact.

### 2. Forked Execution Control Flow

#### 🟢 Limited Sandbox Mode (`asimp_privilege_level == 'limited_sandbox'`)
- All system-altering remediation tasks (packages, kernel modifications, SSHD file edits, service restarts) are **skipped / bypassed** to prevent playbook execution failure.
- The pipeline executes **real-time audits and scans** (using unprivileged local/portable Lynis and OpenSCAP binary scanning where supported).
- If system tools are completely restricted, the reporting engine gracefully falls back to baseline simulation scores to allow report compilation and pipeline continuity.

#### 🟠 Full Privilege Mode (`asimp_privilege_level == 'full_privilege'`)
- A mandatory **Pre-Remediation Safety Check & Break-Prevention Verification** block is executed BEFORE applying any modifications.
- If a critical or high safety hazard is detected (such as missing authorized SSH keys or an active port conflict), the remediation is **immediately aborted** via an assertion to prevent lockout or system corruption.
- If all safety gates pass successfully, the playbook executes all-out security remediation.

---

## 🛡️ Pre-Remediation Safety Check and Break-Prevention Verification Block

The following verification logic is integrated into the security hardening playbooks to act as an automated safety gate on full-privilege systems:

```yaml
- name: Pre-Remediation Safety Check & Break-Prevention Verification Block
  block:
    - name: Print safety assessment check status
      ansible.builtin.debug:
        msg: "Pre-Remediation Safety Check & Break-Prevention Verification initiated on full-privilege system."

    - name: Verify no critical risk factors that would break the system or access
      ansible.builtin.assert:
        that:
          - asimp_risk_level not in ['CRITICAL_RISK', 'HIGH_RISK']
        fail_msg: "Pre-Remediation Safety Check failed: High or Critical risk of system breakage detected. Aborting modifications!"
  when:
    - asimp_privilege_level == 'full_privilege'
    - not (skip_remediation | default(false) | bool)
```

By enforcing this guardrail, autonomous agents can guarantee that security hardening does not result in accidental operational downtime or administrator lockouts.

---
*Deep State of Mind (DSOM) For My AI Protocol | Harisfazillah Jamel (LinuxMalaysia) | 2026-08-06*
*Standard: UK English | DBP-standard Bahasa Melayu Malaysia (Piawai) | GNU General Public License v3.0*
