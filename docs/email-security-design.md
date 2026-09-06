---
okf_version: 0.1
type: documentation
title: "Part 25: Email Security from the Wire to the Mailbox, JMAP Protocol & ACME Management"
description: "Architecture specification covering end-to-end transport security (DANE, MTA-STS, TLSRPT), Smallstep ACMEv2 certificate automation, OpenPGP/S/MIME mailbox encryption at rest, JMAP web API integration, Rust memory-safety, and security-focused Ansible playbooks."
resource: "file:///docs/email-security-design.md"
timestamp: 2026-08-19T12:00:00Z
topics: [security, email-security, dane, mta-sts, acmev2, smallstep, openpgp, smime, jmap, rust, ansible]
---

# Part 25: Email Security from the Wire to the Mailbox, JMAP Protocol & ACME Management

## 🔒 1. Executive Summary & Security Philosophy

Security in SongketMail is a core architectural default: **Security is a default, not an add-on**. The platform protects email communication across its entire lifecycle: **from the wire to the mailbox**.

* **Security as Default:** All transports require strict TLS encryption, cryptographic identity verification, and strict authentication policies out-of-the-box.
* **Wire Security:** Mail in transit between servers stays encrypted and verified end-to-end with **DANE**, **MTA-STS**, and **TLS Reporting (TLSRPT)**.
* **Automated Certificate Lifecycle:** TLS certificates renew themselves automatically over **ACMEv2** (RFC 8555) via Let's Encrypt or an internal **Smallstep Certificates (`step-ca`)** Private CA server, preventing outages from certificate expiration.
* **Zero-Trust Mailbox Encryption at Rest:** Mailboxes stored on disk can be encrypted with the user's own **S/MIME certificate** or **OpenPGP key**. Even an operator or adversary with full disk access cannot read mailbox contents without the user's private key.
* **Modern API Access (JMAP):** Replaces legacy IMAP with the **JSON Meta Application Protocol (JMAP / RFC 8620 & RFC 8621)**, offering lightweight, battery-efficient, and secure JSON-over-HTTP web APIs.
* **Memory Safety & Independent Audits:** Core protocol engines leverage **Rust** to prevent memory-corruption vulnerabilities, backed by independent security audits.

---

## 🏗️ 2. End-to-End Email Security Architecture

```text
                                 [ SENDER MTA / CLIENT ]
                                            │
                                            │ ESMTP / TLS 1.3 / DANE / MTA-STS
                                            ▼
                    ┌───────────────────────────────────────────────┐
                    │     BunkerWeb WAF / Reverse Proxy             │
                    │  - ACMEv2 TLS Termination (Let's Encrypt /    │
                    │    Smallstep Private CA)                      │
                    │  - Rate Limiting, ACLs, IP Banning            │
                    └───────────────────────┬───────────────────────┘
                                            │ PROXY Protocol v2
                                            ▼
                    ┌───────────────────────────────────────────────┐
                    │    Postfix MTA (SMTP Ingress / Egress)       │
                    │  - DANE TLSA Validation & MTA-STS Policy      │
                    │  - Automated DKIM Signing (Rspamd Milter)     │
                    └───────────────────────┬───────────────────────┘
                                            │
                                            ▼
                    ┌───────────────────────────────────────────────┐
                    │    Dovecot MDA / Stalwart Engine              │
                    │  - S/MIME or OpenPGP Public Key Encryption    │
                    │  - Encrypted Maildir / Object Storage         │
                    └───────────────────────┬───────────────────────┘
                                            │
                                            ▼
                    ┌───────────────────────────────────────────────┐
                    │    JMAP & IMAP API Server (Port 8443 / 443)   │
                    │  - Rust Memory-Safe Implementation            │
                    │  - Synchronises Email, Calendar & Contacts     │
                    └───────────────────────────────────────────────┘
```

---

## 🌐 3. Strong Transport Security: DANE, MTA-STS & TLS Reporting

### 3.1 DANE (DNS-based Authentication of Named Entities - RFC 6698 / RFC 7672)
DANE leverages **DNSSEC** to publish TLSA records in DNS, binding domain MX servers directly to expected TLS certificates or public keys.
* **Operation:** Postfix validates TLSA records (`3 1 1` or `2 1 1`) when delivering outbound mail.
* **Mitigation:** Completely eliminates Man-in-the-Middle (MitM) attacks and rogue CA certificate issuance.

### 3.2 MTA-STS (SMTP MTA Strict Transport Security - RFC 8461)
MTA-STS enables domain owners to declare that inbound SMTP connections must enforce TLS with valid certificates.
* **Internet-Facing Domains:** Public domains deploy MTA-STS HTTPS policy endpoints (`https://mta-sts.domain.com/.well-known/mta-sts.txt`) backed by publicly trusted Let's Encrypt / ACME certificates.
* **Private / Internal Environments:** Internal enterprise domains (`*.songketmail.internal`) utilize Smallstep Private CA issued certificates for `mta-sts.songketmail.internal`.
* **DNS TXT Record:** `_mta-sts.songketmail.internal. IN TXT "v=STSv1; id=2026081901;"`
* **Policy Endpoint:** Served over HTTPS at `https://mta-sts.songketmail.internal/.well-known/mta-sts.txt`:

  ```ini
  version: STSv1
  mode: enforce
  mx: mail.songketmail.internal
  max_age: 604800
  ```

### 3.3 TLS Reporting (TLSRPT - RFC 8460)
TLSRPT enables daily diagnostic feedback from sending servers regarding TLS handshake failures or MTA-STS policy breaches.
* **DNS TXT Record:** `_smtp._tls.songketmail.internal. IN TXT "v=TLSRPTv1; rua=mailto:tls-rpt@songketmail.internal"`

---

## 🔑 4. Automatic TLS Provisioning via ACMEv2 & Smallstep CA

### 4.1 ACMEv2 Standard (RFC 8555)
ACMEv2 automates certificate issuance, validation, and renewal:
* **HTTP-01 Challenge:** Validates domain ownership via HTTP port 80 token placement.
* **DNS-01 Challenge:** Mandated for **wildcard certificates** (`*.songketmail.internal`) by inserting TXT records into DNS.
* **TLS-ALPN-01 Challenge:** Performs validation directly over TLS port 443 using the ALPN extension without requiring open port 80.

### 4.2 Private Certificate Authority with Smallstep Certificates (`step-ca`)
For enterprise, air-gapped, or internal deployments, SongketMail integrates [Smallstep Certificates](https://github.com/smallstep/certificates) (`smallstep.com/certificates`):
* **Private X.509 & SSH CA:** Provides automated TLS certificate management across internal microservices, Podman Quadlets, and SSH single sign-on (SSO).
* **Embedded ACME Server:** Operates an internal ACME endpoint (`https://ca.songketmail.internal:9000/acme/acme/directory`), enabling seamless auto-renewal for all email services without public internet dependencies.

---

## 🔐 5. Zero-Trust Mailbox Encryption at Rest (OpenPGP & S/MIME)

SongketMail supports server-side automatic encryption before mail is written to persistent disk storage or S3 buckets:
* **Public Key Ingestion:** Users upload their public S/MIME certificate (X.509) or OpenPGP public key via webmail or API.
* **Pre-Storage Encryption:** As incoming messages pass through the MDA (Dovecot / Stalwart milter), the payload is encrypted using the recipient's public key.
* **Operator Isolation:** Mail at rest remains encrypted. Disk storage operators, backup routines, or compromised system administrators cannot decrypt or inspect mailbox contents without the user's private key, which remains under client custody.

---

## ⚡ 6. JSON Meta Application Protocol (JMAP - RFC 8620 & RFC 8621)

JMAP is a modern open standard designed to replace legacy IMAP, SMTP Submission, and CalDAV/CardDAV protocols with fast, lightweight REST/JSON APIs over HTTP/2 and HTTP/3.

### 6.1 How JMAP Works
* **JSON over HTTP:** Synchronises email, calendars, and contacts in single, batched HTTP requests over port 443 / 8443.
* **Event-Driven Push:** Uses Server-Sent Events (SSE) or WebSocket connections for instant push notifications without battery-draining IMAP IDLE polling.

### 6.2 Key Benefits of JMAP
* **Performance & Mobile Efficiency:** Reduces network round-trips by up to 80%, substantially lowering mobile device battery consumption.
* **Unified Data Synchronization:** Synchronises mail, address books, and calendars through a single consistent API structure.
* **Developer Friendly:** Simple REST/JSON data structures replace complex IMAP string commands.
* **Learn More:** Official specifications available at [JMAP.io](https://jmap.io).

---

## 🛡️ 7. Granular ACLs, Rate Limiting, DKIM Automation & Rust Memory Safety

* **Automated DKIM Lifecycle:** Rspamd automatically generates 2048-bit RSA / Ed25519 DKIM keypairs, manages scheduled 90-day key rotations, and exports formatted DNS TXT records.
* **Granular ACLs & IP Banning:** BunkerWeb and Rspamd enforce connection rate limits, greylisting, neural network spam scoring, and dynamic IP banning via `fail2ban` and eBPF packet drop rules.
* **Memory-Safe Implementation in Rust:** Core storage (RustFS), mail engines (Stalwart), and proxy extensions are built in Rust, mathematically eliminating buffer overflows, use-after-free, double-frees, and data races.
* **Independently Security-Audited:** Audited against CIS Benchmarks, NIST SP 800-53, and OWASP Top 10 recommendations.

---

## ⚙️ 8. Ansible Security-by-Default Playbook Mapping

The SongketMail Ansible automation suite enforces security variables by default in `group_vars/all.yml` and Quadlet templates:

| Security Feature | Group Variable / Ansible Task | Target Quadlet Container |
| :--- | :--- | :--- |
| **DANE & DNSSEC Validation** | `enable_dane: true` | `postfix.container` |
| **MTA-STS Enforcement** | `enable_mta_sts: true` | `proxy.container` / `postfix.container` |
| **TLS Reporting (TLSRPT)** | `enable_tls_rpt: true` | `postfix.container` / `rspamd.container` |
| **ACMEv2 Certificate Auto-Renewal** | `enable_acme_v2: true` | `proxy.container` |
| **Smallstep Private CA & SSH SSO** | `smallstep_ca_url: "https://ca..."` | `smallstep.container` |
| **S/MIME / OpenPGP Encryption at Rest**| `enable_openpgp_smime_at_rest: true` | `dovecot.container` |
| **JMAP Protocol API (Port 8443)** | `enable_jmap_protocol: true` | `proxy.container` / `dovecot.container` |
| **DKIM Auto Rotation (90 Days)** | `dkim_rotation_days: 90` | `rspamd.container` |

---

*Deep State of Mind (DSOM) For My AI Protocol | Harisfazillah Jamel (LinuxMalaysia) | 2026-08-19*
*Standard: UK English | DBP-standard Bahasa Melayu Malaysia (Piawai) | GNU General Public License v3.0*
