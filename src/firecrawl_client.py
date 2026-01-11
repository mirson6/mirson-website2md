"""Firecrawl API client with comprehensive error handling."""

import logging
import time
from typing import Optional, Callable
from dataclasses import dataclass
from requests.exceptions import RequestException
import requests


@dataclass
class CircuitBreaker:
    """Circuit breaker for failing endpoints."""

    failure_threshold: int = 5
    timeout: int = 60
    failures: int = 0
    last_failure_time: Optional[float] = None
    state: str = "closed"  # closed, open, half-open

    def record_failure(self) -> None:
        """Record a failure and potentially open the circuit."""
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = "open"

    def record_success(self) -> None:
        """Record a success and close the circuit."""
        self.failures = 0
        self.state = "closed"

    def can_attempt(self) -> bool:
        """Check if operation can be attempted based on circuit state."""
        if self.state == "closed":
            return True
        if self.state == "open":
            if self.last_failure_time and (time.time() - self.last_failure_time > self.timeout):
                self.state = "half-open"
                return True
            return False
        return True


def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    circuit_breaker: Optional[CircuitBreaker] = None
) -> Callable:
    """
    Retry decorator with exponential backoff.

    Args:
        func: Function to retry
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for delay after each retry
        circuit_breaker: Optional circuit breaker instance

    Returns:
        Wrapped function with retry logic
    """
    def wrapper(*args, **kwargs):
        delay = initial_delay
        last_exception = None

        for attempt in range(max_retries):
            if circuit_breaker and not circuit_breaker.can_attempt():
                raise Exception("Circuit breaker is OPEN")

            try:
                result = func(*args, **kwargs)
                if circuit_breaker:
                    circuit_breaker.record_success()
                return result
            except (RequestException, TimeoutError) as e:
                last_exception = e
                if attempt < max_retries - 1:
                    logging.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                    time.sleep(delay)
                    delay *= backoff_factor
                else:
                    if circuit_breaker:
                        circuit_breaker.record_failure()
                    logging.error(f"All {max_retries} attempts failed: {e}")

        raise last_exception

    return wrapper


class FirecrawlClient:
    """Firecrawl API client wrapper with error handling."""

    def __init__(
        self,
        api_base_url: str = "http://localhost:3002",
        api_key: str = "fc-test",
        timeout_seconds: int = 120
    ):
        """
        Initialize Firecrawl client.

        Args:
            api_base_url: Base URL for Firecrawl API
            api_key: API key for authentication
            timeout_seconds: Request timeout in seconds
        """
        self.api_base_url = api_base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout_seconds
        self.circuit_breaker = CircuitBreaker()
        self.logger = logging.getLogger(__name__)

    def _get_headers(self) -> dict:
        """Get request headers with authentication."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    @retry_with_backoff
    def _make_request(self, method: str, endpoint: str, **kwargs) -> dict:
        """
        Make HTTP request with error handling.

        Args:
            method: HTTP method (GET, POST)
            endpoint: API endpoint path
            **kwargs: Additional arguments for requests

        Returns:
            Parsed JSON response

        Raises:
            RequestException: If request fails after retries
        """
        url = f"{self.api_base_url}{endpoint}"
        headers = self._get_headers()

        self.logger.debug(f"API Request: {method} {url}")

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                timeout=self.timeout,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout as e:
            self.logger.error(f"Request timeout: {url}")
            raise
        except requests.exceptions.ConnectionError as e:
            self.logger.error(f"Connection failed: {url} - {e}")
            self.logger.error(
                "Firecrawl service may not be running. Start it with:\n"
                "  docker run -p 3002:3002 -e API_KEY=fc-test firecrawl/firecrawl:latest\n"
                "Or install via npm: npm install -g @mendable/firecrawl"
            )
            raise
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
            raise

    def scrape_url(self, url: str, include_html: bool = False) -> dict:
        """
        Scrape a single URL and return Markdown content.

        Args:
            url: URL to scrape
            include_html: Whether to also request HTML content (for navigation extraction)

        Returns:
            API response with scraped data

        Raises:
            RequestException: If scrape request fails
        """
        endpoint = "/v2/scrape"
        formats = ["markdown"]
        if include_html:
            formats.append("html")

        payload = {
            "url": url,
            "formats": formats
        }

        self.logger.info(f"Scraping page: {url}")

        response = self._make_request("POST", endpoint, json=payload)

        self.logger.debug(f"Scrape response success: {response.get('success', False)}")
        return response

    def submit_crawl_job(self, url: str, limit: Optional[int] = None) -> dict:
        """
        Submit a crawl job to Firecrawl API.

        Args:
            url: Starting URL for crawl
            limit: Maximum number of pages to crawl

        Returns:
            API response with job ID and status URL

        Raises:
            RequestException: If job submission fails
        """
        endpoint = "/v2/crawl"
        payload = {
            "url": url,
            "scrapeOptions": {
                "formats": ["markdown"]
            }
        }

        # Add limit if specified
        if limit is not None:
            payload["limit"] = limit

        self.logger.info(f"Submitting crawl job for: {url} (limit: {limit})")

        response = self._make_request("POST", endpoint, json=payload)

        job_id = response.get("id")
        status_url = response.get("status")

        self.logger.info(f"Crawl job submitted: ID={job_id}, status={status_url}")
        return response

    def check_crawl_status(self, job_id: str) -> dict:
        """
        Check status of a crawl job.

        Args:
            job_id: Crawl job ID

        Returns:
            API response with job status and data

        Raises:
            RequestException: If status check fails
        """
        endpoint = f"/v2/crawl/{job_id}"

        self.logger.debug(f"Checking crawl status for job: {job_id}")

        response = self._make_request("GET", endpoint)

        status = response.get("status", "unknown")
        total = response.get("total", 0)
        completed = response.get("completed", 0)

        self.logger.debug(f"Job {job_id} status: {status} ({completed}/{total})")
        return response

    def poll_crawl_job(
        self,
        job_id: str,
        poll_interval: int = 5,
        max_polls: int = 120
    ) -> dict:
        """
        Poll crawl job until completion.

        Args:
            job_id: Crawl job ID
            poll_interval: Seconds between status checks
            max_polls: Maximum number of polling attempts

        Returns:
            Final API response with completed job data

        Raises:
            TimeoutError: If job doesn't complete within max_polls
            RequestException: If status checks fail
        """
        self.logger.info(f"Polling job {job_id} (interval: {poll_interval}s, max: {max_polls})")

        for attempt in range(max_polls):
            response = self.check_crawl_status(job_id)
            status = response.get("status", "unknown")

            # Report progress
            total = response.get("total", 0)
            completed = response.get("completed", 0)
            if total > 0:
                progress = (completed / total) * 100
                self.logger.info(f"Progress: {completed}/{total} pages ({progress:.1f}%)")

            # Check if job is complete
            if status in ["completed", "failed", "cancelled"]:
                self.logger.info(f"Job {job_id} finished with status: {status}")
                return response

            # Wait before next poll
            time.sleep(poll_interval)

        raise TimeoutError(f"Job {job_id} did not complete within {max_polls * poll_interval}s")

    @retry_with_backoff
    def map_url(self, url: str) -> dict:
        """
        Discover all pages under a URL path using Firecrawl map API.

        For VuePress/SPA sites, this scrapes the page and extracts links
        from the HTML content to discover all pages.

        Args:
            url: URL to map (e.g., https://example.com/docs/)

        Returns:
            Dictionary with:
                - success: bool
                - data: list of discovered page URLs with metadata
                - error: str (if failed)

        Raises:
            RequestException: If map request fails after retries
            TimeoutError: If mapping exceeds timeout
        """
        self.logger.info(f"Mapping URL for comprehensive discovery: {url}")

        # First try the Firecrawl map API
        try:
            endpoint = "/v1/map"
            payload = {"url": url}

            response = self._make_request("POST", endpoint, json=payload)

            # Extract page links from response
            links = response.get("links", [])

            # If map API returned links, use them
            if links and len(links) > 1:
                self.logger.info(f"Map API discovered {len(links)} pages")
                return {
                    "success": True,
                    "data": links,
                    "url": url
                }
        except Exception as e:
            self.logger.debug(f"Map API not available or returned insufficient results: {e}")

        # Fallback: Scrape page and extract links from HTML
        self.logger.info("Map API unavailable, using HTML scraping to discover links...")
        scrape_response = self.scrape_url(url, include_html=True)

        if not scrape_response.get("success"):
            return {
                "success": False,
                "error": scrape_response.get("error", "Failed to scrape page"),
                "url": url
            }

        # Extract links from HTML content
        from bs4 import BeautifulSoup
        import re
        from urllib.parse import urljoin

        data = scrape_response.get("data", {})
        html_content = data.get("html", "")

        if not html_content:
            return {
                "success": False,
                "error": "No HTML content returned",
                "url": url
            }

        # Parse HTML and extract all href attributes
        soup = BeautifulSoup(html_content, "html.parser")
        links_dict = {}  # Use dict to deduplicate while preserving first seen

        for link in soup.find_all("a", href=True):
            href = link.get("href")
            if href:
                # Resolve relative URLs
                full_url = urljoin(url, href)
                # Only include URLs from the same domain and path
                if "/VBA/" in full_url:
                    # Remove fragments (anchors) for deduplication
                    base_url = full_url.split('#')[0] if '#' in full_url else full_url
                    # Only keep the first occurrence of each base URL
                    if base_url not in links_dict:
                        links_dict[base_url] = full_url

        # Get unique base URLs
        links = sorted(links_dict.keys())
        self.logger.info(f"HTML scraping discovered {len(links)} unique VBA pages")

        # Log discovered URLs
        for i, link in enumerate(links, 1):
            self.logger.debug(f"  {i}. {link}")

        # Return standardized response format
        return {
            "success": True,
            "data": links,
            "url": url
        }
