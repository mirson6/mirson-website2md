"""URL utilities for validation, boundary checking, and filename generation."""

import hashlib
import re
from urllib.parse import urlparse


def is_allowed_url(url: str, base_path: str = "/VBA/") -> bool:
    """
    Validate URL is within allowed boundary.

    Args:
        url: URL to validate
        base_path: Required base path (default: /VBA/)

    Returns:
        True if URL is within allowed boundary, False otherwise
    """
    try:
        parsed = urlparse(url)
        # Check domain
        if parsed.netloc != "dict.thinktrader.net":
            return False
        # Check path starts with /VBA/
        if not parsed.path.startswith(base_path):
            return False
        return True
    except Exception:
        return False


def sanitize_filename(name: str) -> str:
    """
    Remove invalid filesystem characters from filename.

    Args:
        name: Proposed filename

    Returns:
        Sanitized filename safe for filesystem
    """
    # Remove invalid characters: < > : " / \ | ? *
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '_')
    # Limit length
    return name[:255].strip()


def generate_filename(url: str, metadata: dict) -> str:
    """
    Generate safe filename from URL or metadata.

    Priority order:
    1. Page title from metadata
    2. URL path structure
    3. URL hash as fallback

    Args:
        url: Source URL
        metadata: Page metadata dict (may contain 'title' field)

    Returns:
        Safe filename with .md extension
    """
    # Priority 1: Use page title from metadata
    if "title" in metadata and metadata["title"]:
        title = metadata["title"]
        filename = sanitize_filename(title)
    else:
        # Priority 2: Extract from URL path
        path = urlparse(url).path
        # Remove /VBA/ prefix and .html suffix
        filename = path.replace("/VBA/", "").replace(".html", "")
        if not filename or filename == "/":
            # Priority 3: Use URL hash as fallback
            filename = hashlib.md5(url.encode()).hexdigest()[:8]

    return f"{filename}.md"
