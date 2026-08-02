---
okf_version: 0.1
type: documentation
title: "S3-Compatible Object Storage Options"
description: "Comparing MinIO, SeaweedFS, Garage, and Ceph, and integrating Dovecot MDA with S3 object storage."
resource: "file:///docs/s3-storage.md"
timestamp: 2026-07-04T09:40:04Z
---
# 🪣 S3-Compatible Object Storage Options

Email files historically reside in local maildirs on high-performance SAN or NAS structures. As email body and attachment sizes grow, local hardware limits scalability. Storing mail bodies and attachments in an **S3-compatible object storage cluster** allows IMAP and SMTP servers to remain largely stateless, shifting heavy storage lifting to distributed, highly-redundant storage fabrics.

---

## 📊 Comparing Open-Source S3 Store Solutions

| Software | License | Pros | Cons |
|---|---|---|---|
| **MinIO** | AGPL-3.0 | Extremely popular, rich UI, highly optimized S3 API compatibility. | AGPL license is highly restrictive; heavy memory footprint on multiple buckets. |
| **SeaweedFS** | Apache-2.0 | Blazing fast small-file storage (via Haystack-like model), low metadata overhead. | Relatively less known; UI dashboard is minimal. |
| **Garage S3** | AGPL-3.0 | Written in Rust, incredibly lightweight, designed for multi-region mesh replication. | Not suitable for multi-petabyte datasets. |
| **Ceph RADOS** | LGPL-2.1 | Enterprise standard, massive scalability, robust high-availability structure. | Huge administrative overhead; requires dedicated disks and intense resource tuning. |

---

## 💡 Our Deployed S3 Engine: MinIO

For this SongketMail fabric baseline, we deploy **MinIO** as our primary S3-compatible object storage server. This provides a highly standardized, performant, and reliable storage backend with a complete administrative Console interface.

### MinIO Storage Sovereignty

By utilizing unprivileged namespaces mapped to UID/GID 2001:2001, MinIO accesses host directories directly under `/var/srv/songketmail/minio/data` securely without dynamic permission shifts or root privileges.

---

## 📋 MinIO Declarative Container Quadlet

By launching a standard MinIO server inside our unprivileged container fabric, we instantly gain a high-performance S3 endpoint.

```ini
[Container]
ContainerName=songketmail-s3
Network=songketmail-net
Image=minio/minio:latest
Volume=/var/srv/songketmail/minio/data:/data:Z
Exec=server /data --console-address ":9001"
UserNS=keep-id:uid=2001,gid=2001

[Service]
Restart=always
```

---

## 🏗️ Dovecot MDA to MinIO S3 Object Storage Architecture

Dovecot separates indexing metadata from message payloads. Structural index files (`dovecot.index`) are stored on high-speed host NVMe volumes mounted at `/var/srv/songketmail/dovecot/indexes`. Message bodies are transmitted to MinIO S3 object storage via Dovecot's **obox / s3** plugin drivers.

This storage pipeline integrates three primary performance mechanisms:

1. **Local Filesystem Caching (fscache)**: A local ring-buffer cache (e.g., 512MB) configured on NVMe host storage at `/var/srv/songketmail/dovecot/cache` retains recently accessed message bodies. This reduces S3 API read requests during active IMAP client synchronization.
2. **Data Compression (compress:zstd:3)**: Message bodies are compressed using Zstandard (level 3) before storage in MinIO, reducing network transfer overhead and storage utilization.
3. **Dispersion Prefix Hashing (%8Mu/%u)**: An MD5 hash of the recipient's username is calculated, and the first 8 characters are prepended to the S3 object key path. This dispersion prefix prevents object key grouping, enabling MinIO to distribute object listings and I/O operations evenly across storage disks.
