---
okf_version: 0.1
type: documentation
title: "Postfix & Dovecot Integration Patterns"
description: "Inbound email routing, Local Mail Transport Protocol (LMTP) delivery patterns, and PostgreSQL virtual mailbox queries."
resource: "file:///docs/postfix-dovecot.md"
timestamp: 2026-07-04T09:40:04Z
---
# ✉️ Postfix & Dovecot Integration Patterns

Inbound email received from external servers on port 25 passes through Postfix for recipient validation and Rspamd policy filtering. Once validated, Postfix delivers messages to Dovecot using Local Mail Transport Protocol (LMTP) on internal port 24. LMTP provides transaction verification, confirming that messages are committed to storage before acknowledging receipt to the sending MTA.

By decoupling Postfix and Dovecot, LMTP operates over an isolated, cluster-prefixed container network (`songketmail-net`), preventing other containers or outside actors from intercepting internal mail routing.

---

## 🗄️ PostgreSQL Virtual User Virtualization

Postfix validates domains, mailboxes, and aliases by querying PostgreSQL using native SQL lookup tables (`virtual_mailbox_domains`, `virtual_mailbox_maps`, and `virtual_alias_maps` mapped to `virtual_aliases` table). This allows administrators to scale mailboxes horizontally without altering local host user groups.

### 1. Postfix PGSQL Configuration: `pgsql-virtual-mailbox-maps.cf`
```ini
hosts = songketmail-db.songketmail-net
user = mail_admin
password = super_secure_db_pass
dbname = mailserver
query = SELECT maildir FROM users WHERE email='%s' AND active=true
```

### 2. Postfix Configuration Hooks: `main.cf`
```ini
# Enable Virtual Domain Handlers
virtual_mailbox_domains = pgsql:/etc/postfix/pgsql-virtual-domains-maps.cf
virtual_mailbox_maps = pgsql:/etc/postfix/pgsql-virtual-mailbox-maps.cf
virtual_alias_maps = pgsql:/etc/postfix/pgsql-virtual-alias-maps.cf

# Delegate Delivery to Dovecot LMTP Container
virtual_transport = lmtp:inet:songketmail-dovecot.songketmail-net:24
```

---

## 🔒 Dovecot Database Authentication & LMTP

Dovecot acts as the mail delivery terminal, validating IMAP connections directly against PostgreSQL hashes and listening on port `24` for inbound LMTP flows.

### 1. `dovecot-sql.conf.ext`
```ini
driver = pgsql
connect = host=songketmail-db.songketmail-net dbname=mailserver user=mail_admin password=super_secure_db_pass
default_pass_scheme = ARGON2ID
password_query = SELECT password FROM users WHERE email='%u' AND active=true
user_query = SELECT '/var/vmail/indexes/'||maildir AS home, 2001 AS uid, 2001 AS gid FROM users WHERE email='%u'
```

### 2. `dovecot.conf` (LMTP Service Listener)
```ini
protocols = imap lmtp

service lmtp {
  inet_listener lmtp {
    address = *
    port = 24
  }
}

protocol lmtp {
  postmaster_address = postmaster@songketmail.internal
  mail_plugins = $mail_plugins sieve
}
```

---

## 🛡️ Fabric Isolation Advantage

Because Postfix and Dovecot talk over the isolated `songketmail-net`, LMTP and DB socket traffic never gets exposed to host ports (such as host ports 80, 443, etc.). The database server (PostgreSQL) is placed deep within the network fabric and only responds to verified interior container IPs, maintaining complete defense-in-depth security.

---
*Deep State of Mind (DSOM) For My AI Protocol | Harisfazillah Jamel (LinuxMalaysia) | 2026-07-04*
*Standard: UK English | DBP-standard Bahasa Melayu Malaysia (Piawai) | GNU General Public License v3.0*
