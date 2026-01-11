"""Main crawler orchestration logic."""

import logging
import re
from pathlib import Path
from typing import Optional

from .config import CrawlConfig
from .models import ScrapedPage, MarkdownFile, CrawlResult, AggregatedMarkdownFile
from .firecrawl_client import FirecrawlClient
from .file_writer import write_markdown_file, write_aggregated_file


logger = logging.getLogger(__name__)


def detect_vuejs_content(html_content: str) -> bool:
    """
    Detect if HTML content contains Vue.js markers.

    Checks for common Vue.js indicators:
    - data-v- attributes (scoped CSS)
    - v-if, v-for, v-bind directives
    - Vue.js CDN links or script tags
    - __vue__ or Vue.$root in scripts

    Args:
        html_content: HTML content to analyze

    Returns:
        True if Vue.js markers are detected, False otherwise
    """
    if not html_content:
        return False

    # Check for Vue.js scoped CSS attributes
    if re.search(r'data-v-[a-f0-9]+', html_content):
        return True

    # Check for Vue.js directives
    if re.search(r'\bv-(?:if|for|bind|on|else|else-if|show|hide|model|text|html)\b', html_content):
        return True

    # Check for Vue.js CDN or script tags
    if re.search(r'vue[\.\-]?[0-9]*\.js', html_content, re.IGNORECASE):
        return True

    # Check for Vue-specific patterns
    if re.search(r'__vue__|Vue\.\$root|new Vue\(', html_content):
        return True

    # Check for Vue app mounting points
    if re.search(r'id="app"|id=\\"app\\"', html_content):
        return True

    return False


def scrape_single_page(config: CrawlConfig) -> CrawlResult:
    """
    Scrape a single page and save to Markdown file.

    Args:
        config: Crawl configuration

    Returns:
        CrawlResult with scrape results
    """
    result = CrawlResult(config=config)
    result.started_at = datetime.now()

    try:
        client = FirecrawlClient(
            api_base_url=config.api_base_url,
            api_key=config.api_key,
            timeout_seconds=config.timeout_seconds
        )

        logger.info(f"Scraping single page: {config.start_url}")

        response = client.scrape_url(config.start_url)

        if not response.get("success"):
            error_msg = response.get("error", "Unknown error")
            logger.error(f"Scrape failed: {error_msg}")
            result.add_error(f"Failed to scrape {config.start_url}: {error_msg}")

            page = ScrapedPage(
                url=config.start_url,
                source_url=config.start_url,
                markdown="",
                success=False,
                error_message=error_msg
            )
            result.add_page(page)
            result.completed_at = datetime.now()
            return result

        # Create page from response data
        data = response.get("data", {})
        page_data = {
            "markdown": data.get("markdown", ""),
            "metadata": data.get("metadata", {})
        }

        page = _create_page_from_data(page_data, url=config.start_url)
        result.add_page(page)

        if page.success:
            markdown_file = MarkdownFile.from_scraped_page(page, config.output_dir)
            success = write_markdown_file(markdown_file, overwrite=config.overwrite_existing)

            if success:
                result.files_created.append(markdown_file)
            else:
                result.add_error(f"Failed to write file for {config.start_url}")

        result.completed_at = datetime.now()

    except Exception as e:
        logger.error(f"Unexpected error during scrape: {e}")
        result.add_error(f"Unexpected error: {e}")
        result.completed_at = datetime.now()

    return result


# Import datetime for result timestamp
from datetime import datetime


def filter_allowed_pages(api_results: list, allowed_base_path: str = "/VBA/") -> tuple[list[dict], int]:
    """
    Filter API results to only include pages within allowed boundary.

    Args:
        api_results: List of page dictionaries from Firecrawl API
        allowed_base_path: URL path boundary (e.g., "/VBA/")

    Returns:
        Tuple of (filtered_pages, skipped_count)
    """
    from .url_utils import is_allowed_url

    filtered = []
    skipped = 0

    for page_data in api_results:
        url = page_data.get("metadata", {}).get("sourceURL") or page_data.get("url", "")

        if is_allowed_url(url, allowed_base_path):
            filtered.append(page_data)
        else:
            logger.debug(f"Filtered out URL outside boundary: {url}")
            skipped += 1

    logger.info(f"Filtered pages: {len(filtered)} allowed, {skipped} skipped")
    return filtered, skipped


def deduplicate_urls(api_results: list) -> tuple[list[dict], int]:
    """
    Remove duplicate URLs from API results.

    Args:
        api_results: List of page dictionaries from Firecrawl API

    Returns:
        Tuple of (deduplicated_pages, duplicate_count)
    """
    seen = set()
    deduplicated = []
    duplicates = 0

    for page_data in api_results:
        url = page_data.get("metadata", {}).get("sourceURL") or page_data.get("url", "")

        if url not in seen:
            seen.add(url)
            deduplicated.append(page_data)
        else:
            logger.debug(f"Skipping duplicate URL: {url}")
            duplicates += 1

    if duplicates > 0:
        logger.info(f"Removed {duplicates} duplicate URLs")

    return deduplicated, duplicates


def _process_crawl_results(api_results: list, config: CrawlConfig) -> CrawlResult:
    """
    Process crawl job results and write files.

    Args:
        api_results: Raw page data from Firecrawl API
        config: Crawl configuration

    Returns:
        CrawlResult with processed pages
    """
    result = CrawlResult(config=config)

    # Filter by boundary
    filtered_pages, skipped_boundary = filter_allowed_pages(
        api_results,
        config.allowed_base_path
    )

    # Deduplicate URLs
    unique_pages, skipped_duplicates = deduplicate_urls(filtered_pages)

    result.skipped_pages = skipped_boundary + skipped_duplicates

    # Process each page
    for page_data in unique_pages:
        page = _create_page_from_data(page_data)
        result.add_page(page)

        # Write to disk if successful
        if page.success:
            markdown_file = MarkdownFile.from_scraped_page(page, config.output_dir)
            success = write_markdown_file(markdown_file, overwrite=config.overwrite_existing)

            if success:
                result.files_created.append(markdown_file)
                logger.info(f"Created file: {markdown_file.relative_path}")
            else:
                result.add_error(f"Failed to write file for {page.url}")

    return result


def _create_page_from_data(page_data: dict, url: Optional[str] = None) -> ScrapedPage:
    """
    Create ScrapedPage from API data.

    Args:
        page_data: Page dictionary from Firecrawl API
        url: Optional URL override (use for single-page scrape)

    Returns:
        ScrapedPage instance
    """
    metadata = page_data.get("metadata", {})
    page_url = url or (metadata.get("sourceURL") or page_data.get("url", ""))
    markdown = page_data.get("markdown", "")

    page = ScrapedPage(
        url=page_url,
        source_url=page_url,
        markdown=markdown,
        title=metadata.get("title"),
        description=metadata.get("description"),
        language=metadata.get("language"),
        metadata=metadata
    )

    if not page.has_valid_content:
        logger.warning(f"Page has no valid content: {page_url}")
        page.success = False
        page.error_message = "No valid content"

    return page


def crawl_multiple_pages(config: CrawlConfig) -> CrawlResult:
    """
    Crawl multiple pages starting from config URL.

    Args:
        config: Crawl configuration

    Returns:
        CrawlResult with multi-page crawl results
    """
    result = CrawlResult(config=config)
    result.started_at = datetime.now()

    try:
        client = FirecrawlClient(
            api_base_url=config.api_base_url,
            api_key=config.api_key,
            timeout_seconds=config.timeout_seconds
        )

        logger.info(f"Starting multi-page crawl from: {config.start_url}")

        # Submit crawl job
        submit_response = client.submit_crawl_job(
            url=config.start_url,
            limit=config.max_pages
        )

        if not submit_response.get("id"):
            error_msg = "Failed to submit crawl job"
            logger.error(error_msg)
            result.add_error(error_msg)
            result.completed_at = datetime.now()
            return result

        job_id = submit_response["id"]

        # Poll for job completion
        final_response = client.poll_crawl_job(
            job_id=job_id,
            poll_interval=5,
            max_polls=config.timeout_seconds // 5
        )

        # Check final status
        if final_response.get("status") != "completed":
            error_msg = final_response.get("error", "Crawl job failed")
            logger.error(f"Crawl job failed: {error_msg}")
            result.add_error(f"Crawl job failed: {error_msg}")
            result.completed_at = datetime.now()
            return result

        # Extract and process page data
        api_results = final_response.get("data", [])
        logger.info(f"Job completed with {len(api_results)} pages")

        process_result = _process_crawl_results(api_results, config)

        # Merge process result into main result
        result.pages_scraped = process_result.pages_scraped
        result.files_created = process_result.files_created
        result.total_pages = process_result.total_pages
        result.successful_pages = process_result.successful_pages
        result.failed_pages = process_result.failed_pages
        result.skipped_pages = process_result.skipped_pages
        result.errors = process_result.errors

        result.completed_at = datetime.now()
        logger.info(f"Crawl completed: {result.successful_pages} successful, {result.failed_pages} failed")

    except TimeoutError as e:
        logger.error(f"Crawl job timed out: {e}")
        result.add_error(f"Crawl timed out: {e}")
        result.completed_at = datetime.now()

    except Exception as e:
        logger.error(f"Unexpected error during crawl: {e}")
        result.add_error(f"Unexpected error: {e}")
        result.completed_at = datetime.now()

    return result


def scrape_with_aggregation(config: CrawlConfig) -> CrawlResult:
    """
    Scrape a page and aggregate content from all navigation links into a single Markdown file.

    This function:
    1. Discovers all pages using map API or crawl API
    2. Filters discovered pages to only include /VBA/ path URLs
    3. Scrapes each discovered page
    4. Aggregates all content into a single Markdown file

    Discovery method (config.discovery_mode):
    - "map" (default): Uses Firecrawl map API for comprehensive page discovery
    - "crawl": Uses crawl API for recursive link following

    Args:
        config: Crawl configuration with aggregate_navigation=True

    Returns:
        CrawlResult with aggregated page results
    """
    result = CrawlResult(config=config)
    result.started_at = datetime.now()

    try:
        client = FirecrawlClient(
            api_base_url=config.api_base_url,
            api_key=config.api_key,
            timeout_seconds=config.timeout_seconds
        )

        logger.info(f"Starting aggregation mode from: {config.start_url}")
        logger.info(f"Discovery mode: {config.discovery_mode}")

        # Discover pages using the configured method
        unique_pages = None
        use_sequential_crawl = False

        if config.discovery_mode == "map":
            # Try map API first
            logger.info("Using map API for comprehensive page discovery...")
            try:
                map_response = client.map_url(config.start_url)

                if map_response.get("success"):
                    # Map API returns links directly
                    map_links = map_response.get("data", [])

                    # Convert map links to page data format
                    # Map API returns a list of URLs, convert to page_data format
                    api_results = []
                    for link in map_links:
                        if isinstance(link, str):
                            api_results.append({"url": link})
                        elif isinstance(link, dict):
                            api_results.append(link)

                    logger.info(f"Map API discovered {len(api_results)} pages")

                    # If map API only found 1 page, use sequential crawl instead
                    if len(api_results) <= 1:
                        logger.info("Map API only found 1 page, using sequential crawl for VuePress sites...")
                        use_sequential_crawl = True
                    else:
                        # Filter and deduplicate pages
                        filtered_pages, skipped_boundary = filter_allowed_pages(
                            api_results,
                            config.allowed_base_path
                        )
                        unique_pages, skipped_duplicates = deduplicate_urls(filtered_pages)

                        result.skipped_pages = skipped_boundary + skipped_duplicates
                        logger.info(f"Filtered to {len(unique_pages)} unique pages within {config.allowed_base_path}")
                else:
                    # Map API failed, try sequential crawl
                    error_msg = map_response.get("error", "Unknown map API error")
                    logger.warning(f"Map API failed: {error_msg}")
                    logger.info("Falling back to sequential crawl...")
                    use_sequential_crawl = True

            except Exception as e:
                # Map API threw exception, try sequential crawl
                logger.warning(f"Map API error: {e}, falling back to sequential crawl...")
                use_sequential_crawl = True

        # Use sequential crawler for VuePress sites
        if use_sequential_crawl:
            from .sequential_crawler import crawl_sequential_pages

            logger.info("Using sequential crawl to follow VuePress navigation links...")
            scraped_pages = crawl_sequential_pages(
                start_url=config.start_url,
                client=client,
                allowed_base_path=config.allowed_base_path,
                max_pages=config.max_pages
            )

            if scraped_pages:
                # Convert scraped pages to the expected format
                for page in scraped_pages:
                    result.add_page(page)

                # Skip scraping step since we already scraped during discovery
                unique_pages = []  # Skip the scraping loop below
                result.skipped_pages = 0

        # Fallback: Use crawl API if map failed or mode is "crawl"
        if unique_pages is None:
            logger.info("Using crawl API for page discovery...")

            # Submit crawl job to discover all pages
            submit_response = client.submit_crawl_job(
                url=config.start_url,
                limit=config.max_pages
            )

            if not submit_response.get("id"):
                error_msg = "Failed to submit crawl job for page discovery"
                logger.error(error_msg)
                result.add_error(error_msg)
                result.completed_at = datetime.now()
                return result

            job_id = submit_response["id"]
            logger.info(f"Crawl job submitted: {job_id}")

            # Poll for job completion
            final_response = client.poll_crawl_job(
                job_id=job_id,
                poll_interval=5,
                max_polls=config.timeout_seconds // 5
            )

            # Check final status
            if final_response.get("status") != "completed":
                error_msg = final_response.get("error", "Crawl job failed")
                logger.error(f"Crawl job failed: {error_msg}")
                result.add_error(f"Crawl job failed: {error_msg}")
                result.completed_at = datetime.now()
                return result

            # Extract and process page data
            api_results = final_response.get("data", [])
            logger.info(f"Job completed with {len(api_results)} pages discovered")

            # Filter and deduplicate pages
            filtered_pages, skipped_boundary = filter_allowed_pages(
                api_results,
                config.allowed_base_path
            )
            unique_pages, skipped_duplicates = deduplicate_urls(filtered_pages)

            result.skipped_pages = skipped_boundary + skipped_duplicates
            logger.info(f"Filtered to {len(unique_pages)} unique pages within {config.allowed_base_path}")

        if not unique_pages and not use_sequential_crawl:
            error_msg = f"No pages found within allowed path '{config.allowed_base_path}'"
            logger.error(error_msg)
            result.add_error(error_msg)
            result.completed_at = datetime.now()
            return result

        # Step 2: Scrape each discovered page (skip if already scraped via sequential crawl)
        scraped_pages = []
        failed_urls = []

        # If we used sequential crawl, pages are already scraped
        if use_sequential_crawl:
            # Extract scraped pages from result
            scraped_pages = [p for p in result.pages_scraped if p.success]
            failed_urls = [p.url for p in result.pages_scraped if not p.success]
            logger.info(f"Sequential crawl completed: {len(scraped_pages)} successful, {len(failed_urls)} failed")
        elif unique_pages:
            # Scrape each discovered page
            logger.info(f"Scraping {len(unique_pages)} discovered pages...")

            for i, page_data in enumerate(unique_pages, 1):
                url = page_data.get("metadata", {}).get("sourceURL") or page_data.get("url", "")
                logger.info(f"[{i}/{len(unique_pages)}] Scraping: {url}")

                try:
                    response = client.scrape_url(url)

                    if response.get("success"):
                        page = _create_page_from_data(response.get("data", {}), url=url)
                        scraped_pages.append(page)
                        result.add_page(page)
                        logger.info(f"  Successfully scraped: {url}")
                    else:
                        error_msg = response.get("error", "Unknown error")
                        logger.warning(f"  Failed to scrape {url}: {error_msg}")
                        failed_urls.append(url)
                        result.add_error(f"Failed to scrape {url}: {error_msg}")

                        page = ScrapedPage(
                            url=url,
                            source_url=url,
                            markdown="",
                            success=False,
                            error_message=error_msg
                        )
                        result.add_page(page)

                except Exception as e:
                    logger.warning(f"  Error scraping {url}: {e}")
                    failed_urls.append(url)
                    result.add_error(f"Error scraping {url}: {e}")

                    page = ScrapedPage(
                        url=url,
                        source_url=url,
                        markdown="",
                        success=False,
                        error_message=str(e)
                    )
                    result.add_page(page)

        # Step 3: Create aggregated markdown file
        if scraped_pages:
            logger.info(f"Creating aggregated file from {len(scraped_pages)} successfully scraped pages...")
            try:
                # Log optimization settings
                if config.include_toc:
                    logger.info(f"Table of contents generation enabled (max_level={config.toc_max_level})")
                else:
                    logger.info("Table of contents generation disabled")

                if config.normalize_headings:
                    logger.info("Heading normalization enabled")
                else:
                    logger.info("Heading normalization disabled")

                # Detect Vue.js content
                vuejs_detected = False
                for page in scraped_pages:
                    html_content = page.html or page.metadata.get("html", "")
                    if html_content and detect_vuejs_content(html_content):
                        vuejs_detected = True
                        logger.info(f"Detected Vue.js content in page: {page.url}")
                        break

                if vuejs_detected:
                    logger.info("Vue.js rendering detected - Firecrawl JavaScript rendering is enabled by default")

                aggregated_file = AggregatedMarkdownFile.from_pages(
                    base_url=config.start_url,
                    pages=scraped_pages,
                    output_dir=config.output_dir,
                    failed_urls=failed_urls,
                    include_toc=config.include_toc,
                    normalize_headings=config.normalize_headings,
                    toc_max_level=config.toc_max_level,
                    vuejs_content=vuejs_detected
                )

                # Log optimization results
                if config.normalize_headings and aggregated_file.headings_normalized > 0:
                    logger.info(f"Normalized {aggregated_file.headings_normalized} headings")
                if config.include_toc:
                    logger.info(f"Table of contents added with max_level={config.toc_max_level}")

                # Step 5: Write aggregated file
                success = write_aggregated_file(
                    aggregated_file,
                    overwrite=config.overwrite_existing
                )

                if success:
                    result.aggregated_files.append(aggregated_file)
                    logger.info(f"Aggregated file created: {aggregated_file.relative_path}")
                else:
                    result.add_error(f"Failed to write aggregated file: {aggregated_file.relative_path}")

            except Exception as e:
                logger.error(f"Failed to create aggregated file: {e}")
                result.add_error(f"Failed to create aggregated file: {e}")
        else:
            logger.warning("No pages were successfully scraped, cannot create aggregated file")
            result.add_error("No pages were successfully scraped")

        result.completed_at = datetime.now()
        logger.info(f"Aggregation completed: {len(scraped_pages)} successful, {len(failed_urls)} failed")

    except Exception as e:
        logger.error(f"Unexpected error during aggregation: {e}")
        result.add_error(f"Unexpected error: {e}")
        result.completed_at = datetime.now()

    return result
