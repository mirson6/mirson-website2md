"""
Automatic aggregator for VBA documentation.

Scraps discovered URLs and aggregates them into a single markdown file.
"""

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import List

from .firecrawl_client import FirecrawlClient


logger = logging.getLogger(__name__)


def scrape_and_aggregate_urls(
    urls: List[str],
    output_file: str = "VBA_Documentation_Auto_Aggregated.md"
) -> dict:
    """
    Scrape all discovered URLs and aggregate into one markdown file.

    Args:
        urls: List of URLs to scrape
        output_file: Output markdown file path

    Returns:
        Dictionary with results
    """
    client = FirecrawlClient()
    all_markdown = []
    failed_urls = []

    # Add frontmatter
    frontmatter = f"""---
title: VBA Documentation - Auto Aggregated
aggregated_at: {datetime.now().isoformat()}
total_pages: {len(urls)}
discovery_method: automatic
source_urls:
"""
    for url in urls:
        frontmatter += f"  - {url}\n"
    frontmatter += "---\n\n"
    frontmatter += "# VBA Documentation\n\n"
    frontmatter += "Automatically aggregated from 迅投知识库 VBA documentation.\n\n"
    frontmatter += f"Discovered {len(urls)} pages using automatic route extraction.\n\n"
    frontmatter += "---\n\n"

    all_markdown.append(frontmatter)

    logger.info(f"Scraping {len(urls)} VBA documentation pages...")

    for i, url in enumerate(urls, 1):
        logger.info(f"[{i}/{len(urls)}] Scraping: {url}")

        try:
            response = client.scrape_url(url)

            if response.get("success"):
                data = response.get("data", {})
                markdown = data.get("markdown", "")
                title = data.get("metadata", {}).get("title", url)

                # Add section
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

        # Small delay between requests to be respectful
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
