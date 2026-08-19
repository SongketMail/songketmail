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


# --- Additional coverage: group_vars/all.yml security-by-default fields ---

def test_group_vars_smallstep_image_tag_defined():
    """Verifies the smallstep_image_tag container image pin was added alongside other image tags."""
    content = _read_file(GROUP_VARS_FILE)
    assert 'smallstep_image_tag: "0.26.1"' in content
    # Must be declared in the same image-tag block as the other services (no :latest tags).
    tag_block_match = re.search(
        r"bunkerweb_image_tag:.*?smallstep_image_tag:\s*\"[^\"]+\"",
        content,
        re.DOTALL,
    )
    assert tag_block_match is not None, "smallstep_image_tag is not grouped with other image tags"


def test_group_vars_songketmail_services_includes_smallstep():
    """Verifies the songketmail_services list was extended with the smallstep entry."""
    content = _read_file(GROUP_VARS_FILE)
    services_match = re.search(r"songketmail_services:\n((?:\s+-\s+\S+\n)+)", content)
    assert services_match, "songketmail_services list not found"
    services = [line.strip().lstrip("- ").strip() for line in services_match.group(1).splitlines() if line.strip()]
    assert services == ["proxy", "postfix", "dovecot", "db", "s3", "web", "rspamd", "smallstep"]


def test_group_vars_storage_dirs_includes_smallstep_paths():
    """Verifies smallstep/config and smallstep/data were appended to songketmail_storage_dirs."""
    content = _read_file(GROUP_VARS_FILE)
    dirs_match = re.search(r'songketmail_storage_dirs:\n((?:\s+-\s+"[^"]+"\n?)+)', content)
    assert dirs_match, "songketmail_storage_dirs list not found"
    dirs = re.findall(r'"([^"]+)"', dirs_match.group(1))
    assert "smallstep/config" in dirs
    assert "smallstep/data" in dirs
    # Ensure they are the trailing two entries appended by this PR.
    assert dirs[-2:] == ["smallstep/config", "smallstep/data"]


def test_group_vars_security_controls_types():
    """Verifies numeric/boolean security-by-default fields have the expected literal types."""
    content = _read_file(GROUP_VARS_FILE)
    assert "jmap_port: 8443" in content
    assert "dkim_key_bits: 2048" in content
    assert "dkim_rotation_days: 90" in content
    # Boolean flags must be lower-case YAML booleans, not quoted strings.
    for flag in ["enable_dane", "enable_mta_sts", "enable_tls_rpt", "enable_acme_v2",
                 "enable_openpgp_smime_at_rest", "enable_jmap_protocol"]:
        assert re.search(rf"^{flag}:\s*true\s*$", content, re.MULTILINE), f"{flag} is not set to boolean true"


# --- Additional coverage: Quadlet template Jinja2 filter correctness ---

def test_quadlet_security_env_vars_use_default_string_lower_filters():
    """Verifies boolean security toggles are rendered through default/string/lower Jinja2 filters."""
    filter_pattern = re.compile(r"\{\{\s*\w+\s*\|\s*default\(true\)\s*\|\s*string\s*\|\s*lower\s*\}\}")

    proxy = _read_file(os.path.join(QUADLET_DIR, "proxy.container"))
    postfix = _read_file(os.path.join(QUADLET_DIR, "postfix.container"))
    dovecot = _read_file(os.path.join(QUADLET_DIR, "dovecot.container"))

    for name, content, expected_count in (
        ("proxy.container", proxy, 3),
        ("postfix.container", postfix, 3),
        ("dovecot.container", dovecot, 2),
    ):
        matches = filter_pattern.findall(content)
        assert len(matches) == expected_count, (
            f"{name}: expected {expected_count} default/string/lower boolean env vars, found {len(matches)}"
        )


def test_quadlet_env_vars_isolated_per_service():
    """Verifies security env vars are scoped to their intended service and not leaked into others."""
    postfix = _read_file(os.path.join(QUADLET_DIR, "postfix.container"))
    dovecot = _read_file(os.path.join(QUADLET_DIR, "dovecot.container"))
    rspamd = _read_file(os.path.join(QUADLET_DIR, "rspamd.container"))
    proxy = _read_file(os.path.join(QUADLET_DIR, "proxy.container"))

    # DANE/MTA-STS/TLSRPT belong to postfix, not dovecot or rspamd's dedicated DKIM vars.
    assert "ENABLE_DANE" not in dovecot
    assert "ENABLE_DANE" not in rspamd
    assert "DKIM_KEY_BITS" not in postfix
    assert "DKIM_KEY_BITS" not in dovecot
    # OpenPGP/S-MIME-at-rest and JMAP toggles belong to dovecot; ACME/Smallstep belong to proxy.
    assert "ENABLE_OPENPGP_SMIME_AT_REST" not in proxy
    assert "SMALLSTEP_CA_URL" not in postfix
    assert "SMALLSTEP_CA_URL" not in dovecot


def test_proxy_container_jmap_port_publish_line():
    """Verifies the JMAP PublishPort line is present and distinct from the existing HTTPS mapping."""
    content = _read_file(os.path.join(QUADLET_DIR, "proxy.container"))
    lines = [l for l in content.splitlines() if l.startswith("PublishPort=")]
    assert "PublishPort={{ jmap_port }}:8443" in lines
    assert "PublishPort=443:8443" in lines
    # The templated jmap_port entry must appear after the static HTTPS TCP/UDP entries.
    idx_https = lines.index("PublishPort=443:8443")
    idx_jmap = lines.index("PublishPort={{ jmap_port }}:8443")
    assert idx_jmap > idx_https


def test_smallstep_container_full_definition():
    """Verifies the new smallstep.container Quadlet unit has all required sections and directives."""
    content = _read_file(os.path.join(QUADLET_DIR, "smallstep.container"))

    assert "[Unit]" in content
    assert "[Container]" in content
    assert "[Install]" in content
    assert "After=network-online.target" in content
    assert "WantedBy=default.target" in content

    assert "ContainerName={{ cluster_prefix }}-smallstep" in content
    assert "Image=docker.io/smallstep/step-ca:{{ smallstep_image_tag }}" in content
    assert "Network={{ podman_network_name }}" in content
    assert "UserNS=keep-id:uid={{ songketmail_uid }},gid={{ songketmail_gid }}" in content
    assert "Volume={{ storage_base_path }}/smallstep/config:/home/step/config:Z" in content
    assert "Volume={{ storage_base_path }}/smallstep/data:/home/step/db:Z" in content
    assert "PublishPort=9000:9000" in content
    assert "Environment=DOCKER_STEPCA_INIT_NAME=SongketMail Private CA" in content
    assert "Environment=DOCKER_STEPCA_INIT_DNS_NAMES=localhost,ca.songketmail.internal" in content
    assert "Environment=DOCKER_STEPCA_INIT_PROVISIONER_NAME=admin@songketmail.internal" in content
    assert "Label=fabric_cluster={{ cluster_prefix }}" in content
    assert "Label=service_type=smallstep" in content

    # No hardcoded plaintext passwords should be present in the new template.
    assert not re.search(r"Environment=.*PASSWORD=(?!\{\{)", content, re.IGNORECASE)


# --- Additional coverage: docs/SUMMARY.md and docs/ansible-playbook-map.md updates ---

def test_summary_md_lists_part25_entry():
    """Verifies SUMMARY.md contains the new Part 25 entry linking to email-security-design.md."""
    content = _read_file(os.path.join(DOCS_DIR, "SUMMARY.md"))
    assert "* [Part 25: Email Security from the Wire to the Mailbox, JMAP Protocol & ACME Management](email-security-design.md)" in content
    # Part 25 must come after Part 24 and before the DSOM footer.
    idx_24 = content.index("Part 24: Proxmox VE Enterprise Datacentre Architecture")
    idx_25 = content.index("Part 25: Email Security from the Wire to the Mailbox")
    idx_footer = content.index("Deep State of Mind (DSOM)")
    assert idx_24 < idx_25 < idx_footer


def test_ansible_playbook_map_site_yml_services_updated():
    """Verifies the site.yml row in the master matrix lists RustFS and Smallstep CA as managed services."""
    content = _read_file(os.path.join(DOCS_DIR, "ansible-playbook-map.md"))
    assert "BunkerWeb, Postfix, Dovecot, PostgreSQL, RustFS, Roundcube, Rspamd, Smallstep CA" in content
    assert "[Part 25](email-security-design.md)" in content


def test_ansible_playbook_map_part25_related_docs_entry():
    """Verifies the related documentation section links to the new Part 25 email security document."""
    content = _read_file(os.path.join(DOCS_DIR, "ansible-playbook-map.md"))
    assert "**[Part 25: Email Security & JMAP Protocol](email-security-design.md)**" in content
    assert "DANE, MTA-STS, TLSRPT" in content
    assert "Smallstep ACMEv2 CA" in content


# --- Additional coverage: sitemap.txt manifests ---

def test_sitemaps_include_email_security_design_url():
    """Verifies both root and docs/ sitemap.txt list the new email-security-design.html page."""
    expected_url = "https://songketmail.github.io/songketmail/email-security-design.html"
    for path in ("sitemap.txt", os.path.join(DOCS_DIR, "sitemap.txt")):
        content = _read_file(path)
        assert expected_url in content, f"{path} is missing {expected_url}"


def test_root_and_docs_sitemap_are_identical():
    """Verifies root sitemap.txt and docs/sitemap.txt stay in sync (both updated in this PR)."""
    root_content = _read_file("sitemap.txt")
    docs_content = _read_file(os.path.join(DOCS_DIR, "sitemap.txt"))
    assert root_content == docs_content


def test_sitemap_email_security_entry_ordered_after_privilege_report():
    """Verifies the new sitemap entry was appended directly after the privilege-safety-report entry."""
    content = _read_file("sitemap.txt")
    lines = [l for l in content.splitlines() if l.strip()]
    idx_privilege = next(i for i, l in enumerate(lines) if "privilege-safety-report.html" in l)
    idx_email_security = next(i for i, l in enumerate(lines) if "email-security-design.html" in l)
    assert idx_email_security == idx_privilege + 1


# --- Additional coverage: docs/email_security_preview.png binary asset ---

def test_email_security_preview_png_is_valid_png():
    """Verifies the new preview image exists, is non-empty, and has a valid PNG signature/dimensions."""
    import struct

    path = os.path.join(DOCS_DIR, "email_security_preview.png")
    assert os.path.isfile(path), "email_security_preview.png missing"
    assert os.path.getsize(path) > 0, "email_security_preview.png is empty"

    with open(path, "rb") as f:
        header = f.read(24)

    assert header[:8] == b"\x89PNG\r\n\x1a\n", "email_security_preview.png has an invalid PNG signature"
    width, height = struct.unpack(">II", header[16:24])
    assert width > 0 and height > 0, "email_security_preview.png reports invalid dimensions"


# --- Additional coverage: email-security-design content structural regressions ---

def test_email_security_markdown_section_ordering():
    """Verifies the 8 major sections of email-security-design.md appear in ascending order."""
    content = _read_file(os.path.join(DOCS_DIR, "email-security-design.md"))
    headings = [
        "## 🔒 1. Executive Summary & Security Philosophy",
        "## 🏗️ 2. End-to-End Email Security Architecture",
        "## 🌐 3. Strong Transport Security: DANE, MTA-STS & TLS Reporting",
        "## 🔑 4. Automatic TLS Provisioning via ACMEv2 & Smallstep CA",
        "## 🔐 5. Zero-Trust Mailbox Encryption at Rest (OpenPGP & S/MIME)",
        "## ⚡ 6. JSON Meta Application Protocol (JMAP - RFC 8620 & RFC 8621)",
        "## 🛡️ 7. Granular ACLs, Rate Limiting, DKIM Automation & Rust Memory Safety",
        "## ⚙️ 8. Ansible Security-by-Default Playbook Mapping",
    ]
    positions = [content.index(h) for h in headings]
    assert positions == sorted(positions), "email-security-design.md sections are out of order"


def test_email_security_markdown_ansible_mapping_table_rows():
    """Verifies the Ansible security-by-default mapping table rows match the Quadlet templates."""
    content = _read_file(os.path.join(DOCS_DIR, "email-security-design.md"))
    expected_rows = [
        ("**DANE & DNSSEC Validation**", "`enable_dane: true`", "`postfix.container`"),
        ("**MTA-STS Enforcement**", "`enable_mta_sts: true`", "`proxy.container` / `postfix.container`"),
        ("**TLS Reporting (TLSRPT)**", "`enable_tls_rpt: true`", "`postfix.container` / `rspamd.container`"),
        ("**ACMEv2 Certificate Auto-Renewal**", "`enable_acme_v2: true`", "`proxy.container`"),
        ("**Smallstep Private CA & SSH SSO**", 'smallstep_ca_url: "https://ca...', "`smallstep.container`"),
        ("**S/MIME / OpenPGP Encryption at Rest**", "`enable_openpgp_smime_at_rest: true`", "`dovecot.container`"),
        ("**JMAP Protocol API (Port 8443)**", "`enable_jmap_protocol: true`", "`proxy.container` / `dovecot.container`"),
        ("**DKIM Auto Rotation (90 Days)**", "`dkim_rotation_days: 90`", "`rspamd.container`"),
    ]
    for feature, variable, target in expected_rows:
        assert feature in content, f"Missing table feature cell: {feature}"
        assert variable in content, f"Missing table variable cell: {variable}"
        assert target in content, f"Missing table target cell: {target}"


def test_email_security_html_table_of_contents_links_resolve_to_anchors():
    """Verifies each right-hand ToC anchor link in the HTML has a matching heading id."""
    content = _read_file(os.path.join(DOCS_DIR, "email-security-design.html"))
    toc_hrefs = re.findall(r'href="#([\w-]+)"', content)
    assert len(toc_hrefs) > 0, "No table-of-contents anchor links found"
    for anchor in toc_hrefs:
        assert f'id="{anchor}"' in content, f"ToC link #{anchor} has no matching heading id"


def test_email_security_html_no_placeholder_or_broken_markers():
    """Regression guard: ensures no leftover TODO/placeholder markers exist in the new HTML page."""
    content = _read_file(os.path.join(DOCS_DIR, "email-security-design.html"))
    for marker in ("TODO", "FIXME", "{{", "}}", "<<<<<<<", ">>>>>>>"):
        assert marker not in content, f"Found leftover placeholder marker '{marker}' in email-security-design.html"
