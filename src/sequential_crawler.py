"""Sequential crawler that follows VuePress page navigation links."""

import logging
from typing import List, Set
from urllib.parse import urljoin, urlparse

from .firecrawl_client import FirecrawlClient
from .models import ScrapedPage
from .config import CrawlConfig


logger = logging.getLogger(__name__)


def crawl_sequential_pages(
    start_url: str,
    client: FirecrawlClient,
    allowed_base_path: str = "/VBA/",
    max_pages: int = 200
) -> List[ScrapedPage]:
    """
    Crawl pages sequentially by following VuePress next/prev navigation links.

    This approach works well for VuePress SPAs where the "next" link
    leads to the next page in the documentation.

    Args:
        start_url: Starting URL
        client: FirecrawlClient instance
        allowed_base_path: URL path boundary (e.g., "/VBA/")
        max_pages: Maximum pages to crawl

    Returns:
        List of ScrapedPage objects
    """
    from bs4 import BeautifulSoup
    from datetime import datetime

    scraped_pages = []
    seen_urls: Set[str] = set()
    current_url = start_url

    while current_url and len(scraped_pages) < max_pages:
        if current_url in seen_urls:
            logger.warning(f"Already scraped {current_url}, stopping to avoid loop")
            break

        seen_urls.add(current_url)
        logger.info(f"[{len(scraped_pages) + 1}/{max_pages}] Scraping: {current_url}")

        # Scrape the current page
        try:
            response = client.scrape_url(current_url, include_html=True)

            if not response.get("success"):
                logger.error(f"Failed to scrape {current_url}")
                break

            data = response.get("data", {})
            page = ScrapedPage(
                url=current_url,
                source_url=current_url,
                markdown=data.get("markdown", ""),
                title=data.get("metadata", {}).get("title"),
                description=data.get("metadata", {}).get("description"),
                language=data.get("metadata", {}).get("language"),
                metadata=data.get("metadata", {})
            )
            scraped_pages.append(page)

            # Extract the "next" page link from HTML
            html_content = data.get("html", "")
            next_url = extract_next_page_link(html_content, current_url, allowed_base_path)

            if next_url:
                logger.info(f"Found next page: {next_url}")
                current_url = next_url
            else:
                logger.info("No next page link found, reached end of documentation")
                break

        except Exception as e:
            logger.error(f"Error scraping {current_url}: {e}")
            break

    logger.info(f"Sequential crawl completed: {len(scraped_pages)} pages scraped")
    return scraped_pages


def extract_next_page_link(html_content: str, base_url: str, allowed_base_path: str) -> str:
    """
    Extract the "next page" link from VuePress navigation.

    VuePress typically has navigation like:
    <nav class="page-nav">
      <span class="next"><a href="/VBA/next_page.html">Next Page Title</a></span>
    </nav>

    Args:
        html_content: HTML content to parse
        base_url: Base URL for resolving relative links
        allowed_base_path: URL path boundary

    Returns:
        Next page URL or None if not found
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_content, "html.parser")

    # Look for VuePress next page link
    next_link = soup.select_one(".page-nav .next a")

    if next_link and next_link.get("href"):
        href = next_link.get("href")
        full_url = urljoin(base_url, href)

        # Check if within allowed path
        if allowed_base_path in full_url:
            # Remove any fragments
            base_url_only = full_url.split('#')[0] if '#' in full_url else full_url
            return base_url_only

    return None
