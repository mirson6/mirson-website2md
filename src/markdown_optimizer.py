"""Markdown structure optimization for TOC generation and heading normalization."""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


logger = logging.getLogger(__name__)


class TOCPosition(Enum):
    """Position for TOC insertion in Markdown document."""

    AFTER_FRONTMATTER = "after_frontmatter"  # After YAML frontmatter (recommended)
    BEFORE_FIRST_HEADING = "before_first_heading"  # Before first H1
    DOCUMENT_START = "document_start"  # At very beginning


@dataclass
class HeadingNode:
    """Represents a heading in a Markdown document."""

    level: int  # 1-6
    title: str  # Heading text
    anchor_id: str  # Unique ID for linking
    line_number: int  # Position in document
    children: list["HeadingNode"] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"HeadingNode(level={self.level}, title='{self.title}', id='{self.anchor_id}')"


@dataclass
class HeadingNormalizationReport:
    """Statistics from heading normalization process."""

    original_headings: int
    normalized_headings: int
    base_level_shift: int
    pages_normalized: int
    conflicts_resolved: int


def analyze_heading_structure(markdown: str) -> list[HeadingNode]:
    """
    Parse Markdown and extract heading hierarchy.

    Detects both ATX-style headings (#, ##, etc.) and Setext-style headings (===, ---).
    Builds a hierarchical tree structure and generates unique anchor IDs.

    Args:
        markdown: Markdown content to analyze

    Returns:
        List of HeadingNode with level, title, anchor_id, line_number
    """
    if not markdown:
        return []

    headings = []
    lines = markdown.split("\n")
    anchor_counts = {}  # Track duplicate heading titles

    for line_num, line in enumerate(lines, start=1):
        # Check for ATX-style headings
        atx_match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if atx_match:
            level = len(atx_match.group(1))
            title = atx_match.group(2).strip()

            # Remove trailing #s from ATX headings
            title = re.sub(r'\s*#+\s*$', '', title).strip()

            # Generate unique anchor ID
            anchor_id = _generate_anchor_id(title, anchor_counts)
            anchor_counts[anchor_id] = anchor_counts.get(anchor_id, 0) + 1

            node = HeadingNode(
                level=level,
                title=title,
                anchor_id=anchor_id,
                line_number=line_num
            )
            headings.append(node)
            continue

        # Check for Setext-style headings (underlines with === or ---)
        # Need to check previous line
        if line_num > 1:
            setext_match = re.match(r'^(=+|-+)\s*$', line)
            if setext_match and setext_match.group(1):
                prev_line = lines[line_num - 2].strip()

                # Determine level based on underline character
                level = 1 if setext_match.group(1).startswith('=') else 2

                # Generate unique anchor ID
                anchor_id = _generate_anchor_id(prev_line, anchor_counts)
                anchor_counts[anchor_id] = anchor_counts.get(anchor_id, 0) + 1

                node = HeadingNode(
                    level=level,
                    title=prev_line,
                    anchor_id=anchor_id,
                    line_number=line_num - 1  # Heading is on previous line
                )
                headings.append(node)

    logger.info(f"Analyzed {len(headings)} headings in markdown content")
    return headings


def _generate_anchor_id(title: str, counts: dict) -> str:
    """
    Generate a unique anchor ID from heading title.

    Args:
        title: Heading title
        counts: Dictionary tracking ID usage counts

    Returns:
        Unique anchor ID suitable for Markdown linking
    """
    # Convert to lowercase, replace spaces with hyphens, remove special chars
    base_id = title.lower()
    base_id = re.sub(r'[^\w\s-]', '', base_id)  # Remove special chars
    base_id = re.sub(r'\s+', '-', base_id)  # Spaces to hyphens
    base_id = base_id.strip('-')

    # Handle empty titles
    if not base_id:
        base_id = 'heading'

    # Handle duplicates
    count = counts.get(base_id, 0)
    if count > 0:
        return f"{base_id}-{count}"

    return base_id


def normalize_heading_levels(
    markdown: str,
    base_level: int = 2
) -> tuple[str, HeadingNormalizationReport]:
    """
    Shift all headings to maintain proper hierarchy in aggregated documents.

    Strategy:
    1. Parse document to find all headings
    2. Shift headings by base_level offset
    3. Ensure nested hierarchy (no skipping levels: H1 -> H3)
    4. Preserve relative heading levels within content

    Args:
        markdown: Markdown content to normalize
        base_level: Starting level for first H1 (2 means H1 becomes H2)

    Returns:
        Tuple of (normalized_markdown, report_with_stats)
    """
    if not markdown:
        return markdown, HeadingNormalizationReport(0, 0, 0, 0, 0)

    lines = markdown.split("\n")
    normalized_lines = []
    original_count = 0
    normalized_count = 0
    conflicts_resolved = 0

    for line in lines:
        # Check for ATX-style headings
        atx_match = re.match(r'^(#{1,6})(\s+)(.+)$', line)
        if atx_match:
            original_count += 1
            original_level = len(atx_match.group(1))
            spaces = atx_match.group(2)
            content = atx_match.group(3)

            # Calculate new level
            new_level = original_level + base_level - 1

            # Ensure level doesn't exceed 6
            if new_level > 6:
                new_level = 6
                conflicts_resolved += 1

            # Create new heading line
            new_line = f"{'#' * new_level}{spaces}{content}"
            normalized_lines.append(new_line)
            normalized_count += 1
            continue

        # Check for Setext-style headings
        setext_match = re.match(r'^(=+|-+)\s*$', line)
        if setext_match and setext_match.group(1):
            original_count += 1
            underline = setext_match.group(1)

            # Determine current level from underline character
            is_h1 = underline.startswith('=')
            original_level = 1 if is_h1 else 2

            # Calculate new level
            new_level = original_level + base_level - 1

            # Can't represent Setext-style headings above H2
            # Convert to ATX-style if needed
            if new_level > 2:
                # Need to find the heading text from previous line
                if normalized_lines:
                    prev_line = normalized_lines[-1]
                    # Convert to ATX-style heading
                    new_heading_line = f"{'#' * new_level} {prev_line}"
                    normalized_lines[-1] = new_heading_line
                    normalized_count += 1
                    conflicts_resolved += 1
                # Skip the underline
                continue
            else:
                # Adjust underline (change = to - if needed)
                if new_level == 2 and is_h1:
                    normalized_lines.append('-' * len(underline))
                else:
                    normalized_lines.append(underline)
                normalized_count += 1
                continue

        # Not a heading, keep as-is
        normalized_lines.append(line)

    normalized_markdown = "\n".join(normalized_lines)

    report = HeadingNormalizationReport(
        original_headings=original_count,
        normalized_headings=normalized_count,
        base_level_shift=base_level - 1,
        pages_normalized=1,
        conflicts_resolved=conflicts_resolved
    )

    logger.info(
        f"Normalized {normalized_count} headings with base level {base_level} "
        f"({conflicts_resolved} conflicts resolved)"
    )

    return normalized_markdown, report


def generate_table_of_contents(
    headings: list[HeadingNode],
    max_level: int = 3,
    title: str = "Table of Contents"
) -> str:
    """
    Generate Markdown TOC from heading list.

    Format:
    ## Table of Contents

    - [Heading 1](#heading-1)
      - [Heading 2](#heading-2)
        - [Heading 3](#heading-3)

    Args:
        headings: List of HeadingNode objects
        max_level: Maximum heading level to include in TOC (default: 3)
        title: Title for the TOC section

    Returns:
        Markdown formatted table of contents
    """
    if not headings:
        logger.warning("No headings provided for TOC generation")
        return ""

    # Filter headings by max_level
    filtered_headings = [h for h in headings if h.level <= max_level]

    if not filtered_headings:
        logger.warning(f"No headings found within max_level {max_level}")
        return ""

    # Build TOC lines
    toc_lines = [f"\n## {title}\n"]

    for heading in filtered_headings:
        # Calculate indentation based on level
        indent = "  " * (heading.level - 1)
        # Create link
        link = f"- [{heading.title}](#{heading.anchor_id})"
        toc_lines.append(f"{indent}{link}")

    toc = "\n".join(toc_lines) + "\n"

    logger.info(f"Generated TOC with {len(filtered_headings)} entries (max_level={max_level})")

    return toc


def insert_toc_into_markdown(
    markdown: str,
    toc: str,
    position: TOCPosition = TOCPosition.AFTER_FRONTMATTER
) -> str:
    """
    Insert TOC at optimal position in document.

    Args:
        markdown: Markdown content
        toc: Table of contents to insert
        position: Where to insert the TOC

    Returns:
        Markdown with TOC inserted
    """
    if not toc:
        return markdown

    if position == TOCPosition.DOCUMENT_START:
        return toc + "\n" + markdown

    if position == TOCPosition.BEFORE_FIRST_HEADING:
        # Find first heading and insert before it
        lines = markdown.split("\n")
        for i, line in enumerate(lines):
            if re.match(r'^#{1,6}\s+', line):
                lines.insert(i, toc)
                return "\n".join(lines)
        # No heading found, append at end
        return markdown + "\n" + toc

    if position == TOCPosition.AFTER_FRONTMATTER:
        # Check for YAML frontmatter (starts with ---)
        lines = markdown.split("\n")

        # Look for frontmatter end
        if len(lines) > 0 and lines[0].strip() == "---":
            # Find the closing ---
            for i, line in enumerate(lines[1:], start=1):
                if line.strip() == "---":
                    # Insert TOC after frontmatter
                    lines.insert(i + 1, toc)
                    return "\n".join(lines)

        # No frontmatter found, insert at beginning
        return toc + "\n" + markdown

    # Default: append at end
    return markdown + "\n" + toc


def normalize_multi_page_content(
    markdown_sections: list[str],
    preserve_first_h1: bool = True
) -> tuple[str, HeadingNormalizationReport]:
    """
    Normalize heading levels across multiple page sections.

    First page keeps H1, subsequent pages have headings shifted by 1 level.

    Args:
        markdown_sections: List of markdown content from each page
        preserve_first_h1: Whether to keep first page's H1 (default: True)

    Returns:
        Tuple of (combined_normalized_markdown, report)
    """
    if not markdown_sections:
        return "", HeadingNormalizationReport(0, 0, 0, 0, 0)

    normalized_sections = []
    total_original = 0
    total_normalized = 0
    total_conflicts = 0

    for i, section in enumerate(markdown_sections):
        if i == 0 and preserve_first_h1:
            # First page: no shifting (base_level = 1)
            normalized, report = normalize_heading_levels(section, base_level=1)
        else:
            # Subsequent pages: shift by 1 (base_level = 2)
            normalized, report = normalize_heading_levels(section, base_level=2)

        normalized_sections.append(normalized)
        total_original += report.original_headings
        total_normalized += report.normalized_headings
        total_conflicts += report.conflicts_resolved

    combined = "\n\n".join(normalized_sections)

    report = HeadingNormalizationReport(
        original_headings=total_original,
        normalized_headings=total_normalized,
        base_level_shift=1,
        pages_normalized=len(markdown_sections),
        conflicts_resolved=total_conflicts
    )

    logger.info(
        f"Normalized {len(markdown_sections)} pages: "
        f"{total_normalized} headings total, {total_conflicts} conflicts"
    )

    return combined, report
