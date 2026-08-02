# 🌐 Nginx Proxy and Mail Protocol Handling

Nginx is globally recognized for its HTTP reverse proxying capabilities, but it also contains a native **mail proxy module**. This allows a single unprivileged Nginx container to terminate SSL/TLS certificates and securely proxy **HTTP/HTTPS webmail** as well as classic TCP mail protocols (**IMAP, IMAPS, SMTP, SMTPS**). This minimizes attack surfaces and centralizes certificate rotation (e.g., Let's Encrypt).

---

## 🔒 HTTPS Webmail Reverse Proxy

The block below represents the traditional `http {}` reverse proxy configuring SSL termination and security headers for Roundcube, routing unencrypted internal TCP streams to backend containers inside `songketmail-net`.

```nginx
http {
    # Hardened Security Protocol Settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384';

    server {
        listen 443 ssl http2;
        server_name mail.songketmail.internal;

        ssl_certificate /etc/letsencrypt/live/songketmail/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/songketmail/privkey.pem;

        # Hardening Headers
        add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;

        location / {
            proxy_pass http://songketmail-web:8080;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto https;
        }
    }
}
```

---

## ✉️ The Native Nginx mail {} Block with PROXY Protocol

Nginx uses a separate `mail {}` configuration block to proxy IMAP, POP3, and SMTP traffic. Because Nginx doesn't read password databases directly, it uses an internal **HTTP Authentication Service** to validate the credentials before routing TCP connections.

Proxying connections directly typically replaces the client's public IP address with Nginx's internal container IP, which disrupts log analysis and fail2ban security mechanisms. SongketMail addresses this by configuring `proxy_protocol on;` within Nginx mail server blocks and enabling PROXY protocol parsing on Dovecot and Postfix listeners. This forwards a PROXY header containing the original client IP and port information to backend services before protocol handshakes initiate.

```nginx
mail {
    # Auth Service endpoint that resolves destination IP/Port
    auth_http http://songketmail-web:8080/mail-auth.php;

    # SSL Termination for Secure Protocols
    ssl_certificate /etc/letsencrypt/live/songketmail/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/songketmail/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    # Enable client IP forwarding via PROXY protocol
    proxy_protocol on;

    # SMTP SMTPS IMAP IMAPS Servers
    server {
        listen 25;
        protocol smtp;
        smtp_auth none; # Let backend authenticate SMTP relays
    }

    server {
        listen 587;
        protocol smtp;
        smtp_auth login plain;
    }

    server {
        listen 465 ssl;
        protocol smtp;
        smtp_auth login plain;
    }

    server {
        listen 143;
        protocol imap;
        starttls on;
    }

    server {
        listen 993 ssl;
        protocol imap;
    }
}
```

---

## 💡 How Nginx Mail Authentication & Client IP Preservation Works

For incoming mail protocol connections, Nginx uses the **ngx_mail_auth_http_module** to validate user credentials against an HTTP authentication service before proxying the session.

Upon receiving a client connection, Nginx issues an HTTP GET request to the authentication endpoint, passing headers such as:

```http
Auth-User: user@songketmail.internal
Auth-Pass: plain_or_hashed_password
Auth-Protocol: imap
Client-IP: 203.0.113.50
```

When the authentication service validates the user against the database, it returns an HTTP 200 OK containing the destination details:

```http
HTTP/1.1 200 OK
Auth-Status: OK
Auth-Server: 10.89.1.15  # Internal IP of Dovecot container
Auth-Port: 143           # Internal IMAP Port
```

Nginx then transparently bridges the IMAPS TCP stream directly to the Dovecot container. Since `proxy_protocol on;` is enabled, Nginx prepends the PROXY header:

```
PROXY TCP4 203.0.113.50 10.89.1.1 43212 993
```

This preserves the client's public IP address (`203.0.113.50`) inside Postfix and Dovecot's logs, enabling fail2ban and audit routines natively.
