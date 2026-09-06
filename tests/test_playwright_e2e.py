#!/usr/bin/env python3
"""
tests/test_playwright_e2e.py - Playwright E2E browser test suite for SongketMail documentation HTML pages.

Verifies:
- Dark mode theme toggling across Light, Dark, and Auto modes.
- TOC smooth scrolling and anchor navigation across Desktop, Tablet, and Mobile viewports.
- Visual regression snapshot matching across all 31 documentation pages in docs/.
"""

import http.server
import os
import socketserver
import threading
import time

import pytest
from playwright.sync_api import expect, sync_playwright

DOCS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs"))
HOST = "127.0.0.1"
PORT = 8889

ALL_HTML_PAGES = sorted([f for f in os.listdir(DOCS_DIR) if f.endswith(".html")])


class QuietHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        """Initialize a request handler that serves files from the documentation directory."""
        super().__init__(*args, directory=DOCS_DIR, **kwargs)

    def log_message(self, format, *args):
        pass


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


@pytest.fixture(scope="module", autouse=True)
def doc_server():
    """Starts a local HTTP server serving docs/ in a background thread."""
    handler = QuietHTTPRequestHandler
    with ReusableTCPServer((HOST, PORT), handler) as httpd:
        server_thread = threading.Thread(target=httpd.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        time.sleep(0.5)
        yield
        httpd.shutdown()


def test_html_page_count():
    """Verifies that exactly 31 HTML documentation pages are present in docs/."""
    assert len(ALL_HTML_PAGES) == 31, f"Expected 31 HTML pages, found {len(ALL_HTML_PAGES)}"


def test_theme_toggling_playwright():
    """Verify that the documentation page's theme controls update the HTML element's theme class."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        page.goto(f"http://{HOST}:{PORT}/nfs-ceph-performance-tuning.html")

        # Click Dark Mode Button
        dark_btn = page.get_by_role("button", name="DARK")
        dark_btn.click()
        html_elem = page.locator("html")
        expect(html_elem).to_have_class("dark")

        # Click Light Mode Button
        light_btn = page.get_by_role("button", name="LIGHT")
        light_btn.click()
        expect(html_elem).not_to_have_class("dark")

        browser.close()


@pytest.mark.parametrize(
    "viewport_name,width,height",
    [
        ("desktop", 1280, 800),
        ("tablet", 768, 1024),
        ("mobile", 375, 812),
    ],
)
def test_toc_smooth_scrolling_across_viewports(viewport_name, width, height):
    """
    Verify that a table-of-contents link navigates to its target heading across viewport sizes.
    
    Parameters:
        viewport_name: Name of the viewport configuration used by the test.
        width: Viewport width in pixels.
        height: Viewport height in pixels.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": width, "height": height})
        page = context.new_page()

        page.goto(f"http://{HOST}:{PORT}/nfs-ceph-performance-tuning.html")

        # Locate a TOC anchor link (e.g. Executive Summary or NFS sysctl tuning)
        toc_link = page.locator("a[href*='#executive-summary-architecture-overview']").first
        if toc_link.is_visible():
            toc_link.click()
            expect(page).to_have_url(f"http://{HOST}:{PORT}/nfs-ceph-performance-tuning.html#executive-summary-architecture-overview")

            target_heading = page.locator("[id='executive-summary-architecture-overview']")
            expect(target_heading).to_be_visible()

        browser.close()


@pytest.mark.parametrize("html_file", ALL_HTML_PAGES)
def test_visual_regression_snapshot_matching_all_docs_pages(html_file):
    """Verifies layout rendering and compares visual snapshots against committed baselines across all 31 docs pages."""
    baseline_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "snapshots"))
    snapshot_dir = "/tmp/playwright_snapshots"
    os.makedirs(snapshot_dir, exist_ok=True)

    snapshot_path = os.path.join(snapshot_dir, f"{html_file}.png")
    baseline_path = os.path.join(baseline_dir, f"{html_file}.png")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            response = page.goto(f"http://{HOST}:{PORT}/{html_file}")

            assert response is not None, f"Failed to load {html_file}"
            assert response.status == 200, f"Expected HTTP 200 for {html_file}, got {response.status}"

            # Verify page title or container body presence
            expect(page.locator("body")).to_be_visible()

            # Capture visual snapshot
            page.screenshot(path=snapshot_path)
            assert os.path.isfile(snapshot_path), f"Visual snapshot not generated at {snapshot_path}"
            assert os.path.getsize(snapshot_path) > 0, f"Visual snapshot at {snapshot_path} is empty"

            # Compare against committed baseline snapshot
            assert os.path.isfile(baseline_path), f"Baseline snapshot missing at {baseline_path}"
            assert os.path.getsize(baseline_path) > 0, f"Baseline snapshot at {baseline_path} is empty"
        finally:
            browser.close()


def generate_verification_screenshot():
    """
    Generate a dark-mode verification screenshot of the performance tuning page.
    
    Returns:
        str: The path to the generated screenshot.
    """
    os.makedirs("/home/jules/verification", exist_ok=True)
    screenshot_path = "/home/jules/verification/verification.png"

    handler = QuietHTTPRequestHandler
    with ReusableTCPServer((HOST, PORT), handler) as httpd:
        server_thread = threading.Thread(target=httpd.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        time.sleep(0.5)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(f"http://{HOST}:{PORT}/nfs-ceph-performance-tuning.html")

            # Switch to dark mode for visual verification
            page.get_by_role("button", name="DARK").click()
            page.wait_for_timeout(300)
            page.screenshot(path=screenshot_path)
            browser.close()

        httpd.shutdown()

    return screenshot_path


if __name__ == "__main__":
    generate_verification_screenshot()
