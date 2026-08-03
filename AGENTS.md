---
okf_version: 0.1
type: agent_guidelines
title: "SongketMail Agent & AI Workspace Reference Manual"
description: "Operational manual, architectural specifications, and compliance rules for Google Jules and other autonomous AI agents."
resource: "file:///AGENTS.md"
timestamp: 2026-07-04T12:00:00Z
---

# 🤖 SongketMail Agent & AI Workspace Reference Manual

Welcome! This document serves as the absolute source of truth for AI agents (including Google Jules and subsequent autonomous entities) operating within the **SongketMail** ecosystem. It compiles critical design philosophies, structural rules, deployment mechanics, and strict repository compliance constraints.

---

## 🧭 Project Architecture Overview

SongketMail is a modern, enterprise-grade, highly secure, and horizontally scalable email server fabric orchestrated via **Ansible** and **Podman 5+** using systemd Quadlets.

The core service fabric is fully decoupled and consists of **seven container services**:
1.  **`proxy`**: Reverse proxy utilizing BunkerWeb All-In-One WAF.
2.  **`postfix`**: MTA (Mail Transfer Agent) for incoming/outgoing SMTP.
3.  **`dovecot`**: IMAP/POP3 storage and access server.
4.  **`db`**: PostgreSQL database storing virtual mail accounts, domains, and aliases.
5.  **`s3`**: MinIO S3 object storage for remote, compressed, and dispersed mailbox storage.
6.  **`web`**: Roundcube webmail client.
7.  **`rspamd`**: Spam filtering, DKIM/DMARC signing, and antivirus scanning service.

These services run within a single rootless systemd Pod (`songketmail_pod`) and communicate on a dedicated bridge network (`songketmail-net`).

---

## 🏛️ The Persistence Trinity Strategy

To achieve high-performance storage isolation and native management, SongketMail adheres strictly to the **Persistence Trinity** design:

1.  **Fabric Isolation (Cluster-Prefixed Networks & Pods)**
    - All Podman objects are cluster-prefixed (e.g., `songketmail_net`, `songketmail_pod`).
    - Multiple parallel mail fabrics can co-exist on the same host with zero conflicts.
2.  **Native Orchestration via User-Level Systemd Quadlets**
    - Services are declared as standard systemd units under:
      `~/.config/containers/systemd/`
    - Start, stop, restart, and monitoring tasks use standard user systemd controls:
      `systemctl --user status songketmail_pod-pod`
3.  **Node-Isolated Host Storage & Sovereignty**
    - Persistent volumes point to host directories under `/var/srv/songketmail`.
    - To avoid high-range host UID translations and preserve native file ownership (allowing easy non-sudo administration, backups, and audits), **User Namespace Keep-ID Mapping** is strictly enforced at the Pod level:
      `UserNS=keep-id:uid=2001,gid=2001`
    - Standard non-privileged user and group mappings correspond to UID/GID `2001:2001` (`songketmail:songketmail`).

---

## 🗄️ Storage Paths & Subdirectories

To ensure storage sovereignty, the fabric structures host persistent storage under `/var/srv/songketmail` using a customized list of **13 specific subdirectories**:

1.  `nginx/conf` - Reverse proxy site configurations.
2.  `certs` - SSL/TLS certificates and keys.
3.  `postfix/config` - Postfix maps, virtual lookup policies, and main configurations.
4.  `postfix/spool` - Active, deferred, and incoming mail queues.
5.  `dovecot/config` - Dovecot configuration overrides, SSL directives, and protocol policies.
6.  `dovecot/indexes` - Fast metadata storage indexes for IMAP/POP operations.
7.  `dovecot/cache` - Local NVMe caching folders.
8.  `postgres/data` - PostgreSQL virtual mailbox maps databases.
9.  `minio/data` - Object blocks storage for MinIO S3 backend.
10. `roundcube/config` - Webmail client plugin and site settings.
11. `roundcube/db` - Local SQLite/metadata tables for Roundcube client sessions.
12. `rspamd/config` - Filter rules, local symbols, and classifier settings.
13. `rspamd/data` - Redis/local database cache for spam neural weights and history.

---

## ⚙️ Host-Level Run & Lingering Configuration

Running rootless container services continuously under unprivileged systemd user sessions requires enabling systemd linger on the host for the service account.
- Enable systemd lingering using:
  `loginctl enable-linger songketmail` (or `loginctl enable-linger songket` depending on the targeted service account name).

---

## 🚀 Ansible Best Practices & Orchestration Rules

When editing, implementing, or running Ansible plays, tasks, and playbooks in this repository, you **must** obey these strict guidelines:

1.  **Fully Qualified Collection Names (FQCN)**:
    - Never use legacy short modules (e.g., `copy`, `template`, `sysctl`).
    - Always use FQCN. For example:
      - `ansible.builtin.copy`
      - `ansible.builtin.template`
      - `ansible.posix.sysctl`
      - `community.general.modprobe`
2.  **Rootless Systemd Execution Context**:
    - When invoking systemd tasks via Ansible for the rootless user, you must explicitly declare the session environment variables:
      {% raw %}
      ```yaml
      environment:
        XDG_RUNTIME_DIR: "/run/user/{{ songketmail_uid }}"
        DBUS_SESSION_BUS_ADDRESS: "unix:path=/run/user/{{ songketmail_uid }}/bus"
      ```
      {% endraw %}

---

## ✉️ Ingress Proxying & Client IP Preservation

The mail server uses a decoupled ingress mechanism:
- **Proxy Configuration**: The ingress proxy utilizes BunkerWeb as the security-hardened reverse proxy layer, terminating SSL/TLS certificates and securing HTTP/HTTPS webmail traffic as well as classic TCP mail streams.
- **Client IP Preservation**: To ensure correct rate-limiting, IP reputation checks, and audit trails across backend Dovecot and Postfix listeners, BunkerWeb transmits the original client IP addresses via **PROXY protocol headers** (`proxy_protocol on;`) on its TCP mail streams.

---

## 📦 S3 Object Storage Integration (Dovecot Obox)

Dovecot manages message storage using advanced S3 object storage capabilities:
- Message bodies are transferred directly to MinIO S3 object storage via the **obox/s3 driver**.
- **Performance Optimizations**:
  - Uses NVMe local filesystem caching (`fscache`).
  - Implements **Zstandard compression** at level 3 (`compress:zstd:3`).
  - Utilizes **dispersion prefix hashing** (`%8Mu/%u`) to prevent S3 bucket hot-spots and maximize I/O throughput distribution.

---

## 📝 Markdown & Jekyll Publishing Guidelines

This repository hosts its static documentation site under the `docs/` directory, automated to deploy to GitHub Pages via `.github/workflows/deploy-pages.yml`.

To prevent build issues and maintain semantic standards, all AI agents **must** adhere to the following:

1.  **Open Knowledge Format (OKF) Compliance**:
    - Every Markdown (`.md`) file in the repository must adopt the Google-inspired **Open Knowledge Format (OKF) v0.1** by including structured YAML frontmatter at the beginning of the file.
    - Required fields:
      - `okf_version: 0.1`
      - `type`
      - `title`
      - `description`
      - `resource`
      - `timestamp`
2.  **Jekyll Template Escaping**:
    - Jekyll builds require wrapping any code blocks containing Jinja2-style braces (such as `{ { ... } }` or `{ % ... % }` commonly used in Ansible templates) inside `{ % raw % }` and `{ % endraw % }` Liquid template tags. Failure to do so will cause Jekyll parsing exceptions on the `gh-pages` branch.
3.  **GitHub Pages Setup**:
    - The repository uses a `gh-pages` branch configured with Jekyll using `_config.yml`, `Gemfile`, and `.nojekyll` files at both the root level and the `docs/` level to ensure correct static site hosting.
4.  **Ignore Jekyll Artifacts**:
    - The root-level `.gitignore` must ignore Jekyll build artifacts (`_site/`, `.sass-cache/`, `.jekyll-cache/`, `.jekyll-metadata`) and Ruby bundler environments (`vendor/`, `.bundle/`).
5.  **Documentation Indexing**:
    - All architectural decisions, guides, and specifications must be stored as parallel Markdown (`.md`) files under the `docs/` directory (covering Podman rootless, Ansible best practices, Postfix/Dovecot, S3 object storage, webmail comparisons, Nginx, and architectural blueprints) fully optimized for GitBook rendering.
    - Keep a centralized resource index (`docs/references.md` and `docs/references.html` as Part 10 of the documentation book) compiling external URLs, official documentation sites, and Wikipedia entries.

---

*Deep State of Mind (DSOM) For My AI Protocol | Harisfazillah Jamel (LinuxMalaysia) | 2026-07-04*
*Standard: UK English | DBP-standard Bahasa Melayu Malaysia (Piawai) | GNU General Public License v3.0*
