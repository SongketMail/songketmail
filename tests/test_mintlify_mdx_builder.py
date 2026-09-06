#!/usr/bin/env python3
"""
tests/test_mintlify_mdx_builder.py - Unit test suite for tools/build_mintlify_mdx.py
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from tools import build_mintlify_mdx
except ImportError:
    import pytest
    pytest.skip("tools module not present in repository", allow_module_level=True)


def test_parse_frontmatter():
    content = "---\ntitle: 'Test Page'\ndescription: 'A test description'\n---\n\n# Body content"
    metadata, body = build_mintlify_mdx.parse_frontmatter(content)
    assert metadata["title"] == "Test Page"
    assert metadata["description"] == "A test description"
    assert body.strip() == "# Body content"


def test_convert_md_to_mdx(tmp_path):
    sample_md = tmp_path / "sample.md"
    sample_md.write_text("---\ntitle: 'Sample Title'\n---\n\n# Sample Heading\nSample text", encoding="utf-8")

    mdx_text, metadata = build_mintlify_mdx.convert_md_to_mdx(sample_md)
    assert "title: \"Sample Title\"" in mdx_text
    assert "# Sample Heading" in mdx_text
    assert metadata["title"] == "Sample Title"


def test_build_docs_json():
    pages_map = {
        "index": {"title": "Index"},
        "quickstart": {"title": "Quickstart"},
        "reference/network-ports": {"title": "Ports"}
    }
    config = build_mintlify_mdx.build_docs_json(pages_map)
    assert "$schema" in config
    assert "navigation" in config
    assert len(config["navigation"]) > 0
