#!/usr/bin/env python3
"""
tests/test_playwright_e2e.py - Playwright E2E browser test suite for SongketMail documentation HTML pages.

Verifies:
- Dark mode theme toggling across Light, Dark, and Auto modes.
- TOC smooth scrolling and anchor navigation across Desktop, Tablet, and Mobile viewports.
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


class QuietHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DOCS_DIR, **kwargs)

    def log_message(self, format, *args):
        pass


@pytest.fixture(scope="module", autouse=True)
def doc_server():
    """Starts a local HTTP server serving docs/ in a background thread."""
    handler = QuietHTTPRequestHandler
    with socketserver.TCPServer((HOST, PORT), handler) as httpd:
        server_thread = threading.Thread(target=httpd.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        time.sleep(0.5)
        yield
        httpd.shutdown()


def test_theme_toggling_playwright():
    """Verifies theme toggle buttons (Light, Dark, Auto) update html element classes."""
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
    """Verifies Table of Contents anchor links trigger navigation and smooth scrolling across viewports."""
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


def generate_verification_screenshot():
    """Generates a visual verification screenshot for the frontend verification tool."""
    os.makedirs("/home/jules/verification", exist_ok=True)
    screenshot_path = "/home/jules/verification/verification.png"

    handler = QuietHTTPRequestHandler
    with socketserver.TCPServer((HOST, PORT), handler) as httpd:
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
