---
okf_version: 0.1
type: agent_skill
title: "SongketMail Architecture Skill"
name: songketmail-architecture
description: "Teaches AI agents the architectural rules, the Persistence Trinity, and the keep-id mapping requirements for SongketMail."
resource: "file:///.agents/skills/songketmail-architecture/SKILL.md"
timestamp: 2026-07-04T12:00:00Z
---

# 🏗️ SongketMail Architecture Skill

This skill teaches Google Antigravity and other AI agents the core architectural guidelines of the SongketMail persistence system, container services, and storage mappings.

## 🎯 When to use this skill
- Use this skill when designing, auditing, modifying, or troubleshooting the SongketMail service stack.
- This is helpful when validating volume storage structures, service namespaces, and permission models.

## 🛠️ The SongketMail Container Services
SongketMail is composed of seven fully decoupled, highly secure container services communicating over a dedicated user-level network bridge (`songketmail-net`):
1.  **`proxy`**: Reverse proxy utilizing BunkerWeb All-In-One WAF (stream and HTTP).
2.  **`postfix`**: Mail Transfer Agent (MTA) handling SMTP relaying.
3.  **`dovecot`**: Mail Delivery Agent (MDA) managing IMAP, POP3, and mailbox structures.
4.  **`db`**: PostgreSQL database for virtual accounts, domains, and alias maps.
5.  **`s3`**: MinIO S3 object storage for remote, compressed, and dispersed mailbox objects.
6.  **`web`**: Roundcube webmail client.
7.  **`rspamd`**: Spam filtering, DKIM/DMARC signing, and antivirus checks.

## 🏛️ The Persistence Trinity Strategy
AI agents must align every design decision with the Persistence Trinity:

1.  **Fabric Isolation (Cluster-Prefixed Networks & Pods)**
    - All Podman network, pod, and container objects must utilize the configured prefix (e.g., `songketmail_net`, `songketmail_pod`).
    - Multiple parallel mail server fabrics must be able to co-exist on a single host with zero port or namespace conflicts.
2.  **Native Orchestration via User-Level Systemd Quadlets**
    - High-level orchestrations must utilize systemd Quadlets rather than docker-compose or ad-hoc scripts.
    - Quadlet configurations (.container, .pod, .network) are placed under the user's home directory (`~/.config/containers/systemd/`).
3.  **Node-Isolated Host Storage & Sovereignty**
    - All persistent volumes point to host directories under `/var/srv/songketmail` or a parameterized storage root.
    - **User Namespace Keep-ID Mapping** is strictly enforced at the Pod level:
      ```ini
      UserNS=keep-id:uid=2001,gid=2001
      ```
    - This maps the unprivileged user/group UID/GID `2001:2001` (`songketmail`) natively inside and outside the container. Storage Sovereignty ensures files are owned directly by the `songketmail` host user with no root/sudo privileges required for backups, auditing, or management.

## 🗄️ Storage Paths & Subdirectories
The fabric enforces a strict host-level directory schema under `/var/srv/songketmail`. There are 13 specific folders that must be provisioned with `0700` permissions and owned by the `songketmail` user (UID/GID 2001):
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
*Deep State of Mind (DSOM) For My AI Protocol | Harisfazillah Jamel (LinuxMalaysia) | 2026-07-04*
*Standard: UK English | DBP-standard Bahasa Melayu Malaysia (Piawai) | GNU General Public License v3.0*
