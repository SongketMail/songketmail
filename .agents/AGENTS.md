---
okf_version: 0.1
type: agent_guidelines
title: "SongketMail Agent & AI Workspace Reference Manual"
description: "Operational manual, architectural specifications, and compliance rules for Google Jules and other autonomous AI agents."
resource: "file:///AGENTS.md"
timestamp: 2026-07-25T12:00:00Z
topics: [agents, reference-manual, compliance, workspace]
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
5.  **`s3`**: RustFS S3-compatible object storage for remote, compressed, and dispersed mailbox storage.
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
9.  `rustfs/data` - Object blocks storage for RustFS S3 backend.
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
- Message bodies are transferred directly to RustFS S3 object storage via the **obox/s3 driver**.
- **Performance Optimizations**:
  - Uses NVMe local filesystem caching (`fscache`).
  - Implements **Zstandard compression** at level 3 (`compress:zstd:3`).
  - Utilizes **dispersion prefix hashing** (`%8Mu/%u`) to prevent S3 bucket hot-spots and maximize I/O throughput distribution.

---

## 📝 Markdown & Jekyll Publishing Guidelines

This repository hosts its static documentation site under the `docs/` directory, automated to deploy to GitHub Pages via `.github/workflows/deploy-pages.yml`.

To prevent build issues and maintain semantic standards, all AI agents **must** adhere to the following:

1.  **Open Knowledge Format (OKF) Compliance**:
    - Every Markdown (`.md`) file in the repository must adopt the Google-inspired **Open Knowledge Format (OKF) v0.1** by including structured YAML frontmatter at the beginning of the file, bridging human-readable and agent-consumable knowledge management.
    - Required fields:
      - `okf_version: 0.1` (Specifies the OKF version targeted, e.g., "0.1")
      - `type` (The concept type for classification/routing, e.g., "documentation", "agent_skill", "research", "planning")
      - `title` (A clear, human-readable display name for the document)
      - `timestamp` (An ISO 8601 representation of the generation or last modification time)
      - `topics` (A list of tags or categorized words, e.g., `[email, architecture, security]`)
    - Recommended/Optional fields:
      - `description` (A single sentence summarizing the document's content)
      - `resource` (A URI linking to the physical asset described, e.g., `file:///docs/index.md`)
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

## 🔍 Local Knowledge-First & Metadata Discovery Mandate (Rule 29)

To prevent unnecessary exploratory terminal commands, token window exhaustion, and context loss, the AI agent MUST strictly adhere to the Local Knowledge-First Protocol:
1.  **Search Local First**: BEFORE executing terminal commands, probing live server nodes (`node1.songketmail.internal`, `node2.songketmail.internal`), running playbooks, or performing Google searches, the AI agent MUST first search local project knowledge in `.agents/brain/` and `docs/` (using tools like `grep`, `find`, or `read_file` on OKF frontmatter `topics:`/`description:` tags).
2.  **Retrieve Targeted Context**: Use targeted file reading to inspect relevant documents and preserve context window efficiency.
3.  **Remote Server Gate**: Remote execution or terminal queries are strictly reserved for applying planned changes or fetching live, undocumented runtime state.

---

## ⏳ Temporal Knowledge Verification Mandate (Rule 30)

AI agents must verify the freshness of local knowledge:
1.  **Check OKF Timestamps**: Inspect the `timestamp` field in OKF YAML frontmatter.
2.  **Outdated Knowledge Gate**: If the local documentation appears contextually outdated, research external standards and present a comparison of local knowledge vs. new findings to the human operator.
3.  **Explicit Verification**: Do not proceed with execution until the human operator has explicitly verified whether to update local documents or ignore findings.

---

## 🧪 Unprivileged Sandbox & Google Jules Environment Limitations (Rule 31)

To ensure that the **SongketMail** deployment fabric remains highly adaptable across unprivileged developer sandboxes (like Google Jules or other container-isolated testing environments) and production-grade bare-metal/VM instances, all automation code must respect the boundaries of restricted environments.

### 1. Google Jules / Sandbox Constraints
AI agents operating inside secure, unprivileged sandboxes encounter the following severe system constraints:
- **No Privilege Escalation**: No root/sudo access. Any task requesting `become: yes` without fallback parameters will immediately crash or fail.
- **Immutable Host Configurations**: Restricting `/proc/`, `/sys/`, `/etc/`, and system-wide configurations. Modifying kernel parameters via `sysctl` or loading kernel modules via `modprobe` is prohibited.
- **Disabled Package Managers**: Incapable of installing host OS packages (e.g. `apt`, `yum`) because package operations require root privileges.
- **Inaccessible Host Service Controllers**: Modifying host systemd services, restarting systemd managers, or enabling persistent systemd lingering (`loginctl enable-linger`) is restricted.

### 2. Dual-Environment Engineering Options
All Ansible codebases and deployment scripts must implement the **`is_limited_environment`** variable (defined in `group_vars/all.yml` and defaulting to `false`):

- **Option A: Real OS Deployment (`is_limited_environment: false`)**
  - Runs with zero limitations.
  - Full root privilege escalation is allowed (`become: yes`).
  - Executes host-level hardening, package installations, kernel tuning, subuid mapping, and full ASIMP compliance auditing.
- **Option B: Limited Sandbox Deployment (`is_limited_environment: true`)**
  - Fully unprivileged execution (disables privilege escalation dynamically).
  - Skips kernel adjustments, modprobes, system user/group creations, subuid/subgid line edits, and packages installations.
  - Safely overrides and redirects persistent storage directories to writable locations inside the unprivileged user's home directory (e.g. `~/var/srv/songketmail`).
  - Bypasses systemd user session manager actions (as systemd is generally absent or restricted in unprivileged sandboxes).

All newly-authored or edited Ansible playbooks, roles, and tasks must strictly query `not (is_limited_environment | default(false) | bool)` before running any privileged/system-level operations.

### 3. Dynamic Privilege Level Detection (`asimp_privilege_level`)
To ensure complete robustness across diverse systems, the setup utilizes dynamic privilege level detection:
- **`limited_sandbox`**: Used for limited sandbox/ordinary user environments. In this mode, system-altering remediation tasks are bypassed. Instead, the pipeline runs real-time audits and scans using OpenSCAP and Lynis where available (or falling back to baseline simulation scores if completely restricted).
- **`full_privilege`**: Used for full-privilege bare-metal or VM systems. On these environments, a mandatory **Pre-Remediation Safety Check & Break-Prevention Verification** block is executed BEFORE applying any modifications to ensure no active conflicts or lockouts occur.

### 4. ASIMP Security Hardening & Project Compatibility
The Ansible System Integrity Management Platform (ASIMP) serves as the **major player** for security hardening within the SongketMail deployment flow.
- **Architectural Harmony**: ASIMP measures, hardens, and re-measures host security. SongketMail coordinates its decentralized, rootless container deployment directly on top of the hardened host fabric.
- **Compatibility Patcher**: Because modern Ansible core (2.16+) and unprivileged container sandboxes introduce syntax and operational constraints (e.g. service/systemd modules require systemd as PID 1, and failed_when on block elements is deprecated), our pipeline applies dynamic compatibility patchers on the fly. This ensures ASIMP remains the primary authority for host security enforcement, keeping the project codes and flow fully compatible, without disrupting rootless container networking, storage sovereignty, or remote SSH access controls.

---

*Deep State of Mind (DSOM) For My AI Protocol | Harisfazillah Jamel (LinuxMalaysia) | 2026-07-25*
*Standard: UK English | DBP-standard Bahasa Melayu Malaysia (Piawai) | GNU General Public License v3.0*
