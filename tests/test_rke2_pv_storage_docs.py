"""Tests for the RKE2 persistent-volume documentation in Section 8.6.

The guide is executable documentation: operators copy the shell commands and
Kubernetes manifests into production environments.  These tests therefore
check both the individual examples and the relationships between the PV/PVC
resources, while remaining independent of optional YAML/HTML dependencies.
"""

import html
import re
from pathlib import Path

import pytest


MARKDOWN_PATH = Path("docs/k8s-ceph-design.md")
HTML_PATH = Path("docs/k8s-ceph-design.html")
SECTION_HEADING = "### 8.6 Persistent Volume (PV) Storage Server Setup for RKE2"
SECTION_ANCHOR = "86-persistent-volume-pv-storage-server-setup-for-rke2"


@pytest.fixture(scope="module")
def markdown_section() -> str:
    """Return only Section 8.6 from the Markdown guide."""
    content = MARKDOWN_PATH.read_text(encoding="utf-8")
    start = content.index(SECTION_HEADING)
    end = content.index("\n---", start)
    return content[start:end]


@pytest.fixture(scope="module")
def html_section() -> str:
    """Return only Section 8.6 from the generated HTML guide."""
    content = HTML_PATH.read_text(encoding="utf-8")
    start = content.index(f'id="{SECTION_ANCHOR}"')
    end = content.index('<hr class="my-8', start)
    return content[start:end]


def _fenced_block(section: str, label: str, language: str) -> str:
    """Extract a fenced code block that follows a unique prose label."""
    label_index = section.index(label)
    match = re.search(
        rf"```{re.escape(language)}\s*\n(?P<body>.*?)\n\s*```",
        section[label_index:],
        flags=re.DOTALL,
    )
    assert match is not None, f"Missing {language!r} code block after {label!r}"
    return match.group("body")


def _assert_lines(block: str, *expected_lines: str) -> None:
    """Assert exact logical lines without coupling tests to indentation."""
    lines = {line.strip() for line in block.splitlines() if line.strip()}
    missing = [line for line in expected_lines if line not in lines]
    assert not missing, f"Missing lines from documented example: {missing}"


def test_section_documents_all_three_supported_storage_architectures(markdown_section):
    """The new section keeps NFS, Ceph RBD, and static PV guidance together and ordered."""
    headings = [
        "#### A. Dedicated NFS Storage Server Provisioning (`ReadWriteMany` / RWX)",
        "#### B. External Ceph CSI Storage Provisioning (RBD)",
        "#### C. Static PV Binding & Local Path Provisioner",
    ]

    assert all(heading in markdown_section for heading in headings)
    assert [markdown_section.index(heading) for heading in headings] == sorted(
        markdown_section.index(heading) for heading in headings
    )


def test_nfs_server_exports_are_scoped_and_root_squashed(markdown_section):
    """Both NFS exports use the documented subnet and prevent remote root privileges."""
    nfs_setup = _fenced_block(
        markdown_section,
        "NFS Storage Server Provisioning (`10.200.10.50`)",
        "bash",
    )

    for export_path in ("/srv/nfs/rke2-pv", "/srv/nfs/rke2-static-pv"):
        export = (
            f'echo "{export_path} '
            '10.200.10.0/24(rw,sync,no_subtree_check,root_squash)" '
            "| sudo tee -a /etc/exports"
        )
        assert export in nfs_setup

    assert "no_root_squash" not in nfs_setup
    assert "(rw,*" not in nfs_setup
    _assert_lines(
        nfs_setup,
        "sudo chmod 755 /srv/nfs/rke2-pv /srv/nfs/rke2-static-pv",
        "sudo exportfs -rav",
        "sudo systemctl enable --now nfs-kernel-server",
    )


def test_dynamic_nfs_provisioner_targets_the_secured_export(markdown_section):
    """Dynamic provisioning points to the server/export configured immediately above it."""
    provisioner = _fenced_block(
        markdown_section,
        "Dynamic Volume Provisioning via `nfs-subdir-external-provisioner`",
        "bash",
    )

    _assert_lines(
        provisioner,
        "--set nfs.server=10.200.10.50 \\",
        "--set nfs.path=/srv/nfs/rke2-pv \\",
        "--set storageClass.name=nfs-client \\",
        "--set storageClass.allowVolumeExpansion=false \\",
        "--namespace kube-system",
    )


def test_ceph_storage_class_has_complete_csi_secret_wiring(markdown_section):
    """The RBD StorageClass includes every secret reference needed by its CSI operations."""
    storage_class = _fenced_block(
        markdown_section,
        "Ceph RBD StorageClass Manifest (`ceph-rbd-sc.yaml`)",
        "yaml",
    )

    _assert_lines(
        storage_class,
        "apiVersion: storage.k8s.io/v1",
        "kind: StorageClass",
        "name: ceph-rbd",
        'storageclass.kubernetes.io/is-default-class: "true"',
        "provisioner: rbd.csi.ceph.com",
        'clusterID: "<CEPH_CLUSTER_ID_PLACEHOLDER>"',
        'pool: "<CEPH_RBD_POOL_PLACEHOLDER>"',
        "reclaimPolicy: Delete",
        "allowVolumeExpansion: true",
    )

    operations = ("provisioner", "node-stage", "controller-expand")
    for operation in operations:
        assert (
            f"csi.storage.k8s.io/{operation}-secret-name: csi-rbd-secret"
            in storage_class
        )
        assert (
            f"csi.storage.k8s.io/{operation}-secret-namespace: kube-system"
            in storage_class
        )


def test_ceph_pvc_uses_the_documented_rbd_storage_class(markdown_section):
    """The dynamic PVC consumes the StorageClass and keeps its intended capacity/access mode."""
    pvc = _fenced_block(
        markdown_section,
        "Persistent Volume Claim Example (`rke2-pvc-ceph.yaml`)",
        "yaml",
    )

    _assert_lines(
        pvc,
        "kind: PersistentVolumeClaim",
        "name: songketmail-data-pvc",
        "storageClassName: ceph-rbd",
        "- ReadWriteOnce",
        "storage: 50Gi",
    )


def test_static_pv_and_pvc_binding_contract_matches(markdown_section):
    """The static claim binds exactly to its retained NFS volume with compatible attributes."""
    pv = _fenced_block(
        markdown_section,
        "Static Persistent Volume Manifest (`rke2-static-pv.yaml`)",
        "yaml",
    )
    pvc = _fenced_block(
        markdown_section,
        "Matching Static Persistent Volume Claim (`rke2-static-pvc.yaml`)",
        "yaml",
    )

    _assert_lines(
        pv,
        "kind: PersistentVolume",
        "name: static-nfs-pv",
        "storage: 100Gi",
        "- ReadWriteMany",
        "persistentVolumeReclaimPolicy: Retain",
        "server: 10.200.10.50",
        "path: /srv/nfs/rke2-static-pv",
    )
    _assert_lines(
        pvc,
        "kind: PersistentVolumeClaim",
        "name: static-nfs-pvc",
        "storageClassName: \"\"",
        "volumeName: static-nfs-pv",
        "storage: 100Gi",
        "- ReadWriteMany",
    )


def test_html_section_anchor_is_linked_once_from_the_toc():
    """The generated Section 8.6 anchor remains reachable without duplicate IDs."""
    content = HTML_PATH.read_text(encoding="utf-8")

    assert content.count(f'id="{SECTION_ANCHOR}"') == 1
    assert content.count(f'href="#{SECTION_ANCHOR}"') == 1
    assert content.index(f'id="{SECTION_ANCHOR}"') < content.index(
        "Deep State of Mind (DSOM) For My AI Protocol"
    )


def test_new_and_repaired_html_examples_are_real_code_blocks(html_section):
    """Regression: fenced examples render as code blocks, never literal backtick paragraphs."""
    full_html = HTML_PATH.read_text(encoding="utf-8")
    verification_start = full_html.index(
        'id="85-verification-operational-handover-checklist"'
    )
    verification_end = full_html.index(f'id="{SECTION_ANCHOR}"', verification_start)
    verification_section = full_html[verification_start:verification_end]

    assert html_section.count("<pre") == 7
    assert html_section.count("<code>") == 7
    assert verification_section.count("<pre") == 3
    assert verification_section.count("<code>") == 3
    assert "```" not in verification_section
    assert "```" not in html_section


@pytest.mark.parametrize(
    "term",
    [
        "10.200.10.50",
        "/srv/nfs/rke2-static-pv",
        "rbd.csi.ceph.com",
        "csi-rbd-secret",
        "songketmail-data-pvc",
        "persistentVolumeReclaimPolicy: Retain",
        "storageClassName: \"\"",
    ],
)
def test_critical_storage_details_match_markdown_and_html(
    term, markdown_section, html_section
):
    """Generated HTML does not silently drift from operationally significant Markdown values."""
    assert term in markdown_section
    assert html.escape(term, quote=False) in html_section
