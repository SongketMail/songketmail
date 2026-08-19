import os
import re
import pytest

DOCS_DIR = "docs"
GROUP_VARS_FILE = "group_vars/all.yml"
QUADLET_DIR = "roles/podman_quadlet/templates"

def _read_file(path):
    """
    Read a UTF-8 encoded text file.
    
    Parameters:
    	path: Path to the file to read.
    
    Returns:
    	str: The file contents.
    """
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def test_email_security_docs_exist():
    """Verifies that Markdown and HTML documentation for Part 25 exists."""
    md_path = os.path.join(DOCS_DIR, "email-security-design.md")
    html_path = os.path.join(DOCS_DIR, "email-security-design.html")
    assert os.path.isfile(md_path), "email-security-design.md missing"
    assert os.path.isfile(html_path), "email-security-design.html missing"

def test_email_security_okf_frontmatter():
    """Verifies OKF v0.1 frontmatter header in email-security-design.md."""
    content = _read_file(os.path.join(DOCS_DIR, "email-security-design.md"))
    assert content.startswith("---")
    parts = content.split("---")
    assert len(parts) >= 3
    frontmatter = parts[1]
    assert "okf_version: 0.1" in frontmatter
    assert "type: documentation" in frontmatter
    assert "Email Security" in frontmatter
    assert "dane" in frontmatter
    assert "jmap" in frontmatter

def test_email_security_markdown_contents():
    """Verifies critical concepts in email-security-design.md."""
    content = _read_file(os.path.join(DOCS_DIR, "email-security-design.md"))

    # Core concepts
    assert "from the wire to the mailbox" in content
    assert "Security is a default, not an add-on" in content
    assert "DANE" in content
    assert "MTA-STS" in content
    assert "TLS Reporting" in content or "TLSRPT" in content
    assert "ACMEv2" in content
    assert "Smallstep" in content or "step-ca" in content
    assert "S/MIME" in content
    assert "OpenPGP" in content
    assert "JMAP" in content
    assert "JSON Meta Application Protocol" in content
    assert "RFC 8620" in content
    assert "RFC 8621" in content
    assert "Rust" in content
    assert "Independently Security-Audited" in content or "independently security-audited" in content.lower()

def test_email_security_html_structure():
    """Verifies HTML structure and anchors for email-security-design.html."""
    content = _read_file(os.path.join(DOCS_DIR, "email-security-design.html"))
    assert 'id="1-executive-summary-security-philosophy"' in content
    assert 'id="3-strong-transport-security-dane-mta-sts-tls-reporting"' in content
    assert 'id="4-automatic-tls-provisioning-via-acmev2-smallstep-ca"' in content
    assert 'id="5-zero-trust-mailbox-encryption-at-rest-openpgp-smime"' in content
    assert 'id="6-json-meta-application-protocol-jmap-rfc-8620-rfc-8621"' in content
    assert 'id="8-ansible-security-by-default-playbook-mapping"' in content

def test_group_vars_security_controls():
    """Verifies security-by-default configuration parameters in group_vars/all.yml."""
    content = _read_file(GROUP_VARS_FILE)
    assert "enable_dane: true" in content
    assert "enable_mta_sts: true" in content
    assert "enable_tls_rpt: true" in content
    assert "enable_acme_v2: true" in content
    assert "ca.songketmail.internal" in content
    assert "enable_openpgp_smime_at_rest: true" in content
    assert "enable_jmap_protocol: true" in content
    assert "jmap_port: 8443" in content
    assert "dkim_rotation_days: 90" in content
    assert "- smallstep" in content

def test_smallstep_quadlet_template():
    """Verifies smallstep.container Quadlet template definition."""
    path = os.path.join(QUADLET_DIR, "smallstep.container")
    assert os.path.isfile(path)
    content = _read_file(path)
    assert "[Container]" in content
    assert "smallstep/step-ca" in content
    assert "PublishPort=9000:9000" in content
    assert "keep-id" in content

def test_quadlets_security_env_vars():
    """Verifies security environment variables in proxy, postfix, dovecot, and rspamd Quadlet templates."""
    proxy = _read_file(os.path.join(QUADLET_DIR, "proxy.container"))
    assert "PublishPort={{ jmap_port }}:8443" in proxy
    assert "ENABLE_ACME_V2" in proxy
    assert "SMALLSTEP_CA_URL" in proxy

    postfix = _read_file(os.path.join(QUADLET_DIR, "postfix.container"))
    assert "ENABLE_DANE" in postfix
    assert "ENABLE_MTA_STS" in postfix

    dovecot = _read_file(os.path.join(QUADLET_DIR, "dovecot.container"))
    assert "ENABLE_OPENPGP_SMIME_AT_REST" in dovecot
    assert "ENABLE_JMAP_PROTOCOL" in dovecot

    rspamd = _read_file(os.path.join(QUADLET_DIR, "rspamd.container"))
    assert "DKIM_KEY_BITS" in rspamd
    assert "DKIM_ROTATION_DAYS" in rspamd
