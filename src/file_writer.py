"""File system operations for writing Markdown files."""

import logging
from pathlib import Path
from typing import Optional

from .models import MarkdownFile, AggregatedMarkdownFile


logger = logging.getLogger(__name__)


def write_markdown_file(
    markdown_file: MarkdownFile,
    overwrite: bool = False
) -> bool:
    """
    Write Markdown file to disk with directory creation and error handling.

    Args:
        markdown_file: MarkdownFile object to write
        overwrite: Whether to overwrite existing files

    Returns:
        True if successful, False otherwise
    """
    try:
        if not markdown_file.absolute_path:
            logger.error(f"No absolute path for MarkdownFile: {markdown_file.relative_path}")
            return False

        output_path = Path(markdown_file.absolute_path)

        # Check if file exists
        if output_path.exists() and not overwrite:
            logger.warning(f"File already exists, skipping: {output_path}")
            return False

        # Create parent directories
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file with frontmatter
        content = markdown_file.with_frontmatter()
        output_path.write_text(content, encoding='utf-8')

        logger.info(f"File created: {output_path}")
        return True

    except PermissionError as e:
        logger.error(f"Permission denied writing file: {markdown_file.absolute_path} - {e}")
        return False
    except OSError as e:
        logger.error(f"Failed to write file: {markdown_file.absolute_path} - {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error writing file: {markdown_file.absolute_path} - {e}")
        return False


def write_aggregated_file(
    aggregated_file: AggregatedMarkdownFile,
    overwrite: bool = False
) -> bool:
    """
    Write aggregated Markdown file to disk with directory creation and error handling.

    Args:
        aggregated_file: AggregatedMarkdownFile object to write
        overwrite: Whether to overwrite existing files

    Returns:
        True if successful, False otherwise
    """
    try:
        if not aggregated_file.absolute_path:
            logger.error(f"No absolute path for AggregatedMarkdownFile: {aggregated_file.relative_path}")
            return False

        output_path = Path(aggregated_file.absolute_path)

        # Check if file exists
        if output_path.exists() and not overwrite:
            logger.warning(f"File already exists, skipping: {output_path}")
            return False

        # Create parent directories
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file with frontmatter
        content = aggregated_file.with_frontmatter()
        output_path.write_text(content, encoding='utf-8')

        logger.info(f"Aggregated file created: {output_path} ({len(aggregated_file.source_urls)} pages)")
        return True

    except PermissionError as e:
        logger.error(f"Permission denied writing aggregated file: {aggregated_file.absolute_path} - {e}")
        return False
    except OSError as e:
        logger.error(f"Failed to write aggregated file: {aggregated_file.absolute_path} - {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error writing aggregated file: {aggregated_file.absolute_path} - {e}")
        return False
