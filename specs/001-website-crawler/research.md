# Research: Website to Markdown Crawler

**Feature**: [001-website-crawler](spec.md)
**Date**: 2026-01-10
**Phase**: 0 - Research & Technical Decisions

## Overview

This document consolidates research findings for implementing a Python-based website crawler that uses the Firecrawl API to convert VBA documentation pages to Markdown format.

## Technical Decisions

### 1. Firecrawl Integration Approach

**Decision**: Use Firecrawl Python SDK with fallback to direct HTTP requests

**Rationale**:
- Firecrawl Python SDK provides a clean abstraction over the API
- Simplifies error handling and response parsing
- SDK documentation available at https://docs.firecrawl.dev/zh/sdks/python
- However, SDK may not be mature enough for all edge cases
- Direct HTTP requests using `requests` library provides more control

**Implementation Strategy**:
1. Primary: Use Firecrawl Python SDK for `/v2/crawl`, `/v2/scrape`, `/v2/map` endpoints
2. Fallback: Implement raw HTTP client using `requests` if SDK limitations encountered
3. Configuration: Support both SDK and HTTP client via environment variable or config option

**Alternatives Considered**:
- **Firecrawl SDK only**: rejected due to potential limitations and lack of control
- **HTTP requests only**: rejected due to increased complexity for authentication and response handling
- **Hybrid approach**: selected for optimal balance of simplicity and control

### 2. API Endpoint Usage Strategy

**Decision**: Use `/v2/crawl` for bulk crawling with `/v2/scrape` fallback for individual pages

**Rationale**:
- `/v2/crawl` endpoint handles link discovery and crawling automatically
- Returns job ID for async status checking
- Built-in support for `limit` parameter to control crawl depth
- `scrapeOptions.formats: ["markdown", "html"]` ensures Markdown output
- `/v2/scrape` provides fallback for single-page conversion (User Story 1)

**API Contract**:

```python
# Crawl endpoint (primary)
POST http://localhost:3002/v2/crawl
Headers:
  Authorization: Bearer fc-YOUR_API_KEY
  Content-Type: application/json
Body:
{
  "url": "https://dict.thinktrader.net/VBA/start_now.html",
  "limit": 100,
  "scrapeOptions": {
    "formats": ["markdown", "html"]
  }
}
Response:
{
  "success": true,
  "id": "job-123",
  "url": "http://localhost:3002/v2/crawl/job-123"
}

# Check crawl status
GET http://localhost:3002/v2/crawl/job-123
Headers:
  Authorization: Bearer fc-YOUR_API_KEY
Response:
{
  "success": true,
  "status": "completed",
  "total": 50,
  "completed": 50,
  "data": [
    {
      "markdown": "# Page Title\n\nContent...",
      "metadata": {
        "title": "Page Title",
        "sourceURL": "https://dict.thinktrader.net/VBA/page.html"
      }
    }
  ]
}

# Scrape endpoint (fallback for single page)
POST http://localhost:3002/v2/scrape
Body:
{
  "url": "https://dict.thinktrader.net/VBA/page.html",
  "formats": ["markdown"]
}
Response:
{
  "success": true,
  "data": {
    "markdown": "# Page Title\n\nContent...",
    "metadata": {...}
  }
}
```

**Alternatives Considered**:
- **Only `/v2/crawl`**: rejected - doesn't support single-page use case efficiently
- **Only `/v2/scrape` with custom link discovery**: rejected - increases complexity, violates API-first principle
- **`/v2/map` + `/v2/scrape`**: rejected - `/v2/crawl` provides same functionality more efficiently

### 3. URL Boundary Enforcement Strategy

**Decision**: Multi-layer URL validation (pre-crawl, post-crawl filtering)

**Rationale**:
- Firecrawl `/v2/crawl` may not respect path boundaries automatically
- Must enforce `https://dict.thinktrader.net/VBA/*` constraint strictly
- Pre-validation prevents invalid URLs from being sent to API
- Post-validation filters any URLs that slip through

**Implementation**:

```python
def is_allowed_url(url: str, base_path: str = "/VBA/") -> bool:
    """Validate URL is within allowed boundary."""
    try:
        parsed = urllib.parse.urlparse(url)
        # Check domain
        if parsed.netloc != "dict.thinktrader.net":
            return False
        # Check path starts with /VBA/
        if not parsed.path.startswith(base_path):
            return False
        return True
    except Exception:
        return False
```

**Layers**:
1. **Pre-crawl**: Validate starting URL before API call
2. **Link extraction filter**: If using `/v2/map`, filter results before crawling
3. **Post-crawl**: Filter results from `/v2/crawl` before file generation
4. **File write validation**: Final check before writing to disk

**Alternatives Considered**:
- **Trust Firecrawl to handle boundaries**: rejected - too risky, violates strict requirement
- **Only post-crawl filtering**: rejected - inefficient, wastes API calls
- **Multi-layer approach**: selected for maximum safety and compliance

### 4. Filename Generation Strategy

**Decision**: Priority order: page title (from metadata) → URL path → fallback hash

**Rationale**:
- Page titles provide human-readable filenames
- URL path provides structured fallback
- Hash prevents collisions for edge cases

**Implementation**:

```python
def generate_filename(url: str, metadata: dict) -> str:
    """Generate safe filename from URL or metadata."""
    # Priority 1: Use page title from metadata
    if "title" in metadata and metadata["title"]:
        title = metadata["title"]
        filename = sanitize_filename(title)
    else:
        # Priority 2: Extract from URL path
        path = urllib.parse.urlparse(url).path
        # Remove /VBA/ prefix and .html suffix
        filename = path.replace("/VBA/", "").replace(".html", "")
        if not filename or filename == "/":
            # Priority 3: Use URL hash as fallback
            filename = hashlib.md5(url.encode()).hexdigest()[:8]

    return f"{filename}.md"

def sanitize_filename(name: str) -> str:
    """Remove invalid filesystem characters."""
    # Remove invalid characters: < > : " / \ | ? *
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '_')
    # Limit length
    return name[:255].strip()
```

**Alternatives Considered**:
- **URL path only**: rejected - less user-friendly
- **Title only**: rejected - some pages may lack titles
- **Priority-based approach**: selected for optimal user experience

### 5. Directory Structure Strategy

**Decision**: Mirror URL path hierarchy in output directory

**Rationale**:
- Maintains logical organization of documentation
- Matches User Story 3 requirements
- Simplifies navigation of offline documentation

**Implementation**:

```python
def get_output_path(url: str, base_dir: pathlib.Path) -> pathlib.Path:
    """Generate output file path from URL."""
    parsed = urllib.parse.urlparse(url)
    # Extract path after /VBA/
    path = parsed.path.replace("/VBA/", "", 1)
    # Remove file extension
    path = path.replace(".html", "")

    # Build directory structure
    if "/" in path:
        # Nested path: /VBA/chapter1/lesson1.html
        dir_parts = path.split("/")[:-1]  # All but filename
        filename = path.split("/")[-1] or "index"
    else:
        # Flat path: /VBA/page.html
        dir_parts = []
        filename = path or "index"

    # Create directory path
    output_dir = base_dir / pathlib.Path(*dir_parts) if dir_parts else base_dir
    return output_dir / f"{filename}.md"
```

**Example**:
- URL: `https://dict.thinktrader.net/VBA/chapter1/lesson1.html`
- Output: `output/chapter1/lesson1.md`

**Alternatives Considered**:
- **Flat structure**: rejected - harder to navigate, doesn't match spec
- **Custom organization**: rejected - over-engineering
- **Mirror URL structure**: selected for simplicity and clarity

### 6. Error Handling Strategy

**Decision**: Comprehensive error handling with retry logic and circuit breaker

**Rationale**:
- Network operations are inherently unreliable
- Firecrawl service may be temporarily unavailable
- Must comply with Constitution Principle II (Network Error Handling)

**Implementation**:

```python
import time
import logging
from typing import Optional, Callable
from requests.exceptions import RequestException

class CircuitBreaker:
    """Circuit breaker for failing endpoints."""
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open

    def record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = "open"

    def record_success(self):
        self.failures = 0
        self.state = "closed"

    def can_attempt(self) -> bool:
        if self.state == "closed":
            return True
        if self.state == "open":
            if time.time() - self.last_failure_time > self.timeout:
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
):
    """Retry function with exponential backoff."""
    delay = initial_delay
    last_exception = None

    for attempt in range(max_retries):
        if circuit_breaker and not circuit_breaker.can_attempt():
            raise Exception("Circuit breaker is OPEN")

        try:
            result = func()
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
```

**Error Categories**:
1. **Transient (retryable)**: Connection timeout, 5xx errors, network interruptions
2. **Permanent (non-retryable)**: 4xx errors (except 429), invalid URLs, authentication failures
3. **Service unavailable**: Firecrawl service down (circuit breaker)

**Alternatives Considered**:
- **Basic try-except**: rejected - insufficient for production use
- **Only retries**: rejected - no protection against cascading failures
- **Comprehensive approach**: selected for reliability

### 7. Logging Strategy

**Decision**: Structured logging with multiple levels and contextual information

**Rationale**:
- Facilitates debugging and monitoring
- Complies with Constitution Principle II (logging requirement)
- User-visible progress reporting

**Implementation**:

```python
import logging
import sys

def setup_logging(verbose: bool = False) -> logging.Logger:
    """Configure logging for the crawler."""
    logger = logging.getLogger("vba_crawler")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

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

# Usage examples:
# logger.info(f"Starting crawl from {start_url}")
# logger.debug(f"API Request: POST /v2/crawl with body={request_body}")
# logger.info(f"Crawling page {url}")
# logger.warning(f"Retry {attempt}/{max_retries} after error: {error}")
# logger.error(f"Failed to crawl {url}: {error}", extra={"url": url, "error_type": type(error).__name__})
# logger.info(f"Crawl completed: {success_count} succeeded, {failure_count} failed")
```

**Log Levels**:
- **DEBUG**: Detailed API requests/responses, URL parsing details
- **INFO**: Crawl progress, pages processed, summary reports
- **WARNING**: Retries, skipped URLs, minor issues
- **ERROR**: Failed pages, API errors, file write failures

**Alternatives Considered**:
- **Print statements**: rejected - no flexibility, poor practice
- **File-only logging**: rejected - users need real-time feedback
- **Structured logging with console**: selected for optimal UX

### 8. Dependencies Strategy

**Decision**: Minimize dependencies, prefer standard library

**Selected Dependencies**:

```txt
# Core dependencies
firecrawl-py>=0.0.1  # Firecrawl API client (will verify actual version)
requests>=2.31.0     # HTTP client with retry support

# Development dependencies (optional)
pytest>=7.4.0        # Testing framework
pytest-mock>=3.11.0  # Mocking support
pytest-cov>=4.1.0    # Code coverage
black>=23.0.0        # Code formatting
mypy>=1.5.0          # Type checking
```

**Standard Library Usage**:
- `pathlib`: File system operations
- `urllib.parse`: URL parsing and validation
- `argparse`: CLI argument parsing
- `logging`: Logging infrastructure
- `json`: JSON parsing for API responses
- `hashlib`: Filename hash generation
- `time`: Retry delays

**Rationale**:
- Minimizes external dependencies per Constitution Principle IV
- Standard library is stable, well-documented, and cross-platform
- Firecrawl SDK is necessary for API integration
- requests library is de facto standard for HTTP in Python

**Alternatives Considered**:
- **httpx**: rejected - requests is sufficient and more widely used
- **aiohttp**: rejected - async complexity not needed for this use case
- **click**: rejected - argparse from stdlib is sufficient

## Unresolved Questions

### None

All technical decisions have been resolved. The research phase identified clear approaches for:
1. Firecrawl integration (SDK + HTTP fallback)
2. API endpoint usage (/v2/crawl with /v2/scrape fallback)
3. URL boundary enforcement (multi-layer validation)
4. Filename generation (priority-based: title → path → hash)
5. Directory structure (mirror URL hierarchy)
6. Error handling (retry + circuit breaker)
7. Logging (structured with multiple levels)
8. Dependencies (minimal: firecrawl-py, requests)

## Next Steps

Proceed to **Phase 1: Design & Contracts** to create:
1. `data-model.md` - Entity definitions and data structures
2. `contracts/firecrawl-api.yaml` - OpenAPI specification for Firecrawl integration
3. `quickstart.md` - Developer onboarding guide
