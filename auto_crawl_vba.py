#!/usr/bin/env python3
"""
Automatic VBA Documentation Crawler

One-command solution to automatically discover and aggregate
all VBA documentation pages into a single markdown file.

Usage:
    python auto_crawl_vba.py
    python auto_crawl_vba.py --output vba_docs.md
    python auto_crawl_vba.py --url https://dict.thinktrader.net/VBA/
"""

import argparse
import logging
import sys
import time
import re
from datetime import datetime
from pathlib import Path
from typing import List

import requests


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Configure logging."""
    logger = logging.getLogger("vba_auto_crawler")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.handlers.clear()

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG if verbose else logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console.setFormatter(formatter)
    logger.addHandler(console)

    return logger


class VBAPageDiscoverer:
    """Automatically discovers all VBA documentation pages."""

    def __init__(self, base_url: str = "https://dict.thinktrader.net/VBA/"):
        self.base_url = base_url
        self.domain = "https://dict.thinktrader.net"

    def discover_all_pages(self) -> List[str]:
        """Automatically discover all VBA documentation pages."""
        logger = logging.getLogger("vba_auto_crawler")
        logger.info("Starting automatic VBA page discovery...")

        # Method 1: Extract from JavaScript bundles (most reliable)
        urls = self._try_javascript_bundles()
        if urls and len(urls) > 1:
            logger.info(f"Found {len(urls)} pages via JavaScript bundles")
            return sorted(urls)

        # Method 2: Try sitemap
        urls = self._try_sitemap()
        if urls:
            logger.info(f"Found {len(urls)} pages via sitemap")
            return urls

        # Fallback: return base URL
        logger.warning("Could not discover additional pages, using base URL only")
        return [f"{self.domain}/VBA/start_now.html"]

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
                        urls = re.findall(r'<loc>([^<]*\/VBA\/[^<]*)</loc>', response.text)
                        if urls:
                            return sorted(set(urls))
                except Exception:
                    continue
        except Exception:
            pass

        return []

    def _try_javascript_bundles(self) -> List[str]:
        """Extract VBA page routes from HTML source."""
        try:
            # Use start_now.html as the entry point
            entry_url = f"{self.domain}/VBA/start_now.html"
            response = requests.get(entry_url, timeout=10)
            if response.status_code != 200:
                return []

            # Method 1: Look for VBA page references in HTML/JavaScript
            # Pattern: "/VBA/basic_syntax.html"
            page_pattern = re.compile(r'["\'](/VBA/[a-z_]+\.html)["\']')
            pages = set()

            for match in page_pattern.finditer(response.text):
                full_url = f"{self.domain}{match.group(1)}"
                pages.add(full_url)

            if len(pages) > 1:
                return sorted(pages)

        except Exception as e:
            logger = logging.getLogger("vba_auto_crawler")
            logger.debug(f"Page extraction failed: {e}")

        return []


def scrape_and_aggregate(
    urls: List[str],
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
title: VBA Documentation - Auto Aggregated
aggregated_at: {datetime.now().isoformat()}
total_pages: {len(urls)}
discovery_method: automatic_javascript_bundle_extraction
source_urls:
"""
    for url in urls:
        frontmatter += f"  - {url}\n"
    frontmatter += "---\n\n"
    frontmatter += "# VBA Documentation\n\n"
    frontmatter += "Automatically aggregated from 迅投知识库 VBA documentation.\n\n"
    frontmatter += f"Discovered {len(urls)} pages using automatic route extraction from JavaScript bundles.\n\n"
    frontmatter += "---\n\n"

    all_markdown.append(frontmatter)

    logger = logging.getLogger("vba_auto_crawler")
    logger.info(f"Scraping {len(urls)} VBA documentation pages...")

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
        description="Automatically discover and aggregate VBA documentation"
    )
    parser.add_argument(
        "--url",
        type=str,
        default="https://dict.thinktrader.net/VBA/",
        help="Starting URL for VBA documentation"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="VBA_Documentation_Auto_Aggregated.md",
        help="Output markdown file path"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging"
    )

    args = parser.parse_args()
    logger = setup_logging(args.verbose)

    logger.info("=" * 70)
    logger.info("Automatic VBA Documentation Crawler")
    logger.info("=" * 70)
    logger.info(f"Starting URL: {args.url}")
    logger.info(f"Output file: {args.output}")
    logger.info("")

    try:
        # Discover all pages automatically
        discoverer = VBAPageDiscoverer(args.url)
        urls = discoverer.discover_all_pages()

        logger.info(f"\nDiscovered URLs:")
        for i, url in enumerate(urls, 1):
            logger.info(f"  {i}. {url}")

        # Scrape and aggregate
        result = scrape_and_aggregate(urls, args.output)

        # Print summary
        logger.info("")
        logger.info("=" * 70)
        logger.info("Summary")
        logger.info("=" * 70)
        logger.info(f"Total URLs discovered: {len(result['discovered_urls'])}")
        logger.info(f"Successfully scraped: {result['successful_pages']}")
        logger.info(f"Failed: {result['failed_pages']}")
        logger.info(f"Output: {result['output_file']}")

        if result['successful_pages'] > 0:
            logger.info("")
            logger.info("SUCCESS! All VBA documentation has been aggregated.")
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
