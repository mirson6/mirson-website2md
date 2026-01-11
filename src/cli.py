"""Command-line interface for VBA documentation crawler."""

import argparse
import logging
import sys
from pathlib import Path

from .config import CrawlConfig
from .crawler import scrape_single_page, crawl_multiple_pages, scrape_with_aggregation


def setup_logging(verbose: bool = False) -> logging.Logger:
    """
    Configure logging for the crawler.

    Args:
        verbose: Enable DEBUG level logging

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("vba_crawler")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    # Clear existing handlers
    logger.handlers.clear()

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG if verbose else logging.INFO)

    # Formatter with context
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console.setFormatter(formatter)
    logger.addHandler(console)

    return logger


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Crawl VBA documentation and convert to Markdown"
    )

    parser.add_argument(
        "--url",
        type=str,
        required=True,
        help="Starting URL (must be within https://dict.thinktrader.net/VBA/)"
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="./output",
        help="Output directory for Markdown files (default: ./output)"
    )

    parser.add_argument(
        "--max-pages",
        type=int,
        default=200,
        help="Maximum pages to crawl (default: 200)"
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Request timeout in seconds (default: 120)"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging"
    )

    parser.add_argument(
        "--aggregate-navigation",
        action="store_true",
        help="Extract navigation links and aggregate content into single Markdown file"
    )

    parser.add_argument(
        "--navigation-selector",
        type=str,
        default=None,
        help="CSS selector for navigation element (default: auto-detect VuePress sidebar)"
    )

    parser.add_argument(
        "--discovery-mode",
        type=str,
        choices=["map", "crawl"],
        default=None,
        help="Discovery method for finding pages: 'map' (comprehensive, default) or 'crawl' (recursive link following)"
    )

    # Markdown optimization flags
    parser.add_argument(
        "--include-toc",
        dest="include_toc",
        action="store_true",
        default=None,
        help="Include table of contents in aggregated file (default: enabled for aggregation mode)"
    )

    parser.add_argument(
        "--no-include-toc",
        dest="include_toc",
        action="store_false",
        help="Disable table of contents generation"
    )

    parser.add_argument(
        "--toc-max-level",
        type=int,
        default=3,
        metavar="LEVEL",
        help="Maximum heading level to include in table of contents (default: 3)"
    )

    parser.add_argument(
        "--normalize-headings",
        dest="normalize_headings",
        action="store_true",
        default=None,
        help="Normalize heading levels in aggregated file (default: enabled for aggregation mode)"
    )

    parser.add_argument(
        "--no-normalize-headings",
        dest="normalize_headings",
        action="store_false",
        help="Disable heading normalization"
    )

    return parser.parse_args()


def main() -> int:
    """
    Main entry point for CLI.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    # Parse arguments
    args = parse_arguments()

    # Setup logging
    logger = setup_logging(args.verbose)
    logger.info("Starting VBA documentation crawler")
    logger.info(f"URL: {args.url}")
    logger.info(f"Output directory: {args.output_dir}")
    logger.info(f"Max pages: {args.max_pages}")

    try:
        # Determine default values for optimization flags
        # When aggregation is enabled, defaults are True unless explicitly overridden
        include_toc = args.include_toc if args.include_toc is not None else args.aggregate_navigation
        normalize_headings = args.normalize_headings if args.normalize_headings is not None else args.aggregate_navigation

        # Get environment configuration
        env_config = CrawlConfig.from_env()

        # Determine discovery mode: CLI arg > env var > default
        discovery_mode = args.discovery_mode or env_config.get("discovery_mode", "map")

        # Create configuration
        config = CrawlConfig(
            start_url=args.url,
            output_dir=Path(args.output_dir),
            max_pages=args.max_pages,
            timeout_seconds=args.timeout,
            verbose=args.verbose,
            enable_crawl=(args.max_pages > 1),
            aggregate_navigation=args.aggregate_navigation,
            navigation_selector=args.navigation_selector,
            discovery_mode=discovery_mode,
            include_toc=include_toc,
            normalize_headings=normalize_headings,
            toc_max_level=args.toc_max_level
        )

        # Log discovery mode
        logger.info(f"Discovery mode: {config.discovery_mode}")

        # Validate configuration
        config.validate()

        # Choose mode based on aggregation flag and max_pages
        if args.aggregate_navigation:
            logger.info("Running in navigation aggregation mode")
            result = scrape_with_aggregation(config)
        elif args.max_pages == 1:
            logger.info("Running in single-page mode")
            result = scrape_single_page(config)
        else:
            logger.info("Running in multi-page mode")
            result = crawl_multiple_pages(config)

        # Print summary
        print("\n" + result.generate_summary())

        # Return exit code based on success
        return 0 if result.successful_pages > 0 else 1

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
