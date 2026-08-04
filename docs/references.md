---
okf_version: 0.1
type: documentation
title: "Project References and Compiled Resources"
description: "A comprehensive compilation of all external resources, URLs, websites, Wikipedia entries, and documents used to build the SongketMail project."
resource: "file:///docs/references.md"
timestamp: 2026-07-04T09:40:04Z
---
# 📚 Project References and Compiled Resources

To ensure the reproducibility, long-term maintainability, and architectural clarity of the **SongketMail** project, this document serves as a centralized compendium of all external resources, official documentation pages, Wikipedia articles, and internal project manuals that informed our design choices and deployment strategies.

---

## 🐋 1. Container Engines & Orchestration

The core of SongketMail's unprivileged service fabric runs on Podman 5+ and is orchestrated natively through user-level systemd Quadlets.

### Podman (Pod Manager)
- **Official Website:** [podman.io](https://podman.io/)
- **Official Documentation:** [docs.podman.io](https://docs.podman.io/)
- **Quadlet Unit Specifications:** [Podman Quadlet Docs](https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html)
- **Wikipedia Reference:** [Podman on Wikipedia](https://en.wikipedia.org/wiki/Podman)
- **Internal Reference:** See [Part 1: Podman Rootless & Quadlets](podman-rootless.md) and [Part 7: Unified Architectural Blueprint](architectural-blueprint.md)

### Systemd (Rootless Services & Lingering)
- **Official Systemd Manual:** [systemd.html](https://www.freedesktop.org/software/systemd/man/latest/systemd.html)
- **Systemd User Session Guide:** [systemd-user](https://www.freedesktop.org/software/systemd/man/latest/systemd-user.html)
- **Lingering Configuration (loginctl):** [loginctl.html](https://www.freedesktop.org/software/systemd/man/latest/loginctl.html)
- **Wikipedia Reference:** [Systemd on Wikipedia](https://en.wikipedia.org/wiki/Systemd)

---

## 🤖 2. Automation Framework

All configuration management, container provisioning, host preparation, and system hardening are written in FQCN-compliant Ansible playbooks.

### Ansible
- **Official Website:** [ansible.com](https://www.ansible.com/)
- **Official Documentation:** [docs.ansible.com](https://docs.ansible.com/)
- **FQCN Compliance Standards:** [Using Collections in Ansible](https://docs.ansible.com/ansible/latest/user_guide/collections_using.html)
- **Wikipedia Reference:** [Ansible on Wikipedia](https://en.wikipedia.org/wiki/Ansible_(software))
- **Internal Reference:** See [Part 2: Ansible Best Practices](ansible-fqcn.md)

---

## ✉️ 3. Mail Servers & Transport Protocols

The inbound and outbound mail flows are split between Postfix (MTA) and Dovecot (MDA), utilizing Local Mail Transport Protocol (LMTP) for interior secure delivery.

### Postfix (Mail Transfer Agent)
- **Official Website:** [postfix.org](https://www.postfix.org/)
- **PostgreSQL Lookup Guide:** [Postfix PGSQL Readme](https://www.postfix.org/PGSQL_README.html)
- **Wikipedia Reference:** [Postfix on Wikipedia](https://en.wikipedia.org/wiki/Postfix_(software))
- **Internal Reference:** See [Part 3: Postfix & Dovecot Integration](postfix-dovecot.md)

### Dovecot (Mail Delivery Agent & IMAP Server)
- **Official Website:** [dovecot.org](https://www.dovecot.org/)
- **Official Documentation:** [doc.dovecot.org](https://doc.dovecot.org/)
- **Obox S3 Storage Plugin:** [Dovecot Obox/S3 Reference](https://doc.dovecot.org/configuration_manual/mailbox_formats/obox/)
- **Wikipedia Reference:** [Dovecot on Wikipedia](https://en.wikipedia.org/wiki/Dovecot_(software))
- **Internal Reference:** See [Part 3: Postfix & Dovecot Integration](postfix-dovecot.md)

---

## 🌐 4. Web Proxy & Protocol Preservation

BunkerWeb is used as the security-hardened reverse proxy layer, handling SSL/TLS termination, acting as a Web Application Firewall (WAF), and reverse proxying HTTP/HTTPS webmail as well as TCP mail streams with PROXY protocol support.

### BunkerWeb
- **Official Website:** [bunkerweb.io](https://www.bunkerweb.io/)
- **Official Documentation:** [docs.bunkerweb.io](https://docs.bunkerweb.io/)
- **BunkerWeb GitHub Repository:** [bunkerity/bunkerweb](https://github.com/bunkerity/bunkerweb)
- **Internal Reference:** See [Part 6: BunkerWeb Proxy Configuration](bunkerweb-proxy.md)

---

## 🛡️ 5. Spam Mitigation & Content Policies

Spam scanning, virus prevention, and policy application are centralized under the high-performance Rspamd engine.

### Rspamd
- **Official Website:** [rspamd.com](https://rspamd.com/)
- **Quick Start Guide:** [Rspamd Quickstart](https://rspamd.com/doc/quickstart.html)
- **Wikipedia Reference:** [Rspamd on Wikipedia](https://en.wikipedia.org/wiki/Rspamd)
- **Internal Reference:** See [Part 7: Unified Architectural Blueprint](architectural-blueprint.md)

---

## 🗄️ 6. Relational Database & Account Virtualization

A virtual database backend allows dynamic mailbox validation, domain registration, and user alias lookups.

### PostgreSQL
- **Official Website:** [postgresql.org](https://www.postgresql.org/)
- **Docker Hub Base Image:** [PostgreSQL Image](https://hub.docker.com/_/postgres)
- **Wikipedia Reference:** [PostgreSQL on Wikipedia](https://en.wikipedia.org/wiki/PostgreSQL)
- **Internal Reference:** See [Part 3: Postfix & Dovecot Integration](postfix-dovecot.md) and [Part 7: Unified Architectural Blueprint](architectural-blueprint.md)

---

## 🪣 7. S3-Compatible Object Storage Engines

We evaluated multiple storage options before adopting MinIO for persistent email body caching and S3 synchronization.

### MinIO S3 (Adopted Engine)
- **Official Website:** [min.io](https://min.io/)
- **Container Documentation:** [MinIO Container Guide](https://min.io/docs/minio/container/index.html)
- **Wikipedia Reference:** [MinIO on Wikipedia](https://en.wikipedia.org/wiki/MinIO)
- **Internal Reference:** See [Part 4: S3 Object Storage Options](s3-storage.md)

### SeaweedFS (Evaluated Option)
- **GitHub Repository:** [seaweedfs/seaweedfs](https://github.com/seaweedfs/seaweedfs)
- **SeaweedFS Wiki:** [SeaweedFS Documentation Wiki](https://github.com/seaweedfs/seaweedfs/wiki)

### Garage S3 (Evaluated Option)
- **Official Website:** [garagehq.oberspace.org](https://garagehq.oberspace.org/)

### Ceph RADOS (Evaluated Option)
- **Official Website:** [ceph.io](https://ceph.io/)
- **Wikipedia Reference:** [Ceph on Wikipedia](https://en.wikipedia.org/wiki/Ceph_(software))

---

## 📧 8. Open-Source Webmail Clients

We evaluated and compared SnappyMail, RainLoop, and Nextcloud Mail, selecting Roundcube as our robust, persistent-state webmail standard.

### Roundcube (Adopted Client)
- **Official Website:** [roundcube.net](https://roundcube.net/)
- **Docker Hub Base Image:** [Roundcube Image](https://hub.docker.com/r/roundcube/roundcubemail)
- **Wikipedia Reference:** [Roundcube on Wikipedia](https://en.wikipedia.org/wiki/Roundcube)
- **Internal Reference:** See [Part 5: Webmail Clients Comparison](webmail-clients.md)

### SnappyMail (Evaluated Option)
- **Official Website:** [snappymail.eu](https://snappymail.eu/)

### RainLoop (Evaluated Option)
- **Official Website:** [rainloop.net](https://www.rainloop.net/)

### Nextcloud Mail (Evaluated Option)
- **Official Website:** [nextcloud.com](https://nextcloud.com/)
- **Wikipedia Reference:** [Nextcloud on Wikipedia](https://en.wikipedia.org/wiki/Nextcloud)

---

## 🛡️ 9. Security Hardening, Compliance & Audits

Host level hardening and configuration auditing are aligned with the ASIMP standard, incorporating industry tools for compliance reporting.

### ASIMP (Ansible System Integrity Management Platform)
- **Methodology Reference:** Master "Measure, Harden, Re-Measure" design standards.
- **Internal Reference:** See [README.md (ASIMP Alignment Section)](../README.md)

### Lynis (Auditing Scanner)
- **Official Website:** [cisofy.com/lynis](https://cisofy.com/lynis/)
- **Wikipedia Reference:** [Lynis on Wikipedia](https://en.wikipedia.org/wiki/Lynis)

### OpenSCAP (Compliance Scanner)
- **Official Website:** [open-scap.org](https://www.open-scap.org/)
- **Wikipedia Reference:** [OpenSCAP on Wikipedia](https://en.wikipedia.org/wiki/OpenSCAP)

### Debsums (Package Integrity Verification)
- **Manpage Reference:** [debsums manual](https://manpages.debian.org/unstable/debsums/debsums.1.en.html)

---

## 📜 10. Documentation Standards & AI Synergy

Static generation and autonomous development workflows are managed through W3C-aligned semantic structures, GitBook, and GitHub Pages.

### Open Knowledge Format (OKF)
- **Concept Definition:** An open standard to solve the "context problem" in AI-driven development.
- **Internal Reference:** See [OKF Adoption Guide](OKF-ADOPTION-GUIDE.md)

### Deep State of Mind (DSOM) AI Protocol
- **Official Repository:** [linuxmalaysia/deep-state-of-mind-for-my-ai](https://github.com/linuxmalaysia/deep-state-of-mind-for-my-ai)
- **Internal Reference:** See [Part 8: AI-Assisted Development](ai-dev.md)

### GitHub Pages & Jekyll (Static Site Publishing)
- **GitHub Pages Website:** [pages.github.com](https://pages.github.com/)
- **Jekyll Website:** [jekyllrb.com](https://jekyllrb.com/)
- **Wikipedia Reference:** [Jekyll on Wikipedia](https://en.wikipedia.org/wiki/Jekyll_(software))
- **Internal Reference:** See [Part 9: GitHub Pages Automation Setup](github-pages-setup.md)

---
*Deep State of Mind (DSOM) For My AI Protocol | Harisfazillah Jamel (LinuxMalaysia) | 2026-07-04*
*Standard: UK English | DBP-standard Bahasa Melayu Malaysia (Piawai) | GNU General Public License v3.0*
