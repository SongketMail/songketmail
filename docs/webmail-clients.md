---
okf_version: 0.1
type: documentation
title: "Open-Source Webmail Clients Comparison"
description: "Evaluating containerized webmail clients (Roundcube, SnappyMail, RainLoop, Nextcloud) for persistence, security, and performance."
resource: "file:///docs/webmail-clients.md"
timestamp: 2026-07-04T09:40:04Z
---
# 📧 Open-Source Webmail Clients Comparison

Selecting a containerized webmail client requires careful assessment of scalability, state persistence, security, and performance. Traditional webmail (like Roundcube) requires dedicated MySQL/PostgreSQL databases to hold session and cache states. Modern webmail engines act as stateless client-side rendering portals, connecting directly to IMAP/SMTP backends on demand.

---

## 📊 Webmail Comparison Matrix

| Client | Architecture | Database Req. | Security / 2FA | Performance |
|---|---|---|---|---|
| **Roundcube** | Server-Side PHP (GPL-3.0+) | **Yes (SQL)** | Supported via Plugins | Moderate (heavy server load) |
| **SnappyMail** | SPA / Client-Side (AGPL-3.0) | **No (Stateless)** | Native 2FA / Hardened | Incredibly Fast / Low memory |
| **RainLoop** | Legacy SPA (CC BY-NC-SA 3.0) | **No** | Outdated dependencies | Moderate (unmaintained) |
| **Nextcloud Mail** | Heavy Suite App (AGPL-3.0) | **Yes** | Native via Nextcloud Suite | Very heavy (resource intense) |

---

## ⚡ Chosen Baseline: Roundcube Webmail

**Roundcube** is the chosen, production-ready webmail client deployed in the SongketMail configuration matrix. It offers classic, fully-featured, and highly intuitive desktop and mobile web interfaces with extensive plugin ecosystems.

- **State Persistence Architecture**: Unlike stateless clients like SnappyMail, Roundcube utilizes an internal SQLite/Postgres database to persistently store user session caches, active address books, and interface customization settings. This ensures absolute stability and standard-compliant mail interactions.
- **Secure Host Persistence**: All configuration variables and sqlite database files are mapped directly under `/var/srv/songketmail/roundcube/config` and `/var/srv/songketmail/roundcube/db` respectively, maintaining storage sovereignty via keep-id.
- **Internal Port Binding**: Roundcube runs on unprivileged internal port `8080` inside the secure `songketmail-net` network, accepting requests exclusively from the hardened Nginx proxy.

---

## 📋 Roundcube Container Quadlet

By running Roundcube in our unprivileged systemd Quadlet mesh, it connects to Dovecot and Postgres inside the secure cluster network.

```ini
[Container]
ContainerName=songketmail-web
Network=songketmail-net
Image=roundcube/roundcubemail:latest
Volume=/var/srv/songketmail/roundcube/config:/var/www/html/config:Z
Volume=/var/srv/songketmail/roundcube/db:/var/www/html/db:Z
UserNS=keep-id:uid=2001,gid=2001

[Service]
Restart=always
```
