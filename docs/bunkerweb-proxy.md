---
okf_version: 0.1
type: documentation
title: "BunkerWeb Proxy and Mail Protocol Handling"
description: "Terminating SSL/TLS certificates and reverse proxying HTTP webmail and TCP mail protocols with client IP preservation using BunkerWeb."
resource: "file:///docs/bunkerweb-proxy.md"
timestamp: 2026-07-04T09:40:04Z
---
# 🛡️ BunkerWeb Proxy and Mail Protocol Handling

BunkerWeb is a security-hardened, next-generation Web Application Firewall (WAF) and reverse proxy built on top of Nginx. In the **SongketMail** fabric, we utilize the all-in-one BunkerWeb container as our primary ingress proxy layer, replacing raw Nginx. This layer terminates SSL/TLS certificates and secures **HTTP/HTTPS webmail traffic** as well as classic TCP mail streams (**SMTP, SMTP Submission, and IMAPS**).

Using BunkerWeb centralizes certificate management, automatically mitigates web application attacks (e.g. SQL Injection, XSS), and provides a hardened entry point.

---

## 🔒 HTTPS Webmail Reverse Proxy

BunkerWeb serves as the reverse proxy for our Roundcube webmail instance (`songketmail-web`). It handles SSL termination and injects hardened security headers (e.g. HSTS, X-Frame-Options, X-Content-Type-Options) automatically, routing unencrypted internal HTTP traffic to the backend containers inside `songketmail-net`.

Below is the declarative Quadlet configuration block mapping the HTTP/HTTPS ingress webmail traffic to the backend:

```ini
# Webmail (HTTP/HTTPS) Ingress configuration
Environment=mail.songketmail.internal_USE_REVERSE_PROXY=yes
Environment=mail.songketmail.internal_REVERSE_PROXY_HOST=http://songketmail-web:8080
Environment=mail.songketmail.internal_REVERSE_PROXY_URL=/
```

---

## ✉️ TCP Mail Stream Proxying with PROXY Protocol

BunkerWeb supports stream-level reverse proxying for generic TCP/UDP applications using the Nginx `stream` module. In SongketMail, we leverage this capability to proxy inbound SMTP and IMAP mail streams.

By default, proxying raw TCP streams replaces the client's public IP address with the proxy's internal container IP, which disables backend rate-limiting, IP reputation checks, and fail2ban security mechanisms. To resolve this, we configure `proxy_protocol on;` on the BunkerWeb server blocks and enable PROXY protocol parsing on the backend Postfix and Dovecot listeners. This forwards a PROXY header containing the original client IP and port information to backend services before protocol handshakes initiate.

The stream configuration is defined declaratively inside the BunkerWeb container:

```ini
# SMTP Stream (Port 25)
Environment=smtp.songketmail.internal_SERVER_TYPE=stream
Environment=smtp.songketmail.internal_USE_REVERSE_PROXY=yes
Environment=smtp.songketmail.internal_REVERSE_PROXY_HOST=songketmail-postfix:25
Environment=smtp.songketmail.internal_LISTEN_STREAM_PORT=25
# Enforce PROXY protocol on SMTP connections to backend Postfix to preserve client IP
Environment=smtp.songketmail.internal_CUSTOM_CONF_SERVER_STREAM_proxy-protocol=proxy_protocol on;

# SMTP Submission Stream (Port 587)
Environment=smtp.songketmail.internal_LISTEN_STREAM_PORT_1=587
Environment=smtp.songketmail.internal_REVERSE_PROXY_HOST_1=songketmail-postfix:587
Environment=smtp.songketmail.internal_CUSTOM_CONF_SERVER_STREAM_proxy-protocol_1=proxy_protocol on;

# IMAP Stream (Port 143/993)
Environment=imap.songketmail.internal_SERVER_TYPE=stream
Environment=imap.songketmail.internal_USE_REVERSE_PROXY=yes
Environment=imap.songketmail.internal_REVERSE_PROXY_HOST=songketmail-dovecot:993
Environment=imap.songketmail.internal_LISTEN_STREAM_PORT_SSL=993
# Enforce PROXY protocol on IMAP connections to backend Dovecot
Environment=imap.songketmail.internal_CUSTOM_CONF_SERVER_STREAM_proxy-protocol=proxy_protocol on;
```

---

## 🛡️ How Client IP Preservation Works

When a client initiates a connection to the mail stream, BunkerWeb accepts it and prepends a PROXY protocol header to the upstream TCP connection:

```
PROXY TCP4 203.0.113.50 10.89.1.1 43212 25
```

This preserves the client's public IP address (`203.0.113.50`) inside Postfix and Dovecot's logs, enabling fail2ban and audit routines natively on the backend, while keeping the security-hardened BunkerWeb front-end as the sole exposed gatekeeper.

---
*Deep State of Mind (DSOM) For My AI Protocol | Harisfazillah Jamel (LinuxMalaysia) | 2026-07-04*
*Standard: UK English | DBP-standard Bahasa Melayu Malaysia (Piawai) | GNU General Public License v3.0*
