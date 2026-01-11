"""Navigation link extraction from HTML content using CSS selectors."""

import logging
import re
from typing import Optional
from urllib.parse import urljoin, urlparse

try:
    from bs4 import BeautifulSoup
except ImportError:
    raise ImportError(
        "BeautifulSoup4 is required for navigation extraction. "
        "Install it with: pip install beautifulsoup4"
    )


logger = logging.getLogger(__name__)


# Default CSS selector for VuePress-style left sidebar navigation
# This targets common VuePress sidebar class names
DEFAULT_NAVIGATION_SELECTOR = ".sidebar-nav"

# Fallback selectors to try if the default doesn't match
FALLBACK_SELECTORS = [
    ".sidebar-nav",  # VuePress 2.x
    ".sidebar-links",  # VuePress 1.x
    ".nav-links",  # Generic navigation
    "[class*='sidebar']",  # Any class containing 'sidebar'
    "[class*='nav']",  # Any class containing 'nav'
]


def extract_navigation_links(
    html_content: str,
    css_selector: Optional[str] = None,
    base_url: Optional[str] = None
) -> list[str]:
    """
    Extract navigation links from HTML content using CSS selector.

    Args:
        html_content: HTML content to parse
        css_selector: CSS selector for navigation element (uses DEFAULT_NAVIGATION_SELECTOR if None)
        base_url: Base URL for resolving relative links (optional)

    Returns:
        List of unique URLs found in navigation links

    Raises:
        ValueError: If navigation element not found
    """
    if not html_content:
        raise ValueError("HTML content is empty")

    soup = BeautifulSoup(html_content, "html.parser")

    # Try provided selector or defaults
    selectors_to_try = [css_selector] if css_selector else FALLBACK_SELECTORS
    selectors_to_try = [s for s in selectors_to_try if s]

    nav_element = None
    selector_used = None

    for selector in selectors_to_try:
        nav_element = soup.select_one(selector)
        if nav_element:
            selector_used = selector
            logger.debug(f"Found navigation element with selector: {selector}")
            break

    if not nav_element:
        available_classes = [cls for tag in soup.find_all(class_=True) for cls in tag.get("class", [])]
        raise ValueError(
            f"Navigation element not found. Tried selectors: {selectors_to_try}. "
            f"Available classes in HTML: {available_classes[:10]}"
        )

    # Extract all links from navigation element
    links = nav_element.find_all("a", href=True)
    urls = []

    for link in links:
        href = link.get("href", "").strip()
        if not href:
            continue

        # Resolve relative URLs if base_url provided
        if base_url and not href.startswith("http"):
            href = urljoin(base_url, href)

        urls.append(href)

    # Remove duplicates while preserving order
    seen = set()
    unique_urls = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)

    logger.info(f"Extracted {len(unique_urls)} unique navigation links using selector '{selector_used}'")
    return unique_urls


def filter_navigation_links(
    urls: list[str],
    allowed_base_path: str = "/VBA/"
) -> tuple[list[str], int]:
    """
    Filter URLs to only include those within allowed path boundary.

    Args:
        urls: List of URLs to filter
        allowed_base_path: URL path boundary (e.g., "/VBA/")

    Returns:
        Tuple of (filtered_urls, skipped_count)
    """
    filtered = []
    skipped = 0

    for url in urls:
        parsed = urlparse(url)
        path = parsed.path

        # Check if path starts with allowed base path
        if path.startswith(allowed_base_path):
            filtered.append(url)
        else:
            logger.debug(f"Filtered out URL outside boundary: {url}")
            skipped += 1

    logger.info(f"Filtered navigation links: {len(filtered)} allowed, {skipped} skipped")
    return filtered, skipped


def extract_and_filter_navigation(
    html_content: str,
    css_selector: Optional[str] = None,
    base_url: Optional[str] = None,
    allowed_base_path: str = "/VBA/"
) -> list[str]:
    """
    Extract navigation links and filter by allowed path in one step.

    Args:
        html_content: HTML content to parse
        css_selector: CSS selector for navigation element
        base_url: Base URL for resolving relative links
        allowed_base_path: URL path boundary for filtering

    Returns:
        List of filtered URLs within allowed path

    Raises:
        ValueError: If navigation element not found or no valid links after filtering
    """
    # Extract links
    all_urls = extract_navigation_links(html_content, css_selector, base_url)

    # Filter by path
    filtered_urls, skipped = filter_navigation_links(all_urls, allowed_base_path)

    if not filtered_urls:
        raise ValueError(
            f"No navigation links found within allowed path '{allowed_base_path}'. "
            f"Extracted {len(all_urls)} total links, {skipped} were filtered out."
        )

    return filtered_urls


def extract_links_from_markdown(
    markdown: str,
    base_url: str,
    allowed_base_path: str = "/VBA/"
) -> list[str]:
    """
    Extract all HTTP links from markdown content and filter by allowed path.

    This function finds URLs in markdown link syntax [text](url) and standalone URLs.
    It filters out anchor links (same page with different # fragments) to avoid duplicates.

    Args:
        markdown: Markdown content to parse
        base_url: Base URL for resolving relative links
        allowed_base_path: URL path boundary for filtering

    Returns:
        List of filtered URLs within allowed path (without anchor duplicates)

    Raises:
        ValueError: If no valid links found after filtering
    """
    if not markdown:
        raise ValueError("Markdown content is empty")

    # Pattern for markdown links: [text](url) and standalone HTTP(S) URLs
    # Matches: [text](url) and http:// or https:// URLs
    markdown_link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
    standalone_url_pattern = r'https?://[^\s\)]+'

    # Use a dictionary to track unique URLs (without fragments)
    url_dict = {}  # Maps URL without fragment to original URL (with first fragment seen)

    # Extract markdown links
    for match in re.finditer(markdown_link_pattern, markdown):
        url = match.group(2).strip()

        # Remove fragments
        url_without_fragment = url.split('#')[0] if '#' in url else url

        # Skip if empty or just a fragment
        if not url_without_fragment or url_without_fragment.startswith('#'):
            continue

        # Resolve relative URLs
        if not url_without_fragment.startswith('http'):
            url_without_fragment = urljoin(base_url, url_without_fragment)

        # Store the URL (keep the first occurrence if there are fragments)
        if url_without_fragment not in url_dict:
            url_dict[url_without_fragment] = url_without_fragment

    # Extract standalone URLs
    for match in re.finditer(standalone_url_pattern, markdown):
        url = match.group(0)
        url_without_fragment = url.split('#')[0] if '#' in url else url

        if url_without_fragment and url_without_fragment not in url_dict:
            url_dict[url_without_fragment] = url_without_fragment

    # Convert to list
    unique_urls = list(url_dict.keys())

    logger.info(f"Extracted {len(unique_urls)} unique page URLs from markdown (excluding anchor links)")

    # Filter by allowed path
    filtered_urls, skipped = filter_navigation_links(unique_urls, allowed_base_path)

    if not filtered_urls:
        raise ValueError(
            f"No links found within allowed path '{allowed_base_path}'. "
            f"Extracted {len(unique_urls)} total URLs, {skipped} were filtered out."
        )

    return filtered_urls
