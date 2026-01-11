#!/usr/bin/env python3
"""
Universal Documentation Auto Crawler

Automatically discovers and aggregates all documentation pages
under a given path into a single markdown file.

Examples:
    # Crawl all pages under /VBA/
    python auto_crawl.py --url https://dict.thinktrader.net/VBA/start.html

    # Crawl all pages under /help/
    python auto_crawl.py --url http://ptrade.local.com:7766/hub/help/api

    # Crawl all pages under /docs/
    python auto_crawl.py --url https://example.com/docs/introduction
"""

import argparse
import logging
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List
from urllib.parse import urlparse

import requests


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Configure logging."""
    logger = logging.getLogger("auto_crawler")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.handlers.clear()

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG if verbose else logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console.setFormatter(formatter)
    logger.addHandler(console)

    return logger


class PageDiscoverer:
    """Automatically discovers all pages under a given path."""

    def __init__(self, start_url: str):
        """
        Initialize the discoverer.

        Args:
            start_url: Starting URL for documentation
        """
        self.start_url = start_url
        self.parsed_url = urlparse(start_url)
        self.domain = f"{self.parsed_url.scheme}://{self.parsed_url.netloc}"

        # Extract base path from URL
        # Examples:
        #   /VBA/start.html -> /VBA/
        #   /hub/help/api -> /hub/help/
        #   /docs/introduction -> /docs/
        self.base_path = self._extract_base_path(self.parsed_url.path)

        logger = logging.getLogger("auto_crawler")
        logger.info(f"Detected base path: {self.base_path}")

    def _extract_base_path(self, path: str) -> str:
        """Extract the base documentation path from URL path."""
        # Remove trailing slash if present
        path = path.rstrip('/')

        # Get the directory path
        if '/' in path:
            # Get everything before the last slash
            base_path = path[:path.rfind('/') + 1]
        else:
            base_path = '/'

        return base_path

    def discover_all_pages(self) -> List[str]:
        """
        Automatically discover all pages under the base path.

        Returns:
            List of discovered page URLs
        """
        logger = logging.getLogger("auto_crawler")
        logger.info(f"Starting automatic page discovery for {self.base_path}*")

        # Method 1: Extract page references from HTML source
        urls = self._try_html_extraction()
        if urls and len(urls) > 1:
            logger.info(f"Found {len(urls)} pages via HTML extraction")
            return sorted(set(urls))

        # Method 2: Try sitemap
        urls = self._try_sitemap()
        if urls:
            logger.info(f"Found {len(urls)} pages via sitemap")
            return urls

        # Fallback: return start URL only
        logger.warning("Could not discover additional pages, using start URL only")
        return [self.start_url]

    def _try_html_extraction(self) -> List[str]:
        """Extract page references from HTML source."""
        try:
            response = requests.get(self.start_url, timeout=10)
            if response.status_code != 200:
                return []

            # Extract all links that match our base path pattern
            # Pattern: matches links like "/VBA/page.html", "/help/api.html", etc.
            # The pattern should match the base path followed by page names
            path_pattern = self.base_path.replace('/', r'\/')
            link_pattern = re.compile(r'["\'](' + path_pattern + r'[^"\']*)["\']')

            pages = set()
            for match in link_pattern.finditer(response.text):
                link_path = match.group(1)

                # Only include HTML pages
                if link_path.endswith('.html') or link_path.endswith('.htm'):
                    full_url = f"{self.domain}{link_path}"
                    pages.add(full_url)

            # Also add the start URL
            pages.add(self.start_url)

            if len(pages) > 1:
                return sorted(pages)

        except Exception as e:
            logger = logging.getLogger("auto_crawler")
            logger.debug(f"HTML extraction failed: {e}")

        return []

    def _try_sitemap(self) -> List[str]:
        """Try to extract URLs from sitemap.xml."""
        try:
            sitemap_urls = [
                f"{self.domain}/sitemap.xml",
                f"{self.domain}/sitemap_index.xml",
            ]

            for sitemap_url in sitemap_urls:
                try:
                    response = requests.get(sitemap_url, timeout=10)
                    if response.status_code == 200:
                        # Extract URLs matching our base path
                        path_pattern = self.base_path.replace('/', r'\/')
                        url_pattern = re.compile(r'<loc>([^<]*' + path_pattern + r'[^<]*)</loc>')
                        urls = url_pattern.findall(response.text)

                        if urls:
                            return sorted(set(urls))
                except Exception:
                    continue

        except Exception:
            pass

        return []


def scrape_and_aggregate(
    urls: List[str],
    base_path: str,
    output_file: str,
    api_base_url: str = "http://localhost:3002",
    api_key: str = "fc-test"
) -> dict:
    """Scrape all URLs and aggregate into markdown file."""
    # Import here to avoid circular imports
    sys.path.insert(0, str(Path(__file__).parent / "src"))
    from firecrawl_client import FirecrawlClient

    client = FirecrawlClient(api_base_url=api_base_url, api_key=api_key)
    all_markdown = []
    failed_urls = []

    # Add frontmatter
    frontmatter = f"""---
title: Documentation - Auto Aggregated
aggregated_at: {datetime.now().isoformat()}
total_pages: {len(urls)}
base_path: {base_path}
discovery_method: automatic_html_link_extraction
source_urls:
"""
    for url in urls:
        frontmatter += f"  - {url}\n"
    frontmatter += "---\n\n"
    frontmatter += f"# Documentation ({base_path})\n\n"
    frontmatter += "Automatically aggregated from documentation site.\n\n"
    frontmatter += f"Discovered {len(urls)} pages under {base_path} using automatic link extraction.\n\n"
    frontmatter += "---\n\n"

    all_markdown.append(frontmatter)

    logger = logging.getLogger("auto_crawler")
    logger.info(f"Scraping {len(urls)} documentation pages...")

    for i, url in enumerate(urls, 1):
        logger.info(f"[{i}/{len(urls)}] Scraping: {url}")

        try:
            response = client.scrape_url(url)

            if response.get("success"):
                data = response.get("data", {})
                markdown = data.get("markdown", "")
                title = data.get("metadata", {}).get("title", url)

                all_markdown.append(f"\n\n## {title}\n\n")
                all_markdown.append(f"*Source: {url}*\n\n")
                all_markdown.append(markdown)
                all_markdown.append("\n\n---\n")

                logger.info(f"  [OK] {len(markdown)} characters")
            else:
                error_msg = response.get("error", "Unknown error")
                logger.warning(f"  [FAIL] {error_msg}")
                failed_urls.append(url)

        except Exception as e:
            logger.error(f"  [ERROR] {e}")
            failed_urls.append(url)

        time.sleep(0.5)

    # Write output
    output_path = Path(output_file)
    output_path.write_text("".join(all_markdown), encoding="utf-8")

    successful = len(urls) - len(failed_urls)

    logger.info(f"\n[SUCCESS] Aggregated file created: {output_path}")
    logger.info(f"  Size: {output_path.stat().st_size / 1024:.1f} KB")
    logger.info(f"  Pages: {successful}/{len(urls)} successful")

    if failed_urls:
        logger.warning(f"  Failed: {failed_urls}")

    return {
        "discovered_urls": urls,
        "successful_pages": successful,
        "failed_pages": len(failed_urls),
        "output_file": str(output_path)
    }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Automatically discover and aggregate documentation pages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Crawl VBA documentation
  python auto_crawl.py --url https://dict.thinktrader.net/VBA/start.html

  # Crawl help documentation
  python auto_crawl.py --url http://ptrade.local.com:7766/hub/help/api

  # Crawl docs with custom output
  python auto_crawl.py --url https://example.com/docs/intro --output docs.md
        """
    )
    parser.add_argument(
        "--url",
        type=str,
        required=True,
        help="Starting URL (e.g., https://dict.thinktrader.net/VBA/start.html)"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output markdown file path (auto-generated based on path if not specified)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging"
    )

    args = parser.parse_args()
    logger = setup_logging(args.verbose)

    logger.info("=" * 70)
    logger.info("Universal Documentation Auto Crawler")
    logger.info("=" * 70)
    logger.info(f"Starting URL: {args.url}")
    logger.info("")

    try:
        # Initialize discoverer
        discoverer = PageDiscoverer(args.url)

        # Auto-generate output filename if not specified
        if not args.output:
            # Extract meaningful name from base path
            path_name = discoverer.base_path.strip('/').replace('/', '_')
            if not path_name:
                path_name = "documentation"
            args.output = f"{path_name}_aggregated.md"

        logger.info(f"Base path: {discoverer.base_path}")
        logger.info(f"Output file: {args.output}")
        logger.info("")

        # Discover all pages automatically
        urls = discoverer.discover_all_pages()

        logger.info(f"\nDiscovered URLs:")
        for i, url in enumerate(urls, 1):
            logger.info(f"  {i}. {url}")

        # Scrape and aggregate
        result = scrape_and_aggregate(urls, discoverer.base_path, args.output)

        # Print summary
        logger.info("")
        logger.info("=" * 70)
        logger.info("Summary")
        logger.info("=" * 70)
        logger.info(f"Base path: {discoverer.base_path}")
        logger.info(f"Total URLs discovered: {len(result['discovered_urls'])}")
        logger.info(f"Successfully scraped: {result['successful_pages']}")
        logger.info(f"Failed: {result['failed_pages']}")
        logger.info(f"Output: {result['output_file']}")

        if result['successful_pages'] > 0:
            logger.info("")
            logger.info("SUCCESS! All documentation has been aggregated.")
            return 0
        else:
            logger.error("FAILED! No pages were successfully scraped.")
            return 1

    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
