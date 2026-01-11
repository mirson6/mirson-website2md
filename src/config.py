"""Configuration management for the VBA documentation crawler."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Literal


@dataclass
class CrawlConfig:
    """Configuration for crawler execution."""

    # Input
    start_url: str  # Starting URL for crawl (must be https://dict.thinktrader.net/VBA/*)
    allowed_base_path: str = "/VBA/"  # URL path boundary

    # Firecrawl API
    api_base_url: str = "http://localhost:3002"
    api_key: str = "fc-test"
    timeout_seconds: int = 120
    poll_interval_seconds: int = 2

    # Crawl behavior
    max_pages: int = 200  # Maximum pages to crawl
    enable_crawl: bool = True  # Use /v2/crawl endpoint (False = /v2/scrape only)
    discovery_mode: Literal["map", "crawl"] = "map"  # Discovery method: map API or crawl API

    # Navigation aggregation mode
    aggregate_navigation: bool = False  # Extract navigation links and aggregate content
    navigation_selector: Optional[str] = None  # CSS selector for navigation element

    # Markdown optimization (for aggregation mode)
    include_toc: bool = True  # Include table of contents in aggregated file (default: True for aggregation)
    normalize_headings: bool = True  # Normalize heading levels in aggregated file (default: True for aggregation)
    toc_max_level: int = 3  # Maximum heading level for TOC (default: 3)

    # Output
    output_dir: Path = Path("./output")
    overwrite_existing: bool = False

    # Network error handling
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    retry_backoff_factor: float = 2.0
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout_seconds: int = 60

    # Logging
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR
    verbose: bool = False

    @classmethod
    def from_env(cls) -> dict:
        """
        Get configuration values from environment variables.

        Returns:
            Dictionary of config values from environment
        """
        env_config = {}

        # Discovery mode from environment
        if "CRAWLER_DISCOVERY_MODE" in os.environ:
            discovery_mode = os.environ["CRAWLER_DISCOVERY_MODE"].lower()
            if discovery_mode in ["map", "crawl"]:
                env_config["discovery_mode"] = discovery_mode

        return env_config

    def validate(self) -> None:
        """
        Validate configuration constraints.

        Raises:
            ValueError: If configuration violates constraints.
        """
        if not self.start_url.startswith("https://dict.thinktrader.net/VBA/"):
            raise ValueError(
                f"start_url must be within https://dict.thinktrader.net/VBA/: {self.start_url}"
            )
        if self.max_pages <= 0:
            raise ValueError(f"max_pages must be positive: {self.max_pages}")
        if self.timeout_seconds <= 0:
            raise ValueError(f"timeout_seconds must be positive: {self.timeout_seconds}")

        # Validate discovery_mode
        valid_modes = ["map", "crawl"]
        if self.discovery_mode not in valid_modes:
            raise ValueError(
                f"discovery_mode must be one of {valid_modes}: {self.discovery_mode}"
            )
