# 🏗️ SongketMail Architectural Blueprint

This document synthesizes our previous deep research topics into a cohesive, production-ready deployment fabric named **SongketMail**. Every design decision is governed by the **Persistence Trinity** strategy, ensuring robust security, horizontal scalability, and storage sovereignty.

---

## 🗺️ System Traffic & Network Flow

```
[ Inbound HTTPS Webmail Traffic ]   [ Inbound SMTP / IMAP Mail Streams ]
               │                                       │
               ▼                                       ▼
    ┌─────────────────────────────────────────────────────────────────────┐
    │                        songketmail-proxy                            │
    │                   (SSL Termination & Hardening)                     │
    └──────────────────────────────────┬──────────────────────────────────┘
                                       │
                         Isolated Cluster Network (songketmail-net)
                                       │
            ┌──────────────────────────┴──────────────────────────┐
            ▼                                                     ▼
┌───────────────────────┐                               ┌───────────────────┐
│   songketmail-web     │                               │songketmail-postfix│
│  (Roundcube Webmail)  │                               │ (Mail Receiver)   │
└───────────┬───────────┘                               └─────────┬─────────┘
            │                                                     │ (LMTP, Port 24)
            ▼                                                     ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                            songketmail-dovecot                            │
│                      (Mail Store & Delivery Agent)                        │
└─────┬───────────────────────────────────────────────────────────────┬─────┘
      │                                                               │
      ▼ (SQL Queries)                                                 ▼ (S3 Protocol)
┌───────────────────────┐                               ┌───────────────────┐
│    songketmail-db     │                               │  songketmail-s3   │
│ (Virtual Accounts Map)│                               │ (Body/Attachments)│
└───────────────────────┘                               └───────────────────┘
```

---

## 🌟 The Persistence Trinity in Action

### 1. Cluster-Prefixed Network & Pod Fabric Isolation
Every running component sits in the unprivileged user namespace pod `songketmail`. Intra-container communications occur inside the virtual network `songketmail-net`. This prevents outside host containers from querying internal Postgres parameters or sniffing raw SMTP/LMTP TCP payloads.

### 2. Native User-Level Systemd Quadlet Orchestration
No docker-compose dependency or custom wrapper scripts. Service lifecycle management is delegated directly to systemd via Podman 5 Quadlets.

Running container services under unprivileged user accounts requires interfacing with systemd's user session daemon. When managing systemd user services via Ansible, tasks must explicitly define environment variables to bind to the rootless user runtime context: `XDG_RUNTIME_DIR` configured to `/run/user/2001` and `DBUS_SESSION_BUS_ADDRESS` configured to `unix:path=/run/user/2001/bus`. To allow background services to run continuously without active SSH sessions, systemd linger must be enabled for the service account via `loginctl enable-linger songket`.

### 3. Node-Isolated Host Storage Sovereignty and Namespace Mapping
Volume mapping points to node-isolated host directories: `/var/srv/songketmail/{{ service }}/data`. Because we declare `UserNS=keep-id:uid=2001,gid=2001` at the Pod level, host-level administrative operations (such as rsync backups and log audits) can be executed cleanly without `sudo`. This maps unprivileged process UIDs to subuid/subgid ranges natively, preventing file ownership from complicating permissions.

---

## 📋 Containerized Service Fabric and Quadlet Configuration Matrix

The `podman-systemd-generator` parses the unprivileged `.container`, `.network`, and `.volume` Quadlet definition files located in `$HOME/.config/containers/systemd/`, automatically producing standard systemd unit services.

| Container Service Name | Quadlet Key Definitions | Mapped Host Storage Paths | Network Ports & Exposure |
|---|---|---|---|
| **songketmail-proxy** | `Image=nginx:alpine`<br>`Network=songketmail-net`<br>`UserNS=keep-id:uid=2001,gid=2001` | `/var/srv/songketmail/nginx/conf:/etc/nginx:Z`<br>`/var/srv/songketmail/certs:/etc/letsencrypt:ro` | Public: 80, 443, 25, 587, 993 |
| **songketmail-postfix** | `Image=postfix:latest`<br>`Network=songketmail-net`<br>`UserNS=keep-id:uid=2001,gid=2001` | `/var/srv/songketmail/postfix/config:/etc/postfix:Z`<br>`/var/srv/songketmail/postfix/spool:/var/spool/postfix:Z` | Internal Fabric: Port 25 |
| **songketmail-dovecot** | `Image=dovecot:latest`<br>`Network=songketmail-net`<br>`UserNS=keep-id:uid=2001,gid=2001` | `/var/srv/songketmail/dovecot/config:/etc/dovecot:Z`<br>`/var/srv/songketmail/dovecot/indexes:/var/vmail/indexes:Z`<br>`/var/srv/songketmail/dovecot/cache:/var/vmail/cache:Z` | Internal Fabric: 24 (LMTP), 143 (IMAP), 4190 (Sieve) |
| **songketmail-db** | `Image=postgres:16-alpine`<br>`Network=songketmail-net`<br>`UserNS=keep-id:uid=2001,gid=2001` | `/var/srv/songketmail/postgres/data:/var/lib/postgresql/data:Z` | Internal Fabric: Port 5432 |
| **songketmail-s3** | `Image=minio/minio:latest`<br>`Network=songketmail-net`<br>`UserNS=keep-id:uid=2001,gid=2001` | `/var/srv/songketmail/minio/data:/data:Z` | Internal Fabric: 9000 (S3 API), 9001 (Console) |
| **songketmail-web** | `Image=roundcube/roundcubemail:latest`<br>`Network=songketmail-net`<br>`UserNS=keep-id:uid=2001,gid=2001` | `/var/srv/songketmail/roundcube/config:/var/www/html/config:Z`<br>`/var/srv/songketmail/roundcube/db:/var/www/html/db:Z` | Internal Fabric: Port 8080 |
| **songketmail-rspamd** | `Image=rspamd/rspamd:latest`<br>`Network=songketmail-net`<br>`UserNS=keep-id:uid=2001,gid=2001` | `/var/srv/songketmail/rspamd/config:/etc/rspamd/local.d:Z`<br>`/var/srv/songketmail/rspamd/data:/var/lib/rspamd:Z` | Internal Fabric: 11333 (Web UI), 11334 (Milter) |

---

## 🗄️ PostgreSQL Virtual Account Schema

Executing the SQL query below inside the PostgreSQL container builds the tables required to authenticate virtual domains, virtual users, and aliases dynamically:

```sql
-- Create domains mapping
CREATE TABLE virtual_domains (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

-- Create users mapping (Argon2id passwords)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    domain_id INT REFERENCES virtual_domains(id) ON DELETE CASCADE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    maildir VARCHAR(255) NOT NULL,
    active BOOLEAN DEFAULT true
);

-- Create aliases mapping
CREATE TABLE virtual_aliases (
    id SERIAL PRIMARY KEY,
    domain_id INT REFERENCES virtual_domains(id) ON DELETE CASCADE,
    source VARCHAR(100) NOT NULL,
    destination VARCHAR(100) NOT NULL
);
```

---

## 🏁 Summary Conclusion

By binding unprivileged Quadlet designs, FQCN-compliant Ansible code, PostgreSQL virtualization, LMTP isolated traffic, MinIO S3 attachments, and Nginx proxying together, **SongketMail** guarantees high-availability email operations with robust host level protection.
