# Quickstart Guide: Website to Markdown Crawler

**Feature**: [001-website-crawler](spec.md)
**Branch**: `001-website-crawler`
**Last Updated**: 2026-01-10

## Overview

This guide helps you quickly set up and run the VBA documentation crawler that converts web pages to Markdown files using the Firecrawl API.

## Prerequisites

### 1. Firecrawl Local Service

You must have Firecrawl running locally at `http://localhost:3002`.

**Installation** (if not already running):

```bash
# Using Docker (recommended)
docker run -p 3002:3002 -e API_KEY=fc-test firecrawl/firecrawl:latest

# Or using npm if you have Node.js installed
npm install -g firecrawl
firecrawl start --port 3002
```

**Verify Firecrawl is running**:

```bash
curl http://localhost:3002
# Should return API documentation or status page
```

### 2. Python Environment

- Python 3.11 or higher
- pip (Python package installer)

**Check Python version**:

```bash
python --version
# Should show Python 3.11.x or higher
```

## Installation

### 1. Clone Repository

```bash
git clone <repository-url>
cd crawl-website
git checkout 001-website-crawler
```

### 2. Install Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

**Expected packages in `requirements.txt`**:

```txt
firecrawl-py>=0.0.1
requests>=2.31.0
```

### 3. Verify Installation

```bash
python -c "import firecrawl; import requests; print('Dependencies installed successfully')"
```

## Configuration

### Environment Variables (Optional)

Create a `.env` file in the project root:

```bash
# Firecrawl Configuration
FIRECRAWL_API_URL=http://localhost:3002
FIRECRAWL_API_KEY=fc-test

# Crawler Behavior
CRAWLER_MAX_PAGES=200
CRAWLER_TIMEOUT_SECONDS=120
CRAWLER_OUTPUT_DIR=./output

# Logging
LOG_LEVEL=INFO
```

### CLI Arguments (Override Environment)

The crawler accepts command-line arguments to override configuration:

```bash
python -m src.cli --help
```

**Expected arguments**:
- `--url`: Starting URL (required)
- `--output-dir`: Output directory (default: `./output`)
- `--max-pages`: Maximum pages to crawl (default: 200)
- `--timeout`: Request timeout in seconds (default: 120)
- `--verbose`: Enable debug logging
- `--overwrite`: Overwrite existing files

## Usage Examples

### Example 1: Crawl Single Page (User Story 1)

Convert a single VBA documentation page to Markdown:

```bash
python -m src.cli \
  --url "https://dict.thinktrader.net/VBA/start_now.html" \
  --output-dir ./output \
  --max-pages 1
```

**Expected output**:
```
2026-01-10 10:00:00 - INFO - Starting crawl from https://dict.thinktrader.net/VBA/start_now.html
2026-01-10 10:00:01 - INFO - Scraping page: https://dict.thinktrader.net/VBA/start_now.html
2026-01-10 10:00:03 - INFO - Successfully scraped: start_now.html
2026-01-10 10:00:03 - INFO - Writing file: ./output/start_now.md
2026-01-10 10:00:03 - INFO - File created successfully

=== Crawl Summary ===
Started: 2026-01-10T10:00:00
Completed: 2026-01-10T10:00:03
Duration: 3.00s

Pages:
  Total: 1
  Successful: 1
  Failed: 0
  Success Rate: 100.0%

Files Created: 1
```

**Result**: `./output/start_now.md` containing the converted Markdown content.

### Example 2: Crawl Entire VBA Section (User Story 2)

Crawl all pages within the `/VBA/` path:

```bash
python -m src.cli \
  --url "https://dict.thinktrader.net/VBA/start_now.html" \
  --output-dir ./vba-docs \
  --max-pages 200 \
  --verbose
```

**Expected behavior**:
1. Submit crawl job to Firecrawl API
2. Poll job status every 2 seconds
3. Firecrawl discovers all linked pages within `/VBA/`
4. Each page is scraped and converted to Markdown
5. Files are saved with directory structure matching URL hierarchy

**Result**: `./vba-docs/` directory with:
```
vba-docs/
├── start_now.md
├── chapter1/
│   ├── lesson1.md
│   └── lesson2.md
├── chapter2/
│   ├── functions.md
│   └── examples.md
└── ...
```

### Example 3: Custom Output Directory

Specify a custom output location:

```bash
python -m src.cli \
  --url "https://dict.thinktrader.net/VBA/start_now.html" \
  --output-dir "C:\Users\YourName\Documents\VBA Docs" \
  --max-pages 50
```

### Example 4: Debug Mode

Enable verbose logging for troubleshooting:

```bash
python -m src.cli \
  --url "https://dict.thinktrader.net/VBA/start_now.html" \
  --verbose \
  --max-pages 5
```

**Expected output**:
- DEBUG level logs showing API requests/responses
- URL validation details
- Filename generation logic
- Network retry attempts

## Understanding the Output

### File Structure

The crawler creates a directory structure mirroring the URL hierarchy:

```
output/
├── start_now.md                          # /VBA/start_now.html
├── chapter1/                             # /VBA/chapter1/
│   ├── introduction.md                   # /VBA/chapter1/introduction.html
│   └── basics.md                         # /VBA/chapter1/basics.html
└── functions/                            # /VBA/functions/
    └── reference.md                      # /VBA/functions/reference.html
```

### Markdown File Format

Each `.md` file includes:

**YAML Frontmatter**:
```yaml
---
title: VBA Functions Reference
source_url: https://dict.thinktrader.net/VBA/functions/reference.html
scraped_at: 2026-01-10T10:05:30.123456
---
```

**Content**:
```markdown
# VBA Functions Reference

This guide covers all built-in VBA functions...
```

## Troubleshooting

### Issue 1: Firecrawl Service Unavailable

**Error**:
```
ERROR - Failed to connect to Firecrawl service at http://localhost:3002
```

**Solution**:
1. Verify Firecrawl is running: `curl http://localhost:3002`
2. Check Firecrawl logs for errors
3. Restart Firecrawl service

### Issue 2: No Pages Scraped

**Error**:
```
WARNING - Crawl completed but no pages were returned
```

**Solution**:
1. Verify starting URL is accessible in browser
2. Check if page requires JavaScript (Firecrawl handles this, but may need longer timeout)
3. Try with `--max-pages 1` for single-page debugging
4. Enable `--verbose` to see API responses

### Issue 3: Files Not Created

**Error**:
```
ERROR - Failed to write file: Permission denied
```

**Solution**:
1. Check output directory permissions
2. Ensure output directory exists or is creatable
3. Try different output directory: `--output-dir ./test-output`

### Issue 4: URL Boundary Violation

**Error**:
```
ERROR - URL outside allowed boundary: https://example.com/page.html
```

**Solution**:
- This is expected behavior - the crawler enforces strict `/VBA/` path boundary
- Check if Firecrawl is discovering external links
- Verify URL validation logic is working correctly

### Issue 5: Rate Limiting

**Error**:
```
WARNING - Rate limit exceeded, retrying in 60s...
```

**Solution**:
- Normal behavior - crawler will automatically retry with exponential backoff
- To avoid rate limits, reduce `--max-pages` or increase `--timeout`

## Development Workflow

### Running Tests (Optional)

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_url_utils.py
```

### Code Quality

```bash
# Format code
black src/ tests/

# Type checking
mypy src/

# Linting
flake8 src/
```

## Next Steps

1. **Run your first crawl**: Start with Example 1 (single page)
2. **Verify output**: Check generated Markdown files
3. **Scale up**: Run full crawl with Example 2
4. **Customize**: Adjust configuration as needed

## Additional Resources

- [Feature Specification](spec.md) - Detailed requirements
- [Implementation Plan](plan.md) - Technical design
- [Data Model](data-model.md) - Entity definitions
- [API Contract](contracts/firecrawl-api.yaml) - Firecrawl API specification
- [Research Findings](research.md) - Technical decisions

## Support

For issues or questions:
1. Check [Troubleshooting](#troubleshooting) section above
2. Review logs with `--verbose` flag
3. Consult Firecrawl documentation: https://docs.firecrawl.dev
4. Check project issues (if repository has issue tracker)
