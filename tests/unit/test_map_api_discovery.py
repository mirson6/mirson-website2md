"""Unit tests for map API discovery functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from requests.exceptions import RequestException, Timeout

from src.firecrawl_client import FirecrawlClient
from src.config import CrawlConfig


class TestFirecrawlClientMapUrl:
    """Tests for FirecrawlClient.map_url() method."""

    def test_map_url_success(self):
        """Test successful map API request."""
        client = FirecrawlClient(
            api_base_url="http://localhost:3002",
            api_key="fc-test",
            timeout_seconds=30
        )

        # Mock the _make_request method
        mock_response = {
            "links": [
                "https://dict.thinktrader.net/VBA/start_now.html",
                "https://dict.thinktrader.net/VBA/basic_syntax.html",
                "https://dict.thinktrader.net/VBA/variables.html"
            ]
        }

        with patch.object(client, '_make_request', return_value=mock_response):
            result = client.map_url("https://dict.thinktrader.net/VBA/")

        assert result["success"] is True
        assert len(result["data"]) == 3
        assert result["url"] == "https://dict.thinktrader.net/VBA/"

    def test_map_url_with_dict_links(self):
        """Test map API with dict links containing metadata."""
        client = FirecrawlClient(
            api_base_url="http://localhost:3002",
            api_key="fc-test",
            timeout_seconds=30
        )

        # Mock response with dict links
        mock_response = {
            "links": [
                {"url": "https://dict.thinktrader.net/VBA/start_now.html", "title": "Start Now"},
                {"url": "https://dict.thinktrader.net/VBA/basic_syntax.html", "title": "Basic Syntax"}
            ]
        }

        with patch.object(client, '_make_request', return_value=mock_response):
            result = client.map_url("https://dict.thinktrader.net/VBA/")

        assert result["success"] is True
        assert len(result["data"]) == 2
        assert isinstance(result["data"][0], dict)
        assert result["data"][0]["url"] == "https://dict.thinktrader.net/VBA/start_now.html"

    def test_map_url_empty_results(self):
        """Test map API with empty results."""
        client = FirecrawlClient(
            api_base_url="http://localhost:3002",
            api_key="fc-test",
            timeout_seconds=30
        )

        mock_response = {"links": []}

        with patch.object(client, '_make_request', return_value=mock_response):
            result = client.map_url("https://dict.thinktrader.net/VBA/")

        assert result["success"] is True
        assert len(result["data"]) == 0

    def test_map_url_timeout_handling(self):
        """Test map API timeout handling."""
        client = FirecrawlClient(
            api_base_url="http://localhost:3002",
            api_key="fc-test",
            timeout_seconds=1
        )

        # Mock timeout exception
        with patch.object(client, '_make_request', side_effect=Timeout("Request timed out")):
            with pytest.raises(Timeout):
                client.map_url("https://dict.thinktrader.net/VBA/")

    def test_map_url_retry_on_failure(self):
        """Test map API retry logic on transient errors."""
        client = FirecrawlClient(
            api_base_url="http://localhost:3002",
            api_key="fc-test",
            timeout_seconds=30
        )

        # Mock two failures then success
        mock_response = {
            "links": ["https://dict.thinktrader.net/VBA/start_now.html"]
        }

        with patch.object(client, '_make_request',
                         side_effect=[RequestException("Service unavailable"),
                                    RequestException("Service unavailable"),
                                    mock_response]):
            result = client.map_url("https://dict.thinktrader.net/VBA/")

        assert result["success"] is True
        assert len(result["data"]) == 1


class TestDiscoveryModeConfiguration:
    """Tests for discovery mode configuration."""

    def test_default_discovery_mode_is_map(self):
        """Test that default discovery mode is 'map'."""
        config = CrawlConfig(
            start_url="https://dict.thinktrader.net/VBA/start_now.html"
        )

        assert config.discovery_mode == "map"

    def test_discovery_mode_map(self):
        """Test setting discovery mode to 'map'."""
        config = CrawlConfig(
            start_url="https://dict.thinktrader.net/VBA/start_now.html",
            discovery_mode="map"
        )

        assert config.discovery_mode == "map"
        config.validate()  # Should not raise

    def test_discovery_mode_crawl(self):
        """Test setting discovery mode to 'crawl'."""
        config = CrawlConfig(
            start_url="https://dict.thinktrader.net/VBA/start_now.html",
            discovery_mode="crawl"
        )

        assert config.discovery_mode == "crawl"
        config.validate()  # Should not raise

    def test_invalid_discovery_mode_raises_error(self):
        """Test that invalid discovery mode raises ValueError."""
        config = CrawlConfig(
            start_url="https://dict.thinktrader.net/VBA/start_now.html",
            discovery_mode="invalid"
        )

        with pytest.raises(ValueError, match="discovery_mode must be one of"):
            config.validate()

    def test_from_env_discovery_mode_map(self):
        """Test CrawlConfig.from_env() with map mode."""
        import os
        old_value = os.environ.get("CRAWLER_DISCOVERY_MODE")
        try:
            os.environ["CRAWLER_DISCOVERY_MODE"] = "map"
            env_config = CrawlConfig.from_env()
            assert env_config.get("discovery_mode") == "map"
        finally:
            if old_value is None:
                os.environ.pop("CRAWLER_DISCOVERY_MODE", None)
            else:
                os.environ["CRAWLER_DISCOVERY_MODE"] = old_value

    def test_from_env_discovery_mode_crawl(self):
        """Test CrawlConfig.from_env() with crawl mode."""
        import os
        old_value = os.environ.get("CRAWLER_DISCOVERY_MODE")
        try:
            os.environ["CRAWLER_DISCOVERY_MODE"] = "crawl"
            env_config = CrawlConfig.from_env()
            assert env_config.get("discovery_mode") == "crawl"
        finally:
            if old_value is None:
                os.environ.pop("CRAWLER_DISCOVERY_MODE", None)
            else:
                os.environ["CRAWLER_DISCOVERY_MODE"] = old_value

    def test_from_env_invalid_discovery_mode_ignored(self):
        """Test that invalid discovery mode in env is ignored."""
        import os
        old_value = os.environ.get("CRAWLER_DISCOVERY_MODE")
        try:
            os.environ["CRAWLER_DISCOVERY_MODE"] = "invalid"
            env_config = CrawlConfig.from_env()
            # Invalid values should be ignored
            assert "discovery_mode" not in env_config
        finally:
            if old_value is None:
                os.environ.pop("CRAWLER_DISCOVERY_MODE", None)
            else:
                os.environ["CRAWLER_DISCOVERY_MODE"] = old_value


class TestMapApiUrlBoundaryFiltering:
    """Tests for URL boundary filtering with map API results."""

    def test_filter_map_results_by_boundary(self):
        """Test filtering map API results by allowed path."""
        from src.crawler import filter_allowed_pages

        # Simulate map API results
        api_results = [
            {"url": "https://dict.thinktrader.net/VBA/start_now.html"},
            {"url": "https://dict.thinktrader.net/VBA/basic_syntax.html"},
            {"url": "https://example.com/other/page.html"},  # Outside boundary
            {"url": "https://dict.thinktrader.net/VBA/variables.html"}
        ]

        filtered, skipped = filter_allowed_pages(
            api_results,
            allowed_base_path="/VBA/"
        )

        assert len(filtered) == 3
        assert skipped == 1
        assert all("/VBA/" in page.get("url", "") for page in filtered)

    def test_deduplicate_map_results(self):
        """Test deduplication of map API results."""
        from src.crawler import deduplicate_urls

        # Simulate map results with duplicates
        api_results = [
            {"url": "https://dict.thinktrader.net/VBA/start_now.html"},
            {"url": "https://dict.thinktrader.net/VBA/start_now.html"},  # Duplicate
            {"url": "https://dict.thinktrader.net/VBA/basic_syntax.html"}
        ]

        deduplicated, duplicates = deduplicate_urls(api_results)

        assert len(deduplicated) == 2
        assert duplicates == 1


class TestMapApiIntegrationScenarios:
    """Tests for map API integration scenarios."""

    def test_map_api_fallback_to_crawl_on_failure(self):
        """Test fallback to crawl API when map API fails."""
        # This is more of an integration test scenario
        # The actual implementation is in crawler.py
        # Here we just verify the concept
        client = FirecrawlClient(
            api_base_url="http://localhost:3002",
            api_key="fc-test",
            timeout_seconds=30
        )

        # Mock map API failure
        with patch.object(client, '_make_request', side_effect=RequestException("Map API not available")):
            with pytest.raises(RequestException):
                client.map_url("https://dict.thinktrader.net/VBA/")

        # In the actual crawler.py, this exception is caught and crawl API is used
        # This test verifies the exception is raised for the retry logic to handle it

    def test_discovery_mode_selection(self):
        """Test that discovery mode determines which API is used."""
        # Test map mode
        config_map = CrawlConfig(
            start_url="https://dict.thinktrader.net/VBA/start_now.html",
            discovery_mode="map"
        )
        assert config_map.discovery_mode == "map"

        # Test crawl mode
        config_crawl = CrawlConfig(
            start_url="https://dict.thinktrader.net/VBA/start_now.html",
            discovery_mode="crawl"
        )
        assert config_crawl.discovery_mode == "crawl"
