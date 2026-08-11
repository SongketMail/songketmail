---
okf_version: 0.1
type: documentation
title: "S3-Compatible Object Storage Options"
description: "Comparing RustFS, MinIO, SeaweedFS, Garage, and Ceph, explaining the transition to RustFS, and integrating Dovecot MDA with S3 object storage."
resource: "file:///docs/s3-storage.md"
timestamp: 2026-08-11T19:00:00Z
topics: [s3, rustfs, minio, seaweedfs, garage, dovecot]
---
# 🪣 S3-Compatible Object Storage Options

Email files historically reside in local maildirs on high-performance SAN or NAS structures. As email body and attachment sizes grow, local hardware limits scalability. Storing mail bodies and attachments in an **S3-compatible object storage cluster** allows IMAP and SMTP servers to remain largely stateless, shifting heavy storage lifting to distributed, highly-redundant storage fabrics.

---

## 📊 Comparing Open-Source S3 Store Solutions

| Software | License | Pros | Cons |
|---|---|---|---|
| **RustFS** | Apache-2.0 | Written in Rust, memory safety by design, 2.3x faster than MinIO for 4KB payloads, zero telemetry/GDPR-compliant, business-friendly permissive license, strong edge/IoT support. | Newer ecosystem compared to long-standing storage platforms; some highly-advanced distributed features are still under testing. |
| **MinIO** | AGPL-3.0 | Extremely popular, rich UI, highly optimized S3 API compatibility. | AGPL-3.0 license is highly restrictive (risk of intellectual property pollution); heavy memory footprint under multi-bucket configurations; telemetry concerns. |
| **SeaweedFS** | Apache-2.0 | Blazing fast small-file storage (via Haystack-like model), low metadata overhead. | Relatively less known; UI dashboard is minimal. |
| **Garage S3** | AGPL-3.0 | Written in Rust, incredibly lightweight, designed for multi-region mesh replication. | AGPL-3.0 license; not suitable for massive multi-petabyte datasets. |
| **Ceph RADOS** | LGPL-2.1 | Enterprise standard, massive scalability, robust high-availability structure. | Huge administrative overhead; requires dedicated disks and intense resource tuning. |

---

## 🚫 Why Not MinIO? Critical Pitfalls of Deploying MinIO

While MinIO has historically been a popular baseline choice for S3-compatible storage, it has several critical downsides that make it unsuitable for modern, security-conscious, enterprise, and cloud-native deployments:

1. **Restrictive AGPL-3.0 Licensing (Copyleft Risk)**: MinIO transitioned to the copyleft AGPL-3.0 license. This license is notoriously restrictive, introducing substantial legal risk for enterprise adoption and SaaS hosting. Integrating or modifying AGPL-licensed software can force organizations into copyleft traps, risking intellectual property pollution and forcing them to publish proprietary backend software.
2. **Heavy Resource and Memory Footprint**: Written in Go, MinIO suffers from significant garbage collection (GC) overhead and high idle memory consumption. When running multiple buckets or under massive sustained loads, these GC pauses cause latency spikes. It is also too bloated for edge devices, gateways, and lightweight IoT deployments.
3. **Telemetry & Sovereignty Risks**: MinIO includes automatic telemetry and licensing calls that communicate with external license servers. This creates potential data sovereignty issues and compliance risks under strict GDPR (Europe/UK), CCPA (US), and APPI (Japan) privacy laws.
4. **Poor Small-Payload Optimization**: For typical email workloads where object payloads are small (typically around 4KB for simple message bodies), Go's runtime overhead and MinIO's heavy stack lead to severe performance inefficiencies compared to native Rust implementations.

---

## 💡 Our Deployed S3 Engine: RustFS

For the SongketMail fabric deployment, we select **RustFS** as our primary S3-compatible object storage engine. RustFS combines the simplicity of MinIO with the performance, memory safety, and raw speed of Rust, fully operating under a permissive **Apache 2.0** license.

### RustFS Storage Sovereignty

By utilizing unprivileged namespaces mapped to UID/GID 2001:2001, RustFS accesses host directories directly under `/var/srv/songketmail/rustfs/data` securely without dynamic permission shifts or root privileges. This prevents any host security exposure while maintaining absolute control over the physical block storage.

---

## 📋 RustFS Declarative Container Quadlet

By launching RustFS inside our unprivileged container fabric, we instantly gain a secure, ultra-high-performance S3 endpoint.

```ini
[Container]
ContainerName=songketmail-s3
Network=songketmail-net
Image=docker.io/rustfs/rustfs:1.0.0
Volume=/var/srv/songketmail/rustfs/data:/data:Z
Environment=RUSTFS_ACCESS_KEY=rustfs_admin
Environment=RUSTFS_SECRET_KEY=rustfs_secure_pass
Environment=RUSTFS_VOLUMES=/data
Environment=RUSTFS_ADDRESS=:9000
Environment=RUSTFS_CONSOLE_ADDRESS=:9001
UserNS=keep-id:uid=2001,gid=2001

[Service]
Restart=always
```

---

## 🏗️ Dovecot MDA to RustFS S3 Object Storage Architecture

Dovecot separates indexing metadata from message payloads. Structural index files (`dovecot.index`) are stored on high-speed host NVMe volumes mounted at `/var/srv/songketmail/dovecot/indexes`. Message bodies and payloads are transmitted directly to the RustFS S3 storage cluster via Dovecot's **obox / s3** plugin drivers.

This storage pipeline integrates three primary performance mechanisms:

1. **Local Filesystem Caching (fscache)**: A local ring-buffer cache (e.g., 512MB) configured on NVMe host storage at `/var/srv/songketmail/dovecot/cache` retains recently accessed message bodies. This reduces S3 API read requests during active IMAP client synchronization.
2. **Data Compression (compress:zstd:3)**: Message bodies are compressed using Zstandard (level 3) before storage in RustFS, reducing network transfer overhead and storage utilization.
3. **Dispersion Prefix Hashing (%8Mu/%u)**: An MD5 hash of the recipient's username is calculated, and the first 8 characters are prepended to the S3 object key path. This dispersion prefix prevents object key grouping, enabling RustFS to distribute object listings and I/O operations evenly across storage disks.

Given that RustFS is **2.3x faster than MinIO** for 4KB payloads, this architecture yields massive latency reductions during heavy client sync loops.

---
*Deep State of Mind (DSOM) For My AI Protocol | Harisfazillah Jamel (LinuxMalaysia) | 2026-08-11*
*Standard: UK English | DBP-standard Bahasa Melayu Malaysia (Piawai) | GNU General Public License v3.0*
