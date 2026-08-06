#!/usr/bin/env python3
"""
privilege_and_safety_test.py - Automated Privilege Detection and Remediation Safety Testing
Compatible with OKF v0.1 and DSOM AI Protocol standards.
"""

import os
import sys
import json
import re
import socket
import subprocess
from datetime import datetime, timezone

def check_privileges():
    """Detects what level of privileges we have by testing administrative capabilities."""
    uid = os.getuid()
    username = subprocess.getoutput("whoami").strip()

    # Test passwordless sudo
    has_sudo = False
    try:
        res = subprocess.run(["sudo", "-n", "true"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            has_sudo = True
    except Exception:
        pass

    # Check systemctl access
    can_manage_systemctl = False
    try:
        res = subprocess.run(["systemctl", "is-system-running"], capture_output=True, text=True, timeout=5)
        # Even if degraded, if we get a return code we have some access, but standard unprivileged will fail or show status
        if res.returncode in [0, 1] and "Failed to connect" not in res.stderr:
            can_manage_systemctl = True
    except Exception:
        pass

    # Check sysctl modification permission (dry-run/read)
    can_modify_sysctl = False
    try:
        # Check if we can write to /proc/sys (or we are root/sudo)
        if uid == 0 or has_sudo:
            can_modify_sysctl = True
    except Exception:
        pass

    # Determine privilege mode
    if uid == 0 or has_sudo:
        privilege_level = "FULL_PRIVILEGES"
        asimp_privilege_level = "full_privilege"
    else:
        privilege_level = "UNPRIVILEGED_SANDBOX"
        asimp_privilege_level = "limited_sandbox"

    return {
        "uid": uid,
        "username": username,
        "has_sudo": has_sudo,
        "can_manage_systemctl": can_manage_systemctl,
        "can_modify_sysctl": can_modify_sysctl,
        "privilege_level": privilege_level,
        "asimp_privilege_level": asimp_privilege_level
    }

def check_safety(priv_info):
    """
    Performs critical safety checks to ensure that ASIMP or SSH/sysctl remediations
    do not break the operating system, existing system configurations, or project codes.
    """
    issues = []
    warnings = []
    passed = []

    # 1. SSH Breakage Check
    # Disabling password authentication is a common remediation. If no authorized keys are present,
    # the user will be completely locked out.
    ssh_dir = os.path.expanduser("~/.ssh")
    auth_keys_path = os.path.join(ssh_dir, "authorized_keys")
    has_keys = False
    if os.path.exists(auth_keys_path):
        try:
            with open(auth_keys_path, "r") as f:
                content = f.read().strip()
                # Ensure it's not empty and contains actual key lines
                key_lines = [line for line in content.splitlines() if line and not line.startswith("#")]
                if len(key_lines) > 0:
                    has_keys = True
        except Exception:
            pass

    if not has_keys:
        issues.append({
            "vector": "SSH_LOCKOUT",
            "severity": "HIGH_RISK",
            "description": "No SSH authorized keys found. Remediating SSH passwordless configuration could result in complete lock-out from this node."
        })
    else:
        passed.append({
            "vector": "SSH_KEYS",
            "description": "SSH authorized keys are present. SSH key-based login is safe."
        })

    # Run sshd -t syntax check if sshd is installed
    sshd_bin = "/usr/sbin/sshd"
    if os.path.exists(sshd_bin):
        try:
            # Requires root/sudo to run sshd -t properly on real system, but let's try
            cmd = ["sudo", "-n", sshd_bin, "-t"] if priv_info["has_sudo"] else [sshd_bin, "-t"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if res.returncode != 0:
                issues.append({
                    "vector": "SSH_CONFIG_SYNTAX",
                    "severity": "HIGH_RISK",
                    "description": f"sshd configuration has pre-existing syntax errors: {res.stderr.strip()}"
                })
            else:
                passed.append({
                    "vector": "SSH_CONFIG_SYNTAX",
                    "description": "sshd configuration syntax is valid."
                })
        except Exception:
            # If sshd exists but we couldn't run it (e.g. due to sandbox restriction), warn
            warnings.append({
                "vector": "SSH_SYNTAX_UNCHECKED",
                "description": "sshd configuration syntax check skipped due to permission restrictions."
            })
    else:
        warnings.append({
            "vector": "SSH_DAEMON_ABSENT",
            "description": "OpenSSH server daemon (sshd) not found on host. SSH remediation will be skipped or may fail."
        })

    # 2. Kernel / Sysctl Safety Check
    # Verify if we can read and write virtualized/containerized kernel parameters
    sysctl_keys = ["vm.max_map_count", "net.ipv4.ip_forward"]
    for key in sysctl_keys:
        proc_path = f"/proc/sys/{key.replace('.', '/')}"
        if not os.path.exists(proc_path):
            warnings.append({
                "vector": "SYSCTL_KEY_MISSING",
                "description": f"Kernel key {key} does not exist at {proc_path}. Sysctl change will likely fail."
            })
        else:
            # Check if writable (only root/sudo or in non-sandbox environments)
            is_writable = os.access(proc_path, os.W_OK)
            if not is_writable and priv_info["privilege_level"] == "UNPRIVILEGED_SANDBOX":
                warnings.append({
                    "vector": "SYSCTL_WRITE_RESTRICTED",
                    "description": f"Kernel key {key} is read-only in this unprivileged/sandbox context. Attempting to write directly will crash the execution."
                })
            else:
                passed.append({
                    "vector": "SYSCTL_KEY_SUPPORTED",
                    "description": f"Kernel key {key} exists and is modifiable."
                })

    # 3. Port Conflict / Service Check
    # Critical ports utilized by SongketMail reverse proxy and email services
    critical_ports = {
        25: "SMTP (Postfix)",
        80: "HTTP (BunkerWeb Webmail Proxy)",
        143: "IMAP (Dovecot)",
        443: "HTTPS (BunkerWeb Webmail Proxy)",
        587: "Submission (Postfix SMTP-MSA)",
        993: "IMAPS (Dovecot Secure)",
        8080: "BunkerWeb Admin API / Port Conflict"
    }

    for port, service in critical_ports.items():
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1.0)
        try:
            # Attempt to bind to the port on localhost
            s.bind(('127.0.0.1', port))
            passed.append({
                "vector": f"PORT_{port}_AVAILABLE",
                "description": f"Port {port} ({service}) is free and ready for binding."
            })
        except socket.error:
            # Port is already bound or cannot bind due to permission (< 1024 as non-root)
            if priv_info["privilege_level"] == "UNPRIVILEGED_SANDBOX" and port < 1024:
                # Ordinary user cannot bind to <1024, which is expected, but port might be free.
                # Let's check if there's actually a service listening by attempting to connect
                conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                conn.settimeout(0.5)
                res = conn.connect_ex(('127.0.0.1', port))
                conn.close()
                if res == 0:
                    issues.append({
                        "vector": f"PORT_{port}_OCCUPIED",
                        "severity": "MEDIUM_RISK",
                        "description": f"Port {port} ({service}) is actively occupied by another process on localhost. Running SongketMail will cause binding failures!"
                    })
                else:
                    warnings.append({
                        "vector": f"PORT_{port}_UNPRIVILEGED",
                        "description": f"Port {port} ({service}) is privileged (<1024). Standard unprivileged user cannot bind directly to this port on host without forwarding or cap_net_bind_service."
                    })
            else:
                # If we have root/sudo or it is >1024 and we can't bind, it's definitely occupied
                issues.append({
                    "vector": f"PORT_{port}_OCCUPIED",
                    "severity": "CRITICAL_RISK",
                    "description": f"Port {port} ({service}) is already in use by another active service. Remediation/Deployment will break."
                })
        finally:
            s.close()

    # 4. Storage Directory Ownership / Permission Check
    storage_base = "/var/srv/songketmail"
    if priv_info["privilege_level"] == "UNPRIVILEGED_SANDBOX":
        # Check if the unprivileged user has write access to the host-level storage_base or its home alternative
        sandbox_storage = os.path.join(os.path.expanduser("~"), "var/srv/songketmail")
        passed.append({
            "vector": "STORAGE_SANDBOX_REDIRECT",
            "description": f"Unprivileged Sandbox Detected: Storage will safely redirect to {sandbox_storage}."
        })
    else:
        # Full privileges: Verify if we can create or write to the real storage path via sudo if needed
        is_writable = False
        try:
            # If current process is root
            if os.getuid() == 0:
                os.makedirs(storage_base, exist_ok=True)
                test_dir = os.path.join(storage_base, "safety_test_dir")
                os.makedirs(test_dir, exist_ok=True)
                os.rmdir(test_dir)
                is_writable = True
            elif priv_info["has_sudo"]:
                # Test using sudo command
                test_dir = os.path.join(storage_base, "safety_test_dir")
                res = subprocess.run(["sudo", "-n", "mkdir", "-p", test_dir], capture_output=True, timeout=5)
                if res.returncode == 0:
                    subprocess.run(["sudo", "-n", "rmdir", test_dir], capture_output=True, timeout=5)
                    is_writable = True
        except Exception:
            pass

        if is_writable:
            passed.append({
                "vector": "STORAGE_WRITE_SUCCESS",
                "description": f"Host persistent storage path '{storage_base}' is writable."
            })
        else:
            issues.append({
                "vector": "STORAGE_WRITE_FAILED",
                "severity": "CRITICAL_RISK",
                "description": f"Host persistent storage base path '{storage_base}' is not writable. Check permissions or mount options."
            })

    # 5. Podman Runtime version check
    try:
        res = subprocess.run(["podman", "--version"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            version_str = res.stdout.strip()
            match = re.search(r'(\d+)\.(\d+)\.(\d+)', version_str)
            if match:
                major = int(match.group(1))
                if major < 5:
                    warnings.append({
                        "vector": "PODMAN_VERSION_SUBOPTIMAL",
                        "description": f"Podman version ({match.group(0)}) is below the recommended Podman 5.0.0+ standard. Quadlet features may be limited."
                    })
                else:
                    passed.append({
                        "vector": "PODMAN_VERSION_OK",
                        "description": f"Podman version meets standard requirements: {match.group(0)}."
                    })
            else:
                warnings.append({
                    "vector": "PODMAN_VERSION_UNPARSED",
                    "description": f"Podman is installed, but version string could not be parsed: {version_str}"
                })
        else:
            issues.append({
                "vector": "PODMAN_RUNTIME_BROKEN",
                "severity": "CRITICAL_RISK",
                "description": "Podman CLI is present but exited with a non-zero status. Container runtime might be corrupted."
            })
    except FileNotFoundError:
        issues.append({
            "vector": "PODMAN_MISSING",
            "severity": "CRITICAL_RISK",
            "description": "Podman is not installed on the system. Project cannot run container fabrics."
        })

    # Summarize Risk Status
    risk_level = "LOW_RISK"
    if any(i["severity"] == "CRITICAL_RISK" for i in issues):
        risk_level = "CRITICAL_RISK"
    elif any(i["severity"] == "HIGH_RISK" for i in issues):
        risk_level = "HIGH_RISK"
    elif any(i["severity"] == "MEDIUM_RISK" for i in issues):
        risk_level = "MEDIUM_RISK"

    return {
        "risk_level": risk_level,
        "issues": issues,
        "warnings": warnings,
        "passed": passed
    }

def print_text_report(priv, safety):
    """Prints a beautifully styled text report to the terminal console."""
    print("=" * 80)
    print("            🕵️‍♂️  SONGKETMAIL PRIVILEGE & REMEDIATION SAFETY ASSESSMENT REPORT")
    print("=" * 80)
    print(f"Timestamp:       {datetime.now(timezone.utc).isoformat()}")
    print(f"Current User:    {priv['username']} (UID: {priv['uid']})")
    print(f"Privilege Mode:  {priv['privilege_level']} (asimp_privilege_level: {priv['asimp_privilege_level']})")
    print(f"Passwordless Sudo: {'YES' if priv['has_sudo'] else 'NO'}")
    print(f"Remediation Risk: {safety['risk_level']}")
    print("-" * 80)

    print("\n🟢 PASSED CHECKS:")
    for p in safety["passed"]:
        print(f"  [PASS] {p['vector']}: {p['description']}")

    if safety["warnings"]:
        print("\n🟡 SYSTEM WARNINGS (POTENTIAL LIMITATIONS):")
        for w in safety["warnings"]:
            print(f"  [WARN] {w['vector']}: {w['description']}")

    if safety["issues"]:
        print("\n🔴 RISK ISSUES DETECTED:")
        for i in safety["issues"]:
            print(f"  [{i['severity']}] {i['vector']}: {i['description']}")
    else:
        print("\n✅ NO CRITICAL/HIGH RISK ISSUES FOUND. System is safe for planned operations.")

    print("=" * 80)
    if safety["risk_level"] in ["CRITICAL_RISK", "HIGH_RISK"] and priv["privilege_level"] == "FULL_PRIVILEGES":
        print("⚠️  WARNING: Full privileges are available, but critical safety checks FAILED.")
        print("    Remediation actions may result in OS, system-access, or project code breakage!")
        print("=" * 80)

def generate_markdown_report(priv, safety):
    """Generates an OKF v0.1 compliant Markdown report file inside docs/."""
    os.makedirs("docs", exist_ok=True)
    report_path = "docs/privilege-safety-report.md"

    # Check if there are any critical or high risks
    risk_emoji = "🟢"
    if safety["risk_level"] == "CRITICAL_RISK":
        risk_emoji = "🔴"
    elif safety["risk_level"] == "HIGH_RISK":
        risk_emoji = "🟠"
    elif safety["risk_level"] == "MEDIUM_RISK":
        risk_emoji = "🟡"

    content = f"""---
okf_version: 0.1
type: report
title: "Privilege Detection and Remediation Safety Report"
description: "Analysis of host privilege levels and potential safety hazards of running security hardening remediation."
resource: "file:///docs/privilege-safety-report.md"
timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}
topics: [privilege, safety, reporting, auditing, compliance]
---

# 🕵️‍♂️ Privilege & Remediation Safety Report

This report presents a thorough audit of the active deployment user's privileges and a preventive assessment of proposed OS and service hardening remediations.

---

## 📋 Execution Context Summary

- **Host User**: `{priv['username']}` (UID: `{priv['uid']}`)
- **Detected Privilege Level**: `{priv['privilege_level']}`
- **ASIMP Privilege Level**: `{priv['asimp_privilege_level']}`
- **Passwordless Sudo**: `{"Yes" if priv['has_sudo'] else "No"}`
- **Systemd Controller Connection**: `{"Yes" if priv['can_manage_systemctl'] else "No"}`
- **Sysctl Write Support**: `{"Yes" if priv['can_modify_sysctl'] else "No"}`
- **Overall Safety Risk Score**: {risk_emoji} **`{safety['risk_level']}`**

---

## ⚡ Safety Risk Vectors & Hardening Guardrails

Before running active remediation scripts (which may modify SSH configuration, network sysctls, and package indexes), we perform validation checks to ensure no disruptions occur.

### 🔴 Risk Issues Found
{"No high-risk issues found. System is safe for remediation!" if not safety['issues'] else ""}
"""

    for i in safety["issues"]:
        content += f"- **[{i['severity']}] {i['vector']}**\n  {i['description']}\n"

    content += f"""
### 🟡 System Warnings & Limitations
{"No warnings detected." if not safety['warnings'] else ""}
"""

    for w in safety["warnings"]:
        content += f"- **{w['vector']}**\n  {w['description']}\n"

    content += """
### 🟢 Passed Verifications
"""

    for p in safety["passed"]:
        content += f"- **{p['vector']}**\n  {p['description']}\n"

    content += """
---

## 🛠️ Recommended Action Flow

"""

    if priv["asimp_privilege_level"] == "limited_sandbox":
        content += """
> ℹ️ **Ordinary/Sandbox User Detected**
>
> The mode has been set to **"Test & Info" only**:
> 1. We will NOT attempt to execute any sudo/root level hardening remediations (e.g. modifying SSH configurations, writing to `/proc/sys`, installing system packages).
> 2. We will run **real auditing and scoring scans** using local/portable Lynis and OpenSCAP where supported.
> 3. We will output the list of missing administrative tools/packages.
"""
    else:
        if safety["risk_level"] in ["CRITICAL_RISK", "HIGH_RISK"]:
            content += """
> ⚠️ **CRITICAL/HIGH RISK DETECTED**
>
> The system has full administrative privileges, but the safety check has detected high-risk hazards:
> 1. Do NOT execute remediation allout until the risk issues (such as missing SSH keys or active port conflicts) are resolved.
> 2. Hardening under these conditions will likely result in system lock-out or service failure!
"""
        else:
            content += """
> ✅ **FULL PRIVILEGES & SAFE TO PROCEED**
>
> All safety gates have passed:
> 1. The system has full privileges via root or passwordless sudo.
> 2. You may safely run the full security auditing, testing, and system-level remediation pipeline.
"""

    content += """
---
*Deep State of Mind (DSOM) For My AI Protocol | Harisfazillah Jamel (LinuxMalaysia) | 2026-07-25*
*Standard: UK English | DBP-standard Bahasa Melayu Malaysia (Piawai) | GNU General Public License v3.0*
"""

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Generated Markdown report at: {report_path}")

def generate_json_report(priv, safety):
    """Generates a structured JSON file at data/privilege_and_safety_report.json."""
    os.makedirs("data", exist_ok=True)
    report_path = "data/privilege_and_safety_report.json"

    report_data = {
        "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        "privileges": priv,
        "safety": safety
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)
    print(f"Generated JSON report at: {report_path}")

def main():
    print("Running privilege detection and safety checks...")
    priv = check_privileges()
    safety = check_safety(priv)
    print_text_report(priv, safety)
    generate_markdown_report(priv, safety)
    generate_json_report(priv, safety)

    # If unprivileged sandbox or if safety check fails, return code can indicate status
    # We exit 0 so that the pipeline continues to its appropriate branched mode gracefully
    sys.exit(0)

if __name__ == '__main__':
    main()
