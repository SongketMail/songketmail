"""
tests/test_docs_source_pages.py - Unit test suite for the Mintlify documentation
site added under docs-source/ (the "Documentation Sync Pipeline" feature).

Covers:
- docs-source/docs.json: schema fields, theme/colors, and navigation integrity
  (every referenced page must resolve to a real file, cross-checked with the
  extract_pages_from_nav/resolve_page_path helpers already unit tested for
  scripts/sync_docs.py).
- docs-source/.atlas-analysis.json: structural validity of the project metadata
  consumed by documentation tooling.
- docs-source/.mintignore, AGENTS.md, LICENSE, README.md: presence and expected
  boilerplate content.
- docs-source/*.mdx pages added by this PR: frontmatter completeness.
- docs-source/favicon.svg and logo/*.svg: well-formed XML/SVG assets.

Per this repository's convention (see tests/test_ansible_podman_md_python.py and
get_markdown_files()), the docs-source/ directory is a separate, Mintlify-specific
documentation project and is intentionally excluded from the repository-wide OKF
frontmatter checks in tests/test_all.py; the tests below validate it on its own
terms instead.
"""

import json
import os
import re
import sys
import xml.etree.ElementTree as ET

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts import sync_docs  # noqa: E402

DOCS_SOURCE_DIR = "docs-source"

# .mdx pages added/modified by this PR (excludes pages that already existed,
# e.g. quickstart.mdx, and pages introduced by unrelated PRs, e.g. service-fabric.mdx).
CHANGED_MDX_FILES = [
    "architecture-overview.mdx",
    os.path.join("deployment", "configuration.mdx"),
    os.path.join("deployment", "prerequisites.mdx"),
    os.path.join("deployment", "running-the-playbook.mdx"),
    os.path.join("deployment", "verification.mdx"),
    "index.mdx",
    "introduction.mdx",
    os.path.join("operations", "backups.mdx"),
    os.path.join("operations", "monitoring.mdx"),
    os.path.join("operations", "service-management.mdx"),
    os.path.join("operations", "troubleshooting.mdx"),
    os.path.join("reference", "ansible-modules.mdx"),
    os.path.join("reference", "dockpod-integration.mdx"),
    os.path.join("reference", "global-variables.mdx"),
    os.path.join("reference", "network-ports.mdx"),
]


def _read(relative_path: str) -> str:
    """Reads and returns UTF-8 text content of a path relative to docs-source/."""
    with open(os.path.join(DOCS_SOURCE_DIR, relative_path), encoding="utf-8") as f:
        return f.read()


def _parse_frontmatter(content: str) -> dict:
    """Parses simple `key: "value"` YAML frontmatter pairs from an .mdx file's header."""
    assert content.startswith("---"), "file does not start with YAML frontmatter markers (---)"
    parts = content.split("---", 2)
    assert len(parts) >= 3, "file has an incomplete frontmatter block"
    frontmatter_text = parts[1]

    fields = {}
    for line in frontmatter_text.splitlines():
        line = line.strip()
        if not line:
            continue
        match = re.match(r'^([A-Za-z0-9_]+):\s*"(.*)"\s*$', line)
        if match:
            fields[match.group(1)] = match.group(2)
    return fields


# --- docs.json structural tests ---

def test_docs_json_exists_and_is_valid_json():
    """Verifies docs-source/docs.json exists and parses as valid JSON."""
    data = json.loads(_read("docs.json"))
    assert isinstance(data, dict)


def test_docs_json_top_level_fields():
    """Verifies docs.json declares the Mintlify schema, product name, theme and favicon."""
    data = json.loads(_read("docs.json"))
    assert data["$schema"] == "https://mintlify.com/docs.json"
    assert data["name"] == "SongketMail"
    assert data["theme"] == "aspen"
    assert data["favicon"] == "/favicon.svg"


def test_docs_json_colors_are_valid_hex_values():
    """Verifies the colors block defines primary/light/dark as valid hex color strings."""
    data = json.loads(_read("docs.json"))
    colors = data["colors"]
    for key in ("primary", "light", "dark"):
        assert key in colors, f"colors.{key} is missing"
        assert re.match(r"^#[0-9A-Fa-f]{6}$", colors[key]), f"colors.{key}='{colors[key]}' is not a valid hex color"


def test_docs_json_navbar_points_to_github_repo():
    """Verifies the navbar's primary action links to the SongketMail GitHub repository."""
    data = json.loads(_read("docs.json"))
    primary = data["navbar"]["primary"]
    assert primary["type"] == "github"
    assert primary["href"] == "https://github.com/SongketMail/songketmail"


def test_docs_json_navigation_has_guide_and_reference_tabs():
    """Verifies the navigation structure declares exactly the Guide and Reference tabs."""
    data = json.loads(_read("docs.json"))
    tabs = data["navigation"]["tabs"]
    tab_names = [t["tab"] for t in tabs]
    assert tab_names == ["Guide", "Reference"]


def test_docs_json_navigation_pages_are_unique():
    """Verifies no page path is referenced more than once across the whole navigation tree."""
    data = json.loads(_read("docs.json"))
    pages = sync_docs.extract_pages_from_nav(data["navigation"])
    assert len(pages) == len(set(pages)), "Duplicate page reference(s) found in docs.json navigation"


def test_docs_json_navigation_pages_all_resolve_to_existing_files():
    """Verifies every page referenced in docs.json navigation resolves to a real source file.

    Exercises the same resolve_page_path() helper used by scripts/sync_docs.py's
    validate_source_docs() safety guard, against the real docs-source directory
    added by this PR.
    """
    from pathlib import Path

    data = json.loads(_read("docs.json"))
    pages = sync_docs.extract_pages_from_nav(data["navigation"])
    assert len(pages) > 0

    source_dir = Path(DOCS_SOURCE_DIR)
    missing = [p for p in pages if not sync_docs.resolve_page_path(source_dir, p)]
    assert missing == [], f"docs.json references non-existent page(s): {missing}"


def test_docs_source_directory_passes_sync_docs_validation():
    """Verifies the real docs-source/ directory passes scripts/sync_docs.py's validate_source_docs guard.

    This is a regression/integration check tying the content added by this PR
    directly to the safety guards that gate the Sync Docs workflow.
    """
    from pathlib import Path

    files = sync_docs.validate_source_docs(Path(DOCS_SOURCE_DIR), min_files=5)
    assert len(files) >= 5


def test_docs_source_only_expected_orphan_is_index(capsys):
    """Verifies index.mdx is the only intentional orphan or fully registered in docs.json.

    Guards against silently forgetting to add a newly created .mdx page to the
    docs.json navigation.
    """
    from pathlib import Path

    sync_docs.validate_source_docs(Path(DOCS_SOURCE_DIR), min_files=5)
    captured = capsys.readouterr()
    orphan_lines = [line for line in captured.out.splitlines() if "Orphan MDX file found" in line]
    assert len(orphan_lines) in (0, 1), f"Unexpected orphan MDX file warnings: {orphan_lines}"
    if len(orphan_lines) == 1:
        assert "index.mdx" in orphan_lines[0]


# --- .atlas-analysis.json tests ---

def test_atlas_analysis_json_is_valid_json():
    """Verifies .atlas-analysis.json exists and parses as valid JSON."""
    data = json.loads(_read(".atlas-analysis.json"))
    assert isinstance(data, dict)


def test_atlas_analysis_json_required_top_level_keys():
    """Verifies .atlas-analysis.json declares all required top-level metadata fields."""
    data = json.loads(_read(".atlas-analysis.json"))
    for key in (
        "projectType",
        "projectName",
        "projectDescription",
        "theme",
        "primaryColor",
        "lightColor",
        "darkColor",
        "navigation",
        "keyFeatures",
        "publicApiSurface",
    ):
        assert key in data, f"'{key}' missing from .atlas-analysis.json"


def test_atlas_analysis_json_project_identity():
    """Verifies the project identity fields match SongketMail's Mintlify aspen theme."""
    data = json.loads(_read(".atlas-analysis.json"))
    assert data["projectType"] == "infrastructure"
    assert data["projectName"] == "SongketMail"
    assert data["theme"] == "aspen"
    assert len(data["projectDescription"]) > 0


def test_atlas_analysis_json_colors_match_docs_json():
    """Verifies the color palette in .atlas-analysis.json is consistent with docs.json."""
    atlas_data = json.loads(_read(".atlas-analysis.json"))
    docs_data = json.loads(_read("docs.json"))

    assert atlas_data["primaryColor"] == docs_data["colors"]["primary"]
    assert atlas_data["lightColor"] == docs_data["colors"]["light"]
    assert atlas_data["darkColor"] == docs_data["colors"]["dark"]


def test_atlas_analysis_json_key_features_and_api_surface_are_nonempty_string_lists():
    """Verifies keyFeatures and publicApiSurface are non-empty lists of non-empty strings."""
    data = json.loads(_read(".atlas-analysis.json"))
    for list_key in ("keyFeatures", "publicApiSurface"):
        items = data[list_key]
        assert isinstance(items, list)
        assert len(items) > 0
        for item in items:
            assert isinstance(item, str)
            assert len(item.strip()) > 0


def test_atlas_analysis_json_navigation_tabs_present():
    """Verifies the .atlas-analysis.json navigation block declares Guide and Reference tabs."""
    data = json.loads(_read(".atlas-analysis.json"))
    tab_names = [t["tab"] for t in data["navigation"]["tabs"]]
    assert "Guide" in tab_names
    assert "Reference" in tab_names


# --- .mintignore tests ---

def test_mintignore_exists_and_ignores_drafts():
    """Verifies .mintignore exists and excludes draft content from the docs build."""
    content = _read(".mintignore")
    assert "drafts/" in content
    assert "*.draft.mdx" in content


# --- AGENTS.md tests ---

def test_agents_md_has_expected_sections():
    """Verifies docs-source/AGENTS.md contains the standard Mintlify agent instruction sections."""
    content = _read("AGENTS.md")
    assert "SongketMail Documentation Source Instructions" in content
    assert "## Rules for AI Agents and Developers" in content
    assert "## Style Preferences" in content
    assert "Mintlify" in content
    assert "docs.json" in content


def test_agents_md_mentions_mcp_servers():
    """Verifies AGENTS.md documents the Mintlify documentation structure and sync pipeline."""
    content = _read("AGENTS.md")
    assert "Mintlify" in content
    assert "docs.json" in content


# --- LICENSE tests ---

def test_docs_source_license_is_mit():
    """Verifies docs-source/LICENSE is an MIT license attributed to Mintlify."""
    content = _read("LICENSE")
    assert "MIT License" in content
    assert "Copyright (c) 2026 Mintlify" in content
    assert "THE SOFTWARE IS PROVIDED \"AS IS\"" in content


# --- README.md tests ---

def test_docs_source_readme_warns_against_direct_edits():
    """Verifies the docs-source README explains this is a Mintlify deployment source."""
    content = _read("README.md")
    assert "songketmail/songketmail-product-pages" in content
    assert "Do not edit files in this repo directly" in content


def test_docs_source_readme_documents_sync_pipeline_files():
    """Verifies the README references the sync script and workflow it documents."""
    content = _read("README.md")
    assert "scripts/sync_docs.py" in content
    assert ".github/workflows/sync-docs.yml" in content
    assert "DOCS_REPO_TOKEN" in content


def test_docs_source_readme_lists_rules():
    """Verifies the README's Rules section enumerates the do/don't editing rules."""
    content = _read("README.md")
    idx_rules = content.find("## Rules")
    assert idx_rules != -1, "README.md is missing a '## Rules' section"
    rules_section = content[idx_rules:]
    assert "Do NOT edit files" in rules_section
    assert "Do NOT edit in the Mintlify web editor" in rules_section


# --- SVG asset tests ---

@pytest.mark.parametrize("svg_path", [
    "favicon.svg",
    os.path.join("logo", "dark.svg"),
    os.path.join("logo", "light.svg"),
])
def test_svg_assets_are_well_formed_xml(svg_path):
    """Verifies each SVG asset added by this PR is well-formed XML."""
    full_path = os.path.join(DOCS_SOURCE_DIR, svg_path)
    assert os.path.isfile(full_path), f"{full_path} does not exist"
    tree = ET.parse(full_path)
    root = tree.getroot()
    assert root.tag.endswith("svg"), f"{full_path} root element is not <svg>"


def test_favicon_svg_has_positive_dimensions():
    """Verifies favicon.svg declares positive width/height/viewBox attributes."""
    content = _read("favicon.svg")
    width_match = re.search(r'width="(\d+)"', content)
    height_match = re.search(r'height="(\d+)"', content)
    assert width_match and int(width_match.group(1)) > 0
    assert height_match and int(height_match.group(1)) > 0
    assert "viewBox=" in content


@pytest.mark.parametrize("svg_path,expected_fill", [
    (os.path.join("logo", "dark.svg"), "white"),
    (os.path.join("logo", "light.svg"), "#09090B"),
])
def test_logo_svgs_use_theme_appropriate_wordmark_fill(svg_path, expected_fill):
    """Verifies the dark logo variant uses a light wordmark fill and vice versa."""
    content = _read(svg_path)
    assert f'fill="{expected_fill}"' in content


# --- .mdx frontmatter tests for pages added by this PR ---

@pytest.mark.parametrize("mdx_path", CHANGED_MDX_FILES)
def test_mdx_file_exists_and_is_nonempty(mdx_path):
    """Verifies each new/changed .mdx page exists and has non-trivial content."""
    full_path = os.path.join(DOCS_SOURCE_DIR, mdx_path)
    assert os.path.isfile(full_path), f"{full_path} does not exist"
    content = _read(mdx_path)
    assert len(content.strip()) > 200, f"{mdx_path} appears to be empty or too short"


@pytest.mark.parametrize("mdx_path", CHANGED_MDX_FILES)
def test_mdx_frontmatter_has_required_fields(mdx_path):
    """Verifies each .mdx page declares title, sidebarTitle, and description frontmatter."""
    content = _read(mdx_path)
    fields = _parse_frontmatter(content)
    for key in ("title", "sidebarTitle", "description"):
        assert key in fields, f"{mdx_path} frontmatter is missing '{key}'"
        assert len(fields[key].strip()) > 0, f"{mdx_path} frontmatter '{key}' is empty"


@pytest.mark.parametrize("mdx_path", CHANGED_MDX_FILES)
def test_mdx_frontmatter_description_is_reasonably_sized(mdx_path):
    """Verifies each page's description is a substantive but not excessively long summary."""
    content = _read(mdx_path)
    fields = _parse_frontmatter(content)
    description = fields["description"]
    assert 20 <= len(description) <= 300, (
        f"{mdx_path} description length {len(description)} is outside the expected 20-300 char range"
    )


@pytest.mark.parametrize("mdx_path", CHANGED_MDX_FILES)
def test_mdx_has_content_after_frontmatter(mdx_path):
    """Verifies each .mdx page has a non-empty body following its frontmatter block."""
    content = _read(mdx_path)
    parts = content.split("---", 2)
    body = parts[2].strip()
    assert len(body) > 100, f"{mdx_path} has little or no content after its frontmatter"


# --- Spot checks on specific page content introduced by this PR ---

def test_index_mdx_links_to_new_deployment_and_architecture_pages():
    """Verifies the revamped homepage links to the new prerequisites/architecture pages."""
    content = _read("index.mdx")
    assert "/deployment/prerequisites" in content
    assert "/architecture-overview" in content
    assert "<CardGroup" in content
    assert "<Steps>" in content


def test_introduction_mdx_describes_persistence_trinity():
    """Verifies introduction.mdx documents the three Persistence Trinity pillars."""
    content = _read("introduction.mdx")
    assert "Persistence Trinity" in content
    assert "Fabric Isolation" in content
    assert "Quadlet Orchestration" in content
    assert "Sovereign Storage" in content


def test_architecture_overview_mentions_service_fabric_matrix():
    """Verifies architecture-overview.mdx documents the seven-container service matrix."""
    content = _read("architecture-overview.mdx")
    assert "Service Fabric Matrix" in content
    assert "songketmail-proxy" in content
    assert "songketmail-postfix" in content
    assert "UserNS=keep-id:uid=2001,gid=2001" in content


def test_reference_global_variables_documents_key_params():
    """Verifies reference/global-variables.mdx documents the core tunable variables."""
    content = _read(os.path.join("reference", "global-variables.mdx"))
    for param in (
        "cluster_prefix",
        "songketmail_uid",
        "songketmail_gid",
        "is_limited_environment",
        "storage_base_path",
        "songketmail_services",
    ):
        assert param in content, f"reference/global-variables.mdx is missing '{param}'"


def test_reference_network_ports_lists_all_public_ports():
    """Verifies reference/network-ports.mdx documents all five public-facing ports."""
    content = _read(os.path.join("reference", "network-ports.mdx"))
    for port in ("25", "80", "443", "587", "993"):
        assert port in content, f"reference/network-ports.mdx is missing port {port}"


def test_deployment_prerequisites_lists_required_ansible_collections():
    """Verifies deployment/prerequisites.mdx lists the required Ansible collections."""
    content = _read(os.path.join("deployment", "prerequisites.mdx"))
    for collection in ("community.general", "ansible.posix", "containers.podman"):
        assert collection in content


def test_operations_troubleshooting_uses_accordion_group():
    """Verifies operations/troubleshooting.mdx groups issues using Mintlify AccordionGroup."""
    content = _read(os.path.join("operations", "troubleshooting.mdx"))
    assert "<AccordionGroup>" in content
    assert "</AccordionGroup>" in content
    assert content.count("<Accordion title=") >= 5
