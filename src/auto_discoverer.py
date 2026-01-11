"""
Automatic VBA documentation discoverer and aggregator.

This module automatically discovers all VBA documentation pages
by extracting routes from JavaScript bundles, sitemap, or using
intelligent crawling.
"""

import re
import logging
from typing import List, Set
from urllib.parse import urljoin, urlparse

import requests

from .firecrawl_client import FirecrawlClient


logger = logging.getLogger(__name__)


class VBAPageDiscoverer:
    """Automatically discovers all VBA documentation pages."""

    def __init__(self, base_url: str = "https://dict.thinktrader.net/VBA/"):
        """
        Initialize the discoverer.

        Args:
            base_url: Base URL of VBA documentation
        """
        self.base_url = base_url
        self.domain = "https://dict.thinktrader.net"

    def discover_all_pages(self) -> List[str]:
        """
        Automatically discover all VBA documentation pages.

        Tries multiple methods in order:
        1. Extract from sitemap.xml
        2. Extract from JavaScript bundles
        3. Parse from page source with smart regex
        4. Fallback to crawl API

        Returns:
            List of discovered page URLs
        """
        logger.info("Starting automatic VBA page discovery...")

        # Method 1: Try sitemap
        urls = self._try_sitemap()
        if urls:
            logger.info(f"Found {len(urls)} pages via sitemap")
            return urls

        # Method 2: Extract from JavaScript bundles
        urls = self._try_javascript_bundles()
        if urls:
            logger.info(f"Found {len(urls)} pages via JavaScript bundles")
            return urls

        # Method 3: Parse from page source
        urls = self._try_page_source_parsing()
        if urls:
            logger.info(f"Found {len(urls)} pages via page source parsing")
            return urls

        # Method 4: Fallback to API-based discovery
        logger.warning("All automatic methods failed, using API-based discovery")
        return self._try_api_discovery()

    def _try_sitemap(self) -> List[str]:
        """Try to extract URLs from sitemap.xml."""
        try:
            sitemap_urls = [
                f"{self.domain}/sitemap.xml",
                f"{self.domain}/sitemap_index.xml",
                f"{self.domain}/sitemap1.xml",
            ]

            for sitemap_url in sitemap_urls:
                try:
                    logger.debug(f"Trying sitemap: {sitemap_url}")
                    response = requests.get(sitemap_url, timeout=10)
                    if response.status_code == 200:
                        # Extract all /VBA/ URLs from sitemap
                        urls = re.findall(r'<loc>([^<]*\/VBA\/[^<]*)</loc>', response.text)
                        if urls:
                            logger.info(f"Found {len(urls)} URLs in sitemap")
                            return sorted(set(urls))
                except Exception as e:
                    logger.debug(f"Sitemap {sitemap_url} failed: {e}")
                    continue

        except Exception as e:
            logger.debug(f"Sitemap extraction failed: {e}")

        return []

    def _try_javascript_bundles(self) -> List[str]:
        """Extract VBA page routes from JavaScript bundle filenames."""
        try:
            # Get the main page
            response = requests.get(self.base_url, timeout=10)
            if response.status_code != 200:
                return []

            # Extract all JavaScript bundle URLs
            js_files = re.findall(r'src="(/assets/[^"]*\.js)"', response.text)

            logger.debug(f"Found {len(js_files)} JavaScript bundles")

            # Extract page names from bundle filenames
            # Pattern: /assets/basic_syntax.html-abc123.js
            page_pattern = re.compile(r'/assets/([a-z_]+)\.html-[a-f0-9]+\.js')
            pages = set()

            for js_file in js_files:
                match = page_pattern.search(js_file)
                if match:
                    page_name = match.group(1)
                    # Skip common non-content pages
                    if page_name not in ['index', 'start_now']:
                        full_url = f"{self.domain}/VBA/{page_name}.html"
                        pages.add(full_url)

            # Always add the main page
            pages.add(f"{self.domain}/VBA/start_now.html")

            if len(pages) > 1:
                return sorted(pages)

        except Exception as e:
            logger.debug(f"JavaScript bundle extraction failed: {e}")

        return []

    def _try_page_source_parsing(self) -> List[str]:
        """Parse page source to find all VBA links using smart heuristics."""
        try:
            client = FirecrawlClient()
            response = client.scrape_url(self.base_url, include_html=True)

            if not response.get("success"):
                return []

            data = response.get("data", {})
            html_content = data.get("html", "")

            if not html_content:
                return []

            # Method 1: Look for router configuration or route definitions
            # VuePress typically has route info in scripts
            routes = self._extract_routes_from_scripts(html_content)
            if routes:
                return routes

            # Method 2: Look for navigation menu items
            routes = self._extract_from_navigation(html_content)
            if routes:
                return routes

            # Method 3: Look for all href="/VBA/*.html" patterns
            routes = self._extract_all_vba_links(html_content)
            if routes:
                return routes

        except Exception as e:
            logger.debug(f"Page source parsing failed: {e}")

        return []

    def _extract_routes_from_scripts(self, html: str) -> List[str]:
        """Extract routes from JavaScript code in HTML."""
        # Look for route definitions like "/VBA/basic_syntax"
        routes = set()

        # Pattern 1: VueRouter route definitions
        pattern1 = re.compile(r'["\'](/[A-Za-z]+/([a-z_]+))["\']')
        for match in pattern1.finditer(html):
            full_path = match.group(1)
            if full_path.startswith("/VBA/"):
                page_name = match.group(2)
                routes.add(f"{self.domain}{full_path}.html")

        # Pattern 2: Page references in JavaScript objects
        pattern2 = re.compile(r'["\']([a-z_]+\.html)["\']')
        for match in pattern2.finditer(html):
            page_name = match.group(1)
            if page_name != "index.html":
                routes.add(f"{self.domain}/VBA/{page_name}")

        return sorted(routes) if routes else []

    def _extract_from_navigation(self, html: str) -> List[str]:
        """Extract routes from navigation elements."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        routes = set()

        # Look for navigation links
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            # Match /VBA/*.html or /VBA/*/
            if re.match(r'^/VBA/[a-z_]+\.html$', href):
                routes.add(f"{self.domain}{href}")
            elif re.match(r'^/VBA/[a-z_]+/$', href):
                routes.add(f"{self.domain}{href}index.html")

        return sorted(routes) if routes else []

    def _extract_all_vba_links(self, html: str) -> List[str]:
        """Extract all VBA links using regex."""
        # Find all references to VBA pages
        pattern = re.compile(r'["\'](/VBA/[a-z_]+\.html)["\']')
        matches = pattern.findall(html)

        routes = set()
        for match in matches:
            routes.add(f"{self.domain}{match}")

        return sorted(routes) if routes else []

    def _try_api_discovery(self) -> List[str]:
        """Fallback: Use Firecrawl API for discovery."""
        try:
            client = FirecrawlClient()

            # Try map API
            result = client.map_url(self.base_url)
            if result.get("success"):
                urls = result.get("data", [])
                if len(urls) > 1:
                    return urls

            # If map fails, return at least the base URL
            return [self.base_url]

        except Exception as e:
            logger.error(f"API discovery failed: {e}")
            return [self.base_url]


def discover_and_aggregate_auto(
    base_url: str = "https://dict.thinktrader.net/VBA/start_now.html",
    output_file: str = "VBA_Documentation_Auto_Aggregated.md"
) -> dict:
    """
    Automatically discover all VBA pages and aggregate into one markdown file.

    Args:
        base_url: Starting URL
        output_file: Output markdown file path

    Returns:
        Dictionary with results:
            - discovered_urls: List of discovered URLs
            - successful_pages: Number of successfully scraped pages
            - failed_pages: Number of failed pages
            - output_file: Path to aggregated file
    """
    discoverer = VBAPageDiscoverer(base_url)

    # Discover all pages automatically
    urls = discoverer.discover_all_pages()

    logger.info(f"Automatically discovered {len(urls)} VBA pages")
    for i, url in enumerate(urls, 1):
        logger.info(f"  {i}. {url}")

    if not urls:
        logger.error("No pages discovered!")
        return {
            "discovered_urls": [],
            "successful_pages": 0,
            "failed_pages": 0,
            "output_file": None
        }

    # Scrape all discovered pages
    from .auto_aggregator import scrape_and_aggregate_urls

    return scrape_and_aggregate_urls(urls, output_file)
