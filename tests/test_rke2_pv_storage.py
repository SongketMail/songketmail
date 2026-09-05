"""Tests for the RKE2 persistent-volume documentation feature.

The feature is documentation-driven, with executable integration points in the
HTML template unifier.  These tests verify the documented manifests and safety
properties as well as the Python registries and rendering behaviour that expose
the new page.
"""

import re
from pathlib import Path
from typing import Optional

import pytest

from scripts import unify_templates


MARKDOWN_PATH = Path("docs/rke2-pv-storage-setup.md")
HTML_PATH = Path("docs/rke2-pv-storage-setup.html")
PAGE_NAME = HTML_PATH.name


@pytest.fixture(scope="module")
def markdown() -> str:
    """Return the Part 28 Markdown source."""
    return MARKDOWN_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def html() -> str:
    """Return the generated Part 28 HTML page."""
    return HTML_PATH.read_text(encoding="utf-8")


def _frontmatter(document: str) -> dict[str, str]:
    """Parse the simple scalar/list frontmatter used by this repository."""
    assert document.startswith("---\n"), "Part 28 must begin with OKF frontmatter"
    _, raw_frontmatter, _ = document.split("---", 2)
    return {
        key.strip(): value.strip().strip('"').strip("'")
        for line in raw_frontmatter.splitlines()
        if ":" in line
        for key, value in [line.split(":", 1)]
    }


def _section(document: str, start: str, end: Optional[str] = None) -> str:
    """Extract a Markdown section between two unique heading markers."""
    start_index = document.index(start)
    end_index = document.index(end, start_index) if end else len(document)
    return document[start_index:end_index]


def _code_block(section: str, marker: str, language: str = "yaml") -> str:
    """Extract a fenced block containing, or immediately following, a marker."""
    block_pattern = re.compile(
        rf"```{re.escape(language)}\n(.*?)\n```",
        flags=re.DOTALL,
    )
    for match in block_pattern.finditer(section):
        if marker in match.group(1):
            return match.group(1)

    marker_index = section.index(marker)
    match = block_pattern.search(section, marker_index)
    assert match, f"No {language} code block found after {marker!r}"
    return match.group(1)


def _sidebar_link(sidebar: str, href: str) -> str:
    """Return the opening anchor for a sidebar destination."""
    match = re.search(rf'<a href="{re.escape(href)}" class="([^"]+)">', sidebar)
    assert match, f"Sidebar link {href!r} was not rendered"
    return match.group(1)


def test_markdown_frontmatter_identifies_part_28(markdown: str):
    """The page exposes complete OKF metadata and searchable storage topics."""
    metadata = _frontmatter(markdown)

    assert metadata["okf_version"] == "0.1"
    assert metadata["type"] == "documentation"
    assert metadata["title"] == (
        "Persistent Volume (PV) Storage Server Setup & RKE2 Storage Architecture"
    )
    assert metadata["resource"] == "file:///docs/rke2-pv-storage-setup.md"
    topics = {topic.strip() for topic in metadata["topics"].strip("[]").split(",")}
    assert {"kubernetes", "rke2", "ceph", "nfs", "pv", "storage"} <= topics


def test_ceph_storage_class_and_claim_are_consistent(markdown: str):
    """The RBD claim selects the declared expandable, retained StorageClass."""
    ceph_section = _section(markdown, "## 💾 1.", "## 📁 2.")
    manifest = _code_block(ceph_section, "#### Kubernetes StorageClass & PVC Manifests")

    assert "kind: StorageClass" in manifest
    assert "name: ceph-rbd" in manifest
    assert "provisioner: rbd.csi.ceph.com" in manifest
    assert "reclaimPolicy: Retain" in manifest
    assert "allowVolumeExpansion: true" in manifest
    assert "kind: PersistentVolumeClaim" in manifest
    assert "storageClassName: ceph-rbd" in manifest
    assert "storage: 100Gi" in manifest
    assert manifest.count('clusterID: "pve-ceph-cluster"') == 1
    for operation in ("provisioner", "node-stage", "controller-expand"):
        assert f"csi.storage.k8s.io/{operation}-secret-name: csi-rbd-secret" in manifest
        assert f"csi.storage.k8s.io/{operation}-secret-namespace: kube-system" in manifest


def test_ceph_helm_values_define_redundant_monitors_and_retained_storage(markdown: str):
    """The Helm values retain data and expose every documented PVE monitor."""
    ceph_section = _section(markdown, "## 💾 1.", "## 📁 2.")
    values = _code_block(ceph_section, "# ceph-csi-values.yaml")

    monitors = re.findall(r'- "(10\.0\.10\.\d+:6789)"', values)
    assert monitors == [
        "10.0.10.11:6789",
        "10.0.10.12:6789",
        "10.0.10.13:6789",
    ]
    assert values.count('clusterID: "pve-ceph-cluster"') == 2
    assert 'name: ceph-rbd' in values
    assert 'pool: "k8s-pool"' in values
    assert "imageFeatures: layering" in values
    assert "reclaimPolicy: Retain" in values
    assert "allowVolumeExpansion: true" in values


@pytest.mark.parametrize(
    ("family_heading", "anonymous_owner", "service_name"),
    [
        ("##### Debian/Ubuntu Family", "nobody:nogroup", "nfs-kernel-server"),
        ("##### AlmaLinux/RockyLinux Family", "nobody:nobody", "nfs-server"),
    ],
)
def test_nfs_server_examples_preserve_storage_ownership_and_root_squash(
    markdown: str,
    family_heading: str,
    anonymous_owner: str,
    service_name: str,
):
    """Both OS examples separate dynamic/static ownership and restrict root."""
    nfs_section = _section(markdown, "## 📁 2.", "## ⚡ 3.")
    family_section = _section(
        nfs_section,
        family_heading,
        "#### RKE2 Worker Client Prerequisites"
        if "AlmaLinux" in family_heading
        else "##### AlmaLinux/RockyLinux Family",
    )
    commands = _code_block(family_section, family_heading, language="bash")

    assert f"chown -R {anonymous_owner} /mnt/k8s_storage" in commands
    assert "chmod 755 /mnt/k8s_storage" in commands
    assert "chown -R 2001:2001 /mnt/k8s_static_pv" in commands
    assert "chmod 775 /mnt/k8s_static_pv" in commands
    for export_path in ("/mnt/k8s_storage", "/mnt/k8s_static_pv"):
        export = (
            f"{export_path} 10.0.20.0/24"
            "(rw,sync,no_subtree_check,root_squash)"
        )
        assert export in commands
    assert f"systemctl enable --now {service_name}" in commands


@pytest.mark.parametrize(
    ("family_heading", "package_command"),
    [
        ("* **Debian/Ubuntu Family:**", "apt-get install -y nfs-common"),
        ("* **AlmaLinux/RockyLinux Family:**", "dnf install -y nfs-utils"),
    ],
)
def test_rke2_workers_install_the_matching_nfs_client(
    markdown: str,
    family_heading: str,
    package_command: str,
):
    """Every supported worker OS installs its NFS mount helper."""
    nfs_section = _section(markdown, "## 📁 2.", "## ⚡ 3.")
    clients = _section(
        nfs_section,
        "#### RKE2 Worker Client Prerequisites",
        "### RKE2 NFS Provisioner Configuration",
    )
    family_section = _section(
        clients,
        family_heading,
        "* **AlmaLinux/RockyLinux Family:**"
        if "Debian" in family_heading
        else None,
    )

    assert package_command in _code_block(family_section, family_heading, language="bash")


def test_nfs_provisioner_values_match_the_server_export(markdown: str):
    """The dynamic provisioner consumes the export created in both OS guides."""
    nfs_section = _section(markdown, "## 📁 2.", "## ⚡ 3.")
    values = _code_block(nfs_section, "# nfs-values.yaml")
    install = _code_block(nfs_section, "#### Helm Installation Command", language="bash")

    assert "server: 10.0.20.50" in values
    assert "path: /mnt/k8s_storage" in values
    assert "name: nfs-client" in values
    assert "defaultClass: false" in values
    assert "archiveOnDelete: false" in values
    assert "-f nfs-values.yaml" in install
    assert "--namespace kube-system" in install


def test_static_pv_and_claim_bind_explicitly(markdown: str):
    """The static claim cannot accidentally select a dynamic StorageClass."""
    local_section = _section(markdown, "## ⚡ 3.", "## ⚖️ Storage Decision Matrix")
    manifest = _code_block(local_section, "# rke2-static-pv.yaml")

    assert "name: static-nfs-pv" in manifest
    assert "persistentVolumeReclaimPolicy: Retain" in manifest
    assert "server: 10.0.20.50" in manifest
    assert "path: /mnt/k8s_static_pv" in manifest
    assert 'storageClassName: ""' in manifest
    assert "volumeName: static-nfs-pv" in manifest
    assert manifest.count("storage: 100Gi") == 2
    assert manifest.count("ReadWriteMany") == 2


def test_local_path_config_has_a_nonempty_default_node_path(markdown: str):
    """Unlisted RKE2 nodes still receive a valid local provisioning path."""
    local_section = _section(markdown, "## ⚡ 3.", "## ⚖️ Storage Decision Matrix")
    config = _code_block(local_section, "# local-path-config.yaml")

    assert "name: local-path-config" in config
    assert "namespace: kube-system" in config
    assert '"node":"DEFAULT_PATH_FOR_NON_LISTED_NODES"' in config
    assert '"paths":["/opt/local-path-provisioner"]' in config


def test_storage_decision_matrix_documents_resiliency_boundaries(markdown: str):
    """The comparison does not present NFS or local disks as node-level HA."""
    matrix = _section(markdown, "## ⚖️ Storage Decision Matrix")

    assert "Multi-node OSD replication, dynamic failover" in matrix
    assert "Single NFS server (SPOF unless NAS/SAN appliance)" in matrix
    assert "Bound to single host disk (No node HA)" in matrix
    assert "Ceph CSI (RBD)" in matrix and "ReadWriteOnce" in matrix
    assert "NFS External" in matrix and "ReadWriteMany" in matrix


@pytest.mark.parametrize(
    ("path", "expected_link"),
    [
        (Path("docs/README.md"), "(rke2-pv-storage-setup.md)"),
        (Path("docs/SUMMARY.md"), "(rke2-pv-storage-setup.md)"),
        (Path("docs/k8s-ceph-design.md"), "[Part 28:"),
    ],
)
def test_part_28_is_reachable_from_documentation_navigation(path: Path, expected_link: str):
    """Every changed navigation surface points readers to the new guide."""
    content = path.read_text(encoding="utf-8")

    assert expected_link in content
    assert "rke2-pv-storage-setup.md" in content


def test_template_registries_define_the_complete_rke2_page_contract():
    """Sidebar, footer pills, and subtitle use one exact Part 28 identity."""
    entries = [item for item in unify_templates.SIDEBAR_ITEMS if item.get("href") == PAGE_NAME]

    assert entries == [
        {
            "href": PAGE_NAME,
            "icon": "💾",
            "label": "28. RKE2 PV Storage Setup",
            "section": "research",
        }
    ]
    page_index = unify_templates.SIDEBAR_ITEMS.index(entries[0])
    assert unify_templates.SIDEBAR_ITEMS[page_index - 1]["href"] == (
        "docs-sync-pipeline-guide.html"
    )
    assert unify_templates.SIDEBAR_ITEMS[page_index + 1]["header"] == "Laboratory Modules"
    assert unify_templates.TOPIC_MAP[PAGE_NAME] == (
        "[ TOPIC: 28 ]",
        "[ ORCH: RKE2_PV ]",
        "[ STORAGE: CEPH_NFS_LOCAL ]",
    )
    assert unify_templates.SUBTITLE_MAP[PAGE_NAME] == (
        "Deep Research // Topic 28: Persistent Volume (PV) Storage Server Setup for RKE2"
    )


def test_sidebar_marks_only_the_current_rke2_page_active():
    """Part 28 is highlighted on itself and remains inactive elsewhere."""
    active_classes = _sidebar_link(unify_templates.make_sidebar(PAGE_NAME), PAGE_NAME)
    inactive_classes = _sidebar_link(unify_templates.make_sidebar("index.html"), PAGE_NAME)

    assert "bg-violet-50" in active_classes
    assert "font-bold" in active_classes
    assert "bg-violet-50" not in inactive_classes
    assert "hover:bg-slate-50" in inactive_classes


def test_build_unified_html_renders_rke2_metadata_end_to_end(markdown: str):
    """The page contract reaches the title, header, nav, body, and footer."""
    metadata = _frontmatter(markdown)
    rendered = unify_templates.build_unified_html(
        PAGE_NAME,
        metadata,
        center_content='<h2 id="storage">Storage content</h2>',
        right_sidebar_inner='<a href="#storage">Storage</a>',
    )

    assert f"<title>{metadata['title']} — SongketMail :: LAB</title>" in rendered
    assert unify_templates.SUBTITLE_MAP[PAGE_NAME] in rendered
    assert '<a href="rke2-pv-storage-setup.html"' in rendered
    assert "bg-violet-50" in _sidebar_link(rendered, PAGE_NAME)
    assert '<h2 id="storage">Storage content</h2>' in rendered
    assert '<a href="#storage">Storage</a>' in rendered
    for pill in unify_templates.TOPIC_MAP[PAGE_NAME]:
        assert rendered.count(pill) == 1


def test_rke2_metadata_does_not_leak_to_unregistered_pages():
    """Regression: the new page mappings must not alter fallback rendering."""
    rendered = unify_templates.build_unified_html(
        "unregistered-page.html",
        {},
        center_content="",
        right_sidebar_inner="",
    )

    assert unify_templates.SUBTITLE_MAP[PAGE_NAME] not in rendered
    assert "[ TOPIC: 28 ]" not in rendered
    assert "[ ORCH: RKE2_PV ]" not in rendered
    assert "SECURE EMAIL SERVER FABRIC // PODMAN 5+ & SYSTEMD QUADLET" in rendered
    assert "[ REL: 5.0.0 ]" in rendered


def test_generated_html_has_unique_and_navigable_heading_anchors(html: str):
    """Every generated h2/h3 anchor is unique and represented in the TOC."""
    heading_ids = re.findall(r'<h[23]\b[^>]*\bid="([^"]+)"', html, flags=re.IGNORECASE)
    toc_targets = set(re.findall(r'href="#([^"]+)"', html))

    assert len(heading_ids) >= 10
    assert len(heading_ids) == len(set(heading_ids))
    assert set(heading_ids) <= toc_targets
    assert "rke2-persistent-volume-pv-storage-architecture" in heading_ids
    assert "storage-decision-matrix-architectural-comparison" in heading_ids
    for pill in unify_templates.TOPIC_MAP[PAGE_NAME]:
        assert html.count(pill) == 1
