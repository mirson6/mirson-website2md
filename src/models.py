"""Data models for the VBA documentation crawler."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


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
    metadata: dict = field(default_factory=dict)

    # Processing status
    success: bool = True
    error_message: Optional[str] = None

    @property
    def has_valid_content(self) -> bool:
        """Check if page has valid Markdown content."""
        return bool(self.markdown and len(self.markdown.strip()) > 0)

    @property
    def word_count(self) -> int:
        """Estimate word count of Markdown content."""
        return len(self.markdown.split())


@dataclass
class MarkdownFile:
    """Representation of a Markdown file on disk."""

    # Content
    content: str  # Markdown content

    # File location
    url: str  # Source URL
    relative_path: str  # Relative path from output_dir (e.g., "chapter1/lesson1.md")

    # Optional fields with defaults
    title: Optional[str] = None  # Page title
    absolute_path: Optional[Path] = None  # Absolute path when resolved
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
    def from_scraped_page(cls, page: ScrapedPage, output_dir: Path) -> "MarkdownFile":
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
            import re
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


@dataclass
class AggregatedMarkdownFile:
    """Representation of an aggregated Markdown file from multiple sources."""

    # Content
    aggregated_markdown: str  # Combined Markdown content from multiple pages

    # File location
    base_url: str  # Original page URL where navigation was extracted
    source_urls: list[str]  # All scraped URLs
    relative_path: str  # Relative path from output_dir (e.g., "start_now_aggregated.md")

    # Optional fields with defaults
    title: Optional[str] = None  # Primary page title
    absolute_path: Optional[Path] = None  # Absolute path when resolved
    aggregated_at: Optional[datetime] = None
    failed_urls: list[str] = None  # URLs that failed to scrape

    # Optimization settings (metadata only, actual optimization in from_pages)
    include_toc: bool = True  # Whether TOC was included
    normalize_headings: bool = True  # Whether headings were normalized
    toc_max_level: int = 3  # Maximum TOC depth
    headings_normalized: int = 0  # Number of headings normalized
    vuejs_content: bool = False  # Whether Vue.js content was detected

    def __post_init__(self):
        """Initialize failed_urls as empty list if not provided."""
        if self.failed_urls is None:
            self.failed_urls = []

    def generate_frontmatter(self) -> str:
        """Generate YAML frontmatter for aggregated Markdown file."""
        lines = ["---"]
        if self.title:
            lines.append(f"title: {self.title}")
        lines.append(f"base_url: {self.base_url}")
        lines.append(f"source_urls:")
        for url in self.source_urls:
            lines.append(f"  - {url}")
        if self.failed_urls:
            lines.append(f"failed_urls:")
            for url in self.failed_urls:
                lines.append(f"  - {url}")
        if self.aggregated_at:
            lines.append(f"aggregated_at: {self.aggregated_at.isoformat()}")
        lines.append(f"total_pages: {len(self.source_urls)}")
        lines.append(f"successful_pages: {len(self.source_urls) - len(self.failed_urls)}")

        # Optimization metadata
        if self.include_toc:
            lines.append(f"include_toc: true")
            lines.append(f"toc_max_level: {self.toc_max_level}")
        if self.normalize_headings:
            lines.append(f"normalize_headings: true")
            if self.headings_normalized > 0:
                lines.append(f"headings_normalized: {self.headings_normalized}")
        if self.vuejs_content:
            lines.append(f"vuejs_content: true")
            lines.append(f"rendering_method: javascript")

        lines.append("---")
        lines.append("")
        return "\n".join(lines)

    def with_frontmatter(self) -> str:
        """Return Markdown content with YAML frontmatter prepended."""
        return self.generate_frontmatter() + self.aggregated_markdown

    @classmethod
    def from_pages(
        cls,
        base_url: str,
        pages: list[ScrapedPage],
        output_dir: Path,
        failed_urls: list[str] = None,
        include_toc: bool = True,
        normalize_headings: bool = True,
        toc_max_level: int = 3,
        vuejs_content: bool = False
    ) -> "AggregatedMarkdownFile":
        """
        Create AggregatedMarkdownFile from multiple ScrapedPage instances with optional optimization.

        Args:
            base_url: Original page URL where navigation was extracted
            pages: List of successfully scraped pages
            output_dir: Output directory for the file
            failed_urls: List of URLs that failed to scrape (optional)
            include_toc: Whether to include table of contents (default: True)
            normalize_headings: Whether to normalize heading levels (default: True)
            toc_max_level: Maximum heading level for TOC (default: 3)
            vuejs_content: Whether content is Vue.js rendered (default: False)

        Returns:
            AggregatedMarkdownFile instance with optimized content
        """
        if not pages:
            raise ValueError("At least one page is required for aggregation")

        # Import here to avoid circular imports
        from .markdown_optimizer import (
            normalize_multi_page_content,
            analyze_heading_structure,
            generate_table_of_contents,
            insert_toc_into_markdown,
            TOCPosition
        )

        # Use title from first page as primary title
        primary_title = pages[0].title

        # Generate aggregated filename
        relative_path = cls._generate_aggregated_path(base_url, primary_title)

        # Extract markdown content from each page
        markdown_sections = [page.markdown for page in pages]

        # Step 1: Normalize heading levels if requested
        headings_normalized = 0
        if normalize_headings and len(pages) > 1:
            aggregated_markdown, norm_report = normalize_multi_page_content(
                markdown_sections,
                preserve_first_h1=True
            )
            headings_normalized = norm_report.normalized_headings
        else:
            # Just combine sections without normalization
            content_sections = []
            for i, page in enumerate(pages):
                # Add section separator with source URL
                section_title = page.title or f"Section {i + 1}"
                content_sections.append(f"\n## {section_title}\n")
                content_sections.append(f"*Source: {page.url}*\n")
                content_sections.append(page.markdown)
                content_sections.append("\n---\n")
            aggregated_markdown = "".join(content_sections)

        # Step 2: Generate and insert TOC if requested
        if include_toc:
            # Analyze headings in the combined content
            headings = analyze_heading_structure(aggregated_markdown)

            if headings:
                # Generate TOC
                toc = generate_table_of_contents(
                    headings,
                    max_level=toc_max_level,
                    title="Table of Contents"
                )

                # Insert TOC after frontmatter position
                # Note: frontmatter is added later, so we insert at DOCUMENT_START
                # and it will end up after frontmatter
                aggregated_markdown = insert_toc_into_markdown(
                    aggregated_markdown,
                    toc,
                    position=TOCPosition.DOCUMENT_START
                )

        return cls(
            base_url=base_url,
            source_urls=[p.url for p in pages],
            aggregated_markdown=aggregated_markdown,
            title=primary_title,
            relative_path=relative_path,
            aggregated_at=datetime.now(),
            absolute_path=output_dir / relative_path,
            failed_urls=failed_urls or [],
            include_toc=include_toc,
            normalize_headings=normalize_headings,
            toc_max_level=toc_max_level,
            headings_normalized=headings_normalized,
            vuejs_content=vuejs_content
        )

    @staticmethod
    def _generate_aggregated_path(url: str, title: Optional[str]) -> str:
        """Generate relative file path for aggregated file."""
        from urllib.parse import urlparse
        import re

        parsed = urlparse(url)
        path = parsed.path.replace("/VBA/", "", 1)  # Remove /VBA/ prefix
        path = path.replace(".html", "")  # Remove .html extension

        # Sanitize and use base filename
        if title:
            safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
            safe_title = safe_title[:255].strip()
            base_name = safe_title
        else:
            # Use path structure
            base_name = path.split("/")[-1] if path else "index"

        return f"{base_name}_aggregated.md"


@dataclass
class CrawlResult:
    """Summary of crawl operation results."""

    # Configuration
    config: "CrawlConfig"

    # Job information
    job: Optional[CrawlJob] = None

    # Page results
    pages_scraped: list[ScrapedPage] = field(default_factory=list)
    files_created: list[MarkdownFile] = field(default_factory=list)
    aggregated_files: list[AggregatedMarkdownFile] = field(default_factory=list)

    # Statistics
    total_pages: int = 0
    successful_pages: int = 0
    failed_pages: int = 0
    skipped_pages: int = 0  # Outside boundary, duplicates, etc.

    # Errors
    errors: list[str] = field(default_factory=list)

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

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

        if self.aggregated_files:
            lines.extend([
                "",
                f"Aggregated Files: {len(self.aggregated_files)}",
            ])
            for agg_file in self.aggregated_files:
                lines.append(f"  - {agg_file.relative_path} ({len(agg_file.source_urls)} pages)")

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
