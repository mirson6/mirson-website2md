"""Unit tests for markdown_optimizer module."""

import pytest

from src.markdown_optimizer import (
    analyze_heading_structure,
    normalize_heading_levels,
    generate_table_of_contents,
    insert_toc_into_markdown,
    normalize_multi_page_content,
    TOCPosition,
    HeadingNode,
    HeadingNormalizationReport,
    _generate_anchor_id
)


class TestGenerateAnchorId:
    """Tests for _generate_anchor_id function."""

    def test_simple_title(self):
        counts = {}
        result = _generate_anchor_id("Introduction", counts)
        assert result == "introduction"

    def test_title_with_special_chars(self):
        counts = {}
        result = _generate_anchor_id("Hello, World!", counts)
        assert result == "hello-world"

    def test_duplicate_titles(self):
        counts = {"introduction": 1}
        result = _generate_anchor_id("Introduction", counts)
        assert result == "introduction-1"

    def test_empty_title(self):
        counts = {}
        result = _generate_anchor_id("", counts)
        assert result == "heading"


class TestAnalyzeHeadingStructure:
    """Tests for analyze_heading_structure function."""

    def test_atx_headings(self):
        markdown = """# Title 1
## Title 2
### Title 3
"""
        headings = analyze_heading_structure(markdown)
        assert len(headings) == 3
        assert headings[0].level == 1
        assert headings[0].title == "Title 1"
        assert headings[1].level == 2
        assert headings[1].title == "Title 2"
        assert headings[2].level == 3
        assert headings[2].title == "Title 3"

    def test_setext_headings(self):
        markdown = """Title 1
===
Title 2
---
"""
        headings = analyze_heading_structure(markdown)
        assert len(headings) == 2
        assert headings[0].level == 1
        assert headings[0].title == "Title 1"
        assert headings[1].level == 2
        assert headings[1].title == "Title 2"

    def test_mixed_heading_styles(self):
        markdown = """# ATX Heading
Content here
## Another ATX
Content
Setext Heading
===
More content
Another Setext
---
"""
        headings = analyze_heading_structure(markdown)
        assert len(headings) == 4
        assert headings[0].title == "ATX Heading"
        assert headings[0].level == 1
        assert headings[1].title == "Another ATX"
        assert headings[1].level == 2
        assert headings[2].title == "Setext Heading"
        assert headings[2].level == 1
        assert headings[3].title == "Another Setext"
        assert headings[3].level == 2

    def test_atx_heading_with_trailing_hashes(self):
        markdown = """# Title with hashes ###
## Another ## """
        headings = analyze_heading_structure(markdown)
        assert len(headings) == 2
        assert headings[0].title == "Title with hashes"
        assert headings[1].title == "Another"

    def test_empty_markdown(self):
        headings = analyze_heading_structure("")
        assert len(headings) == 0

    def test_no_headings(self):
        markdown = """This is just plain text.
No headings here.
Just paragraphs."""
        headings = analyze_heading_structure(markdown)
        assert len(headings) == 0

    def test_unique_anchor_ids(self):
        markdown = """# Introduction
## Introduction
### Introduction"""
        headings = analyze_heading_structure(markdown)
        assert len(headings) == 3
        assert headings[0].anchor_id == "introduction"
        assert headings[1].anchor_id == "introduction-1"
        assert headings[2].anchor_id == "introduction-2"

    def test_deeply_nested_headings(self):
        markdown = """# H1
## H2
### H3
#### H4
##### H5
###### H6"""
        headings = analyze_heading_structure(markdown)
        assert len(headings) == 6
        assert headings[0].level == 1
        assert headings[5].level == 6


class TestNormalizeHeadingLevels:
    """Tests for normalize_heading_levels function."""

    def test_no_normalization_needed(self):
        markdown = "# Title\n\n## Subtitle\n\nContent"
        normalized, report = normalize_heading_levels(markdown, base_level=1)
        assert normalized == markdown
        assert report.original_headings == 2
        assert report.normalized_headings == 2

    def test_shift_headings_by_one(self):
        markdown = "# Title\n\n## Subtitle\n\n### Section"
        normalized, report = normalize_heading_levels(markdown, base_level=2)
        assert "## Title" in normalized
        assert "### Subtitle" in normalized
        assert "#### Section" in normalized
        assert report.base_level_shift == 1

    def test_shift_headings_by_two(self):
        markdown = "# Title\n\n## Subtitle"
        normalized, report = normalize_heading_levels(markdown, base_level=3)
        assert "### Title" in normalized
        assert "#### Subtitle" in normalized
        assert report.base_level_shift == 2

    def test_max_heading_level(self):
        markdown = "###### H6\n\n# H1"
        normalized, report = normalize_heading_levels(markdown, base_level=2)
        # H6 should stay at 6 (max level)
        assert "# H1" not in normalized  # H1 shifted to H2
        assert report.conflicts_resolved >= 1

    def test_empty_markdown(self):
        normalized, report = normalize_heading_levels("", base_level=2)
        assert normalized == ""
        assert report.original_headings == 0

    def test_no_headings_in_markdown(self):
        markdown = "Just plain text\n\nNo headings here"
        normalized, report = normalize_heading_levels(markdown, base_level=2)
        assert normalized == markdown
        assert report.original_headings == 0


class TestNormalizeMultiPageContent:
    """Tests for normalize_multi_page_content function."""

    def test_single_page_no_shift(self):
        pages = ["# Page 1\n\n## Section 1"]
        normalized, report = normalize_multi_page_content(pages, preserve_first_h1=True)
        assert "# Page 1" in normalized
        assert report.pages_normalized == 1
        assert report.base_level_shift == 0

    def test_multiple_pages_with_shift(self):
        pages = [
            "# Page 1\n\n## Section 1",
            "# Page 2\n\n## Section 2",
            "# Page 3\n\n## Section 3"
        ]
        normalized, report = normalize_multi_page_content(pages, preserve_first_h1=True)
        # First page keeps H1
        assert "# Page 1" in normalized
        # Subsequent pages shifted to H2
        assert "## Page 2" in normalized
        assert "## Page 3" in normalized
        assert report.pages_normalized == 3
        assert report.base_level_shift == 1

    def test_empty_page_list(self):
        normalized, report = normalize_multi_page_content([])
        assert normalized == ""
        assert report.pages_normalized == 0


class TestGenerateTableOfContents:
    """Tests for generate_table_of_contents function."""

    def test_simple_toc(self):
        headings = [
            HeadingNode(level=1, title="Title 1", anchor_id="title-1", line_number=1),
            HeadingNode(level=2, title="Title 2", anchor_id="title-2", line_number=2),
            HeadingNode(level=3, title="Title 3", anchor_id="title-3", line_number=3),
        ]
        toc = generate_table_of_contents(headings, max_level=3)
        assert "## Table of Contents" in toc
        assert "[Title 1](#title-1)" in toc
        assert "[Title 2](#title-2)" in toc
        assert "[Title 3](#title-3)" in toc

    def test_toc_with_max_level_filtering(self):
        headings = [
            HeadingNode(level=1, title="H1", anchor_id="h1", line_number=1),
            HeadingNode(level=2, title="H2", anchor_id="h2", line_number=2),
            HeadingNode(level=3, title="H3", anchor_id="h3", line_number=3),
            HeadingNode(level=4, title="H4", anchor_id="h4", line_number=4),
        ]
        toc = generate_table_of_contents(headings, max_level=2)
        assert "[H1](#h1)" in toc
        assert "[H2](#h2)" in toc
        assert "[H3](#h3)" not in toc  # Filtered out
        assert "[H4](#h4)" not in toc  # Filtered out

    def test_toc_with_custom_title(self):
        headings = [
            HeadingNode(level=1, title="Title", anchor_id="title", line_number=1),
        ]
        toc = generate_table_of_contents(headings, title="Contents")
        assert "## Contents" in toc

    def test_empty_headings_list(self):
        toc = generate_table_of_contents([])
        assert toc == ""

    def test_all_headings_filtered_out(self):
        headings = [
            HeadingNode(level=4, title="Deep", anchor_id="deep", line_number=1),
        ]
        toc = generate_table_of_contents(headings, max_level=3)
        assert toc == ""


class TestInsertTocIntoMarkdown:
    """Tests for insert_toc_into_markdown function."""

    def test_insert_at_document_start(self):
        markdown = "# Title\n\nContent"
        toc = "\n## TOC\n\n- [Link](#anchor)\n"
        result = insert_toc_into_markdown(markdown, toc, TOCPosition.DOCUMENT_START)
        assert result.startswith(toc.strip())
        assert "# Title" in result

    def test_insert_after_frontmatter(self):
        markdown = """---
title: Test
---

# Content"""
        toc = "\n## TOC\n\n- [Link](#anchor)\n"
        result = insert_toc_into_markdown(markdown, toc, TOCPosition.AFTER_FRONTMATTER)
        assert result.startswith("---\ntitle: Test\n---")
        assert "## TOC" in result

    def test_insert_before_first_heading(self):
        markdown = "Content here\n\n# Heading\n\nMore content"
        toc = "\n## TOC\n\n- [Link](#anchor)\n"
        result = insert_toc_into_markdown(markdown, toc, TOCPosition.BEFORE_FIRST_HEADING)
        lines = result.split("\n")
        heading_idx = next(i for i, line in enumerate(lines) if line.startswith("# Heading"))
        # TOC should be before heading
        toc_idx = next(i for i, line in enumerate(lines) if "## TOC" in line)
        assert toc_idx < heading_idx

    def test_empty_toc(self):
        markdown = "# Title\n\nContent"
        result = insert_toc_into_markdown(markdown, "", TOCPosition.DOCUMENT_START)
        assert result == markdown

    def test_no_frontmatter(self):
        markdown = "# Title\n\nContent"
        toc = "\n## TOC\n\n- [Link](#anchor)\n"
        result = insert_toc_into_markdown(markdown, toc, TOCPosition.AFTER_FRONTMATTER)
        # Should insert at start when no frontmatter
        assert result.startswith(toc.strip())
