---
okf_version: 0.1
type: agent_skill
title: "RustFS S3 Storage Integration Skill"
name: s3-storage-integration
description: "Teaches AI agents how to configure, deploy, and integrate RustFS S3-compatible storage, including user namespace keep-id mapping and Dovecot Obox/S3 driver tuning."
resource: "file:///.agents/skills/s3-storage-integration/SKILL.md"
timestamp: 2026-08-25T12:00:00Z
topics: [skills, s3, rustfs, storage, dovecot, obox, keep-id]
---

# 🪣 RustFS S3 Storage Integration Skill

This skill teaches Google Antigravity and other AI agents how to deploy and configure RustFS S3-compatible object storage to act as the primary, unprivileged mailbox backend within the SongketMail email fabric.

---

## 🎯 When to use this skill
- Use this skill when modifying S3 storage buckets or configuring object credentials.
- Use this skill when auditing storage performance, Dovecot obox variables, or container permission mapping.

---

## 🚫 Why RustFS (Replacing MinIO)

RustFS is selected as the default storage engine due to critical advantages:
1. **Permissive Apache 2.0 Licensing**: Replaces MinIO's copyleft AGPL-3.0, eliminating intellectual property risks.
2. **Resource Footprint**: Written in Rust, avoiding heavy Go runtime garbage collection pauses and telemetry overhead.
3. **Payload Optimization**: Delivers up to 2.3x higher performance than MinIO for small 4KB mail block payloads.

---

## 🏛️ Storage Sovereignty & Quadlet Configuration

RustFS operates rootless within systemd Quadlets, utilizing explicit User Namespace Keep-ID Mapping:

```ini
[Container]
ContainerName=songketmail-s3
Network=songketmail-net
Image=docker.io/rustfs/rustfs:1.0.0
Volume=/var/srv/songketmail/rustfs/data:/data:Z
Environment=RUSTFS_ACCESS_KEY=rustfs_admin
Environment=RUSTFS_SECRET_KEY=rustfs_secure_pass
UserNS=keep-id:uid=2001,gid=2001
```

By retaining UID/GID `2001:2001`, files stored on the host under `/var/srv/songketmail/rustfs/data` are owned directly by the non-root `songketmail` account.

---

## ⚙️ Dovecot MDA Obox Integration

To connect the mail delivery agent cleanly with S3 object storage, Dovecot separates critical structures:
- **Fast Indexes**: Retained on local NVMe volumes (`/var/srv/songketmail/dovecot/indexes`).
- **Object Bodies**: Transmitted to RustFS via the `obox/s3` driver.

### Core Optimization Parameters
1. **Local Ring Cache (`fscache`)**: local cache at `/var/srv/songketmail/dovecot/cache` prevents redundant read requests.
2. **Data Compression (`compress:zstd:3`)**: Compresses messages before transport.
3. **Dispersion Prefix Hashing (`%8Mu/%u`)**: Applies prefix hashing to objects to distribute S3 I/O evenly across backend disks and prevent index hot-spotting.

---
*Deep State of Mind (DSOM) For My AI Protocol | Harisfazillah Jamel (LinuxMalaysia) | 2026-08-25*
*Standard: UK English | DBP-standard Bahasa Melayu Malaysia (Piawai) | GNU General Public License v3.0*
