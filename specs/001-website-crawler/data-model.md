# Data Model: Website to Markdown Crawler

**Feature**: [001-website-crawler](spec.md)
**Date**: 2026-01-10
**Phase**: 1 - Design

## Overview

This document defines the core data entities and their relationships for the website crawler that converts VBA documentation to Markdown files using the Firecrawl API.

## Core Entities

### 1. CrawlConfig

Configuration for the crawling operation.

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass
class CrawlConfig:
    """Configuration for crawler execution."""

    # Input
    start_url: str  # Starting URL for crawl (must be https://dict.thinktrader.net/VBA/*)
    allowed_base_path: str = "/VBA/"  # URL path boundary

    # Firecrawl API
    api_base_url: str = "http://localhost:3002"
    api_key: str = "fc-YOUR_API_KEY"
    timeout_seconds: int = 120
    poll_interval_seconds: int = 2

    # Crawl behavior
    max_pages: int = 200  # Maximum pages to crawl
    enable_crawl: bool = True  # Use /v2/crawl endpoint (False = /v2/scrape only)

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

    def validate(self) -> None:
        """Validate configuration constraints."""
        if not self.start_url.startswith("https://dict.thinktrader.net/VBA/"):
            raise ValueError(f"start_url must be within https://dict.thinktrader.net/VBA/: {self.start_url}")
        if self.max_pages <= 0:
            raise ValueError(f"max_pages must be positive: {self.max_pages}")
        if self.timeout_seconds <= 0:
            raise ValueError(f"timeout_seconds must be positive: {self.timeout_seconds}")
```

**Validation Rules**:
- `start_url` MUST start with `https://dict.thinktrader.net/VBA/`
- `max_pages` MUST be positive integer
- `timeout_seconds` MUST be positive
- `output_dir` MUST be creatable (valid filesystem path)

### 2. CrawlJob

Represents a Firecrawl crawl job and its status.

```python
from enum import Enum
from typing import Optional
from datetime import datetime

class JobStatus(Enum):
    """Status of a crawl job."""
    PENDING = "pending"
    IN_PROGRESS = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class CrawlJob:
    """Firecrawl crawl job representation."""

    job_id: str  # Job ID from Firecrawl API
    status_url: str  # URL to check job status
    status: JobStatus
    created_at: datetime
    completed_at: Optional[datetime] = None

    # Statistics
    total_pages: int = 0
    completed_pages: int = 0
    failed_pages: int = 0

    # Error tracking
    last_error: Optional[str] = None

    @property
    def is_finished(self) -> bool:
        """Check if job has reached terminal state."""
        return self.status in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}

    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage."""
        if self.total_pages == 0:
            return 0.0
        return (self.completed_pages / self.total_pages) * 100
```

**State Transitions**:
```
PENDING → IN_PROGRESS → COMPLETED
                   ↘ FAILED
                   ↘ CANCELLED
```

### 3. ScrapedPage

Represents a single scraped page from Firecrawl.

```python
from typing import Dict, Any

@dataclass
class ScrapedPage:
    """Single page scraped from Firecrawl API."""

    # Source
    url: str  # Original URL
    source_url: str  # Actual URL after redirects

    # Content
    markdown: str  # Converted Markdown content
    html: Optional[str] = None  # Original HTML (if requested)

    # Metadata
    title: Optional[str] = None
    description: Optional[str] = None
    language: Optional[str] = None
    keywords: Optional[list[str]] = None
    metadata: Dict[str, Any] = None  # Additional metadata

    # Processing status
    success: bool = True
    error_message: Optional[str] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    @property
    def has_valid_content(self) -> bool:
        """Check if page has valid Markdown content."""
        return bool(self.markdown and len(self.markdown.strip()) > 0)

    @property
    def word_count(self) -> int:
        """Estimate word count of Markdown content."""
        return len(self.markdown.split())
```

**Validation Rules**:
- `markdown` MUST NOT be empty for successful pages
- `success` is FALSE if `error_message` is present
- `url` MUST be within allowed base path

### 4. MarkdownFile

Represents a Markdown file to be written to disk.

```python
import re

@dataclass
class MarkdownFile:
    """Representation of a Markdown file on disk."""

    # Content
    content: str  # Markdown content
    title: Optional[str] = None  # Page title

    # File location
    url: str  # Source URL
    relative_path: str  # Relative path from output_dir (e.g., "chapter1/lesson1.md")
    absolute_path: Optional[Path] = None  # Absolute path when resolved

    # Metadata for frontmatter
    source_url: str = ""
    scraped_at: Optional[datetime] = None

    def generate_frontmatter(self) -> str:
        """Generate YAML frontmatter for Markdown file."""
        lines = ["---"]
        if self.title:
            lines.append(f"title: {self.title}")
        lines.append(f"source_url: {self.source_url}")
        if self.scraped_at:
            lines.append(f"scraped_at: {self.scraped_at.isoformat()}")
        lines.append("---")
        lines.append("")
        return "\n".join(lines)

    def with_frontmatter(self) -> str:
        """Return Markdown content with YAML frontmatter prepended."""
        return self.generate_frontmatter() + self.content

    @classmethod
    def from_scraped_page(
        cls,
        page: ScrapedPage,
        output_dir: Path
    ) -> "MarkdownFile":
        """Create MarkdownFile from ScrapedPage."""
        # Generate filename and relative path from URL
        relative_path = cls._generate_relative_path(page.url, page.title or page.metadata.get("title"))

        return cls(
            content=page.markdown,
            title=page.title,
            url=page.url,
            source_url=page.source_url,
            relative_path=relative_path,
            scraped_at=datetime.now(),
            absolute_path=output_dir / relative_path
        )

    @staticmethod
    def _generate_relative_path(url: str, title: Optional[str]) -> str:
        """Generate relative file path from URL and optional title."""
        from urllib.parse import urlparse

        parsed = urlparse(url)
        path = parsed.path.replace("/VBA/", "", 1)  # Remove /VBA/ prefix
        path = path.replace(".html", "")  # Remove .html extension

        if title:
            # Sanitize title for filename
            safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
            safe_title = safe_title[:255].strip()
            if "/" in path:
                # Preserve directory structure, use title for filename
                dir_part = "/".join(path.split("/")[:-1])
                return f"{dir_part}/{safe_title}.md" if dir_part else f"{safe_title}.md"
            return f"{safe_title}.md"
        else:
            # Use URL path structure
            if not path or path == "/":
                return "index.md"
            return f"{path}.md"
```

**Filename Generation Rules**:
1. If title exists: Use sanitized title, preserve directory structure from URL
2. If no title: Use URL path structure
3. Remove `/VBA/` prefix and `.html` extension
4. Replace invalid filesystem characters: `< > : " / \ | ? *`
5. Limit filename to 255 characters

### 5. CrawlResult

Aggregated result of crawling operation.

```python
@dataclass
class CrawlResult:
    """Summary of crawl operation results."""

    # Configuration
    config: CrawlConfig

    # Job information
    job: Optional[CrawlJob] = None

    # Page results
    pages_scraped: list[ScrapedPage] = None
    files_created: list[MarkdownFile] = None

    # Statistics
    total_pages: int = 0
    successful_pages: int = 0
    failed_pages: int = 0
    skipped_pages: int = 0  # Outside boundary, duplicates, etc.

    # Errors
    errors: list[str] = None

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def __post_init__(self):
        if self.pages_scraped is None:
            self.pages_scraped = []
        if self.files_created is None:
            self.files_created = []
        if self.errors is None:
            self.errors = []

    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate total duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_pages == 0:
            return 0.0
        return (self.successful_pages / self.total_pages) * 100

    def add_error(self, error: str) -> None:
        """Add error message to results."""
        self.errors.append(error)

    def add_page(self, page: ScrapedPage) -> None:
        """Add scraped page to results."""
        self.pages_scraped.append(page)
        self.total_pages += 1
        if page.success:
            self.successful_pages += 1
        else:
            self.failed_pages += 1

    def generate_summary(self) -> str:
        """Generate human-readable summary report."""
        lines = [
            "=== Crawl Summary ===",
            f"Started: {self.started_at.isoformat() if self.started_at else 'N/A'}",
            f"Completed: {self.completed_at.isoformat() if self.completed_at else 'N/A'}",
            f"Duration: {self.duration_seconds:.2f}s" if self.duration_seconds else "Duration: N/A",
            "",
            "Pages:",
            f"  Total: {self.total_pages}",
            f"  Successful: {self.successful_pages}",
            f"  Failed: {self.failed_pages}",
            f"  Skipped: {self.skipped_pages}",
            f"  Success Rate: {self.success_rate:.1f}%",
            "",
            f"Files Created: {len(self.files_created)}",
        ]

        if self.errors:
            lines.extend([
                "",
                f"Errors ({len(self.errors)}):",
            ])
            for error in self.errors[:10]:  # Show first 10 errors
                lines.append(f"  - {error}")
            if len(self.errors) > 10:
                lines.append(f"  ... and {len(self.errors) - 10} more errors")

        return "\n".join(lines)
```

**Summary Report Format**:
```
=== Crawl Summary ===
Started: 2026-01-10T10:00:00
Completed: 2026-01-10T10:03:45
Duration: 225.00s

Pages:
  Total: 150
  Successful: 145
  Failed: 3
  Skipped: 2
  Success Rate: 96.7%

Files Created: 145

Errors (3):
  - Failed to scrape https://dict.thinktrader.net/VBA/page1.html: Connection timeout
  - Failed to write output/chapter2/lesson3.md: Permission denied
  - Invalid URL returned from API: https://example.com/external.html
```

## Entity Relationships

```
CrawlConfig (1)
    ↓ creates
CrawlJob (1)
    ↓ produces
CrawlResult (1)
    ↓ contains
ScrapedPage (0..*)
    ↓ converts to
MarkdownFile (0..*)
    ↓ written to
Filesystem (1..*)
```

## Data Flow

1. **Configuration**: User provides `CrawlConfig` via CLI
2. **Job Submission**: System creates `CrawlJob` via Firecrawl API
3. **Polling**: System polls job status until completion
4. **Page Extraction**: System extracts `ScrapedPage` objects from job results
5. **File Conversion**: System converts `ScrapedPage` → `MarkdownFile`
6. **File Writing**: System writes `MarkdownFile` content to disk
7. **Aggregation**: System aggregates results into `CrawlResult`
8. **Reporting**: System generates summary report from `CrawlResult`

## Validation Summary

All entities include validation logic:
- **Input validation**: URL boundaries, positive integers, valid paths
- **State validation**: Job status transitions, content non-empty
- **Output validation**: Filename sanitization, path resolution
- **Aggregate validation**: Success rates, error tracking, statistics

This data model ensures type safety, validation, and clear separation of concerns throughout the crawling pipeline.
