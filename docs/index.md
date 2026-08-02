---
okf_version: 0.1
type: documentation
title: "SongketMail: Secure Email Server Fabric"
description: "Welcome to SongketMail, an enterprise-grade, highly secure, and scalable email server baseline."
resource: "file:///docs/index.md"
timestamp: 2026-07-04T09:40:04Z
---
# 🏠 SongketMail: Secure Email Server Fabric

Welcome to **SongketMail**, an enterprise-grade, highly secure, and scalable email server baseline orchestrated using **Ansible** and unprivileged **Podman 5+ Quadlets**.

By enforcing the **"Persistence Trinity"** strategy—combining network/pod fabric isolation, native user-level systemd Quadlet orchestration, and node-isolated host storage paths—this setup delivers absolute storage sovereignty and state isolation without root privileges.

---

## 🌟 The "SongketMail" Persistence Trinity

The deployment design strictly adheres to three architectural pillars:

1. **Fabric Isolation**: Cluster-prefixed network/pod zone isolation keeps internal DB and TCP streams secure.
2. **Quadlet systemd**: Delegated directly to unprivileged systemd user session manager via Podman 5 Quadlets.
3. **Sovereign Storage**: Node-isolated directories owned strictly by `2001:2001` on the host OS natively.

---

## 🛠️ Security & Namespace Mapping

- **Storage Sovereignty**: Namespace mapping using `keep-id:uid=2001,gid=2001` preserves host and container permissions natively.
- **Systemd Lingering**: Enables background services to run continuously without active SSH sessions via `loginctl enable-linger`.
- **Host-Level Isolation**: Standardized path structures under `/var/srv/songketmail` aligned with the architectural blueprint.
- **Symmetric Privilege**: Superuser privileges for OS tuning separated from unprivileged Quadlet container specifications.
- **User-level Systemd**: Explicit configuration of `XDG_RUNTIME_DIR` and `DBUS_SESSION_BUS_ADDRESS` environment context in Ansible.
- **Decoupled Service Fabric**: A 7-service unprivileged mesh communicating on a dedicated bridge network.

---

## 📊 Optimized Deployment Stack

| Component | Description |
|---|---|
| **Runtime** | Podman 5.0+ (Rootless with UserNS=keep-id) |
| **Standards** | Ansible FQCN, systemd Quadlet, UID/GID 2001 Mapping |
| **Base Directory** | `/var/srv/songketmail` (13 customized subdirectories) |
| **Mail Protocol Ingress** | Nginx Mail Auth HTTP, Client IP via PROXY protocol |

---

## 📚 Deep Research Series

Explore our interactive and interconnected deep research topics:

1. [Rootless Podman 5+ & Quadlets](podman-rootless.md)
2. [Ansible FQCN Best Practices](ansible-fqcn.md)
3. [Postfix & Dovecot Integration Patterns](postfix-dovecot.md)
4. [S3-Compatible Object Storage Options](s3-storage.md)
5. [Open-Source Webmail Clients Comparison](webmail-clients.md)
6. [Nginx Proxy and Mail Protocol Handling](nginx-proxy.md)
7. [Comprehensive Architectural Blueprint](architectural-blueprint.md)
8. [AI-Assisted Development: Gemini + Jules](ai-dev.md)
9. [GitHub Pages Automation Setup Guide](github-pages-setup.md)

---
*Deep State of Mind (DSOM) For My AI Protocol | Harisfazillah Jamel (LinuxMalaysia) | 2026-07-04*
*Standard: UK English | DBP-standard Bahasa Melayu Malaysia (Piawai) | GNU General Public License v3.0*
