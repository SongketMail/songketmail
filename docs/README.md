# SongketMail Documentation Book

An enterprise-grade, highly secure, and horizontally scalable email server baseline orchestrated using **Ansible** and **Podman 5+**. This project acts as the architectural blueprint and operational baseline for deploying persistent, secure, and performant rootless email services.

---

## 🛰️ Distributed Node Strategy

To support production-level horizontal scaling, high availability, and localized file execution, the fabric enforces the **Persistence Trinity**:

### 1. Quadlet Orchestration
Instead of legacy docker-compose or ad-hoc run scripts, this baseline utilizes **Podman Quadlets** for native, user-level systemd integration. This ensures:
- Containers automatically recover and start following host/node reboots.
- Services are managed natively via standard systemd tooling (`systemctl --user`).
- Clean separation of concern with declarative `.container`, `.pod`, and `.network` configuration files.

### 2. Node-Isolated Storage & Sovereignty
To maximize host I/O throughput and maintain clear storage structures, volume mounts point to node-isolated paths under:
```
/opt/songketmail/{{ service_name }}/{{ inventory_hostname }}/data
```
For example, the SMTP/IMAP data for `node1.songketmail.internal` maps exactly to `/opt/songketmail/emailserver/node1.songketmail.internal/data`.

### 3. Fabric Isolation
All pods, networks, and container names are cluster-prefixed (e.g., `skm_fabric_net`, `skm_fabric_pod`). This ensures that multiple distinct persistence fabrics can co-exist on a single Jump-Host or hypervisor without port or network conflicts.

---

## 🗂️ Book Structure

This documentation book is structured into several progressive parts:

* **[Part 1: Podman Rootless & Quadlets](podman-rootless.md)**: Deep dive on keep-id mapping (UID/GID 2001:2001) and systemd lingering setup.
* **[Part 2: Ansible Best Practices](ansible-fqcn.md)**: Comprehensive guide on Fully Qualified Collection Names (FQCN) compliance and systemd execution contexts.
* **[Part 3: Postfix & Dovecot Integration](postfix-dovecot.md)**: Details on Local Mail Transport Protocol (LMTP) delivery patterns over isolated networks.
* **[Part 4: S3 Object Storage Options](s3-storage.md)**: Comparing S3 engines (MinIO, SeaweedFS, Ceph) and configuring fscache with compression.
* **[Part 5: Webmail Clients Comparison](webmail-clients.md)**: Evaluation matrix between Roundcube, SnappyMail, RainLoop, and Nextcloud.
* **[Part 6: Nginx Proxy Configuration](nginx-proxy.md)**: Reverse proxying, HTTP mail authentication protocols, and client IP preservation.
* **[Part 7: Unified Architectural Blueprint](architectural-blueprint.md)**: Master block diagrams, container matrix, and PostgreSQL schemas.
* **[Part 8: AI-Assisted Development](ai-dev.md)**: Workflow practices with Google Gemini and Jules developer synergy.
* **[Part 9: GitHub Pages Automation Setup](github-pages-setup.md)**: Walkthrough of setup procedures and automated Actions deployment workflows.
