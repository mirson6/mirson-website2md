# Implementation Plan: Website to Markdown Crawler

**Branch**: `001-website-crawler` | **Date**: 2026-01-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-website-crawler/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Build a Python CLI tool that crawls VBA documentation from `https://dict.thinktrader.net/VBA/` and converts all pages to Markdown files using the Firecrawl API (local service at `http://localhost:3002`). The tool enforces strict URL path boundaries, generates filenames from page titles or URL paths, maintains directory structure matching the URL hierarchy, and provides comprehensive error handling for network operations.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**:
- Firecrawl (local service via Python SDK or HTTP client)
- requests (HTTP client for API calls)
- Standard library: pathlib, urllib, argparse, logging, json

**Storage**: Local filesystem (Markdown files in directory structure)
**Testing**: pytest with mocking for network operations (optional per constitution)
**Target Platform**: Cross-platform (Windows, Linux, macOS) - CLI tool
**Project Type**: Single project (Python CLI tool)
**Performance Goals**:
- Process 100 pages in under 5 minutes (per spec SC-006)
- Handle network errors without crashing
- Support concurrent processing when Firecrawl API allows

**Constraints**:
- Must respect Firecrawl API rate limits and timeout constraints
- Must enforce strict URL boundary: only `https://dict.thinktrader.net/VBA/*` paths
- Must handle Firecrawl service unavailability gracefully
- Must work with local Firecrawl instance at `http://localhost:3002`

**Scale/Scope**:
- Target: VBA documentation site (estimated 50-200 pages)
- Single-site crawler (not general-purpose)
- Output: 50-200 Markdown files with directory hierarchy
- URL deduplication to prevent infinite loops

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. API-First Development ✅

**Status**: PASS - This feature leverages Firecrawl API as the primary HTML parsing and Markdown conversion engine.

**Compliance**:
- Uses external Firecrawl service instead of building custom HTML parser
- Firecrawl provides specialized web scraping, Markdown conversion, and crawling capabilities
- API abstraction layer will be implemented to enable service replacement if needed
- Comprehensive error handling for API failures (per Principle II)

**Rationale**: Firecrawl is specifically designed for web scraping and Markdown conversion, offering proven reliability, active maintenance, and clear documentation. Building equivalent functionality would require significant custom code for HTML parsing, JavaScript rendering, link extraction, and Markdown conversion.

### II. Network Error Handling ✅

**Status**: PASS - Comprehensive network error handling is a core requirement.

**Compliance**:
- FR-011: System MUST handle network errors gracefully (timeouts, connection failures, HTTP errors)
- All Firecrawl API calls will include explicit timeout configuration
- Error handling for connection failures, DNS issues, HTTP 4xx/5xx responses
- Retry logic with exponential backoff for transient failures
- Maximum retry limits to prevent infinite loops
- Detailed error logging with context (URL, operation, error type, timestamp)
- Circuit breaker pattern for repeated Firecrawl service failures
- Distinguish between transient (retryable) and permanent errors

**Implementation**:
- Wrap all Firecrawl API calls in try-except blocks with specific exception handling
- Use requests library's timeout and retry mechanisms
- Log all network operations (request initiation, response status, timing, errors)
- Implement graceful degradation when Firecrawl service is unavailable

### III. Code Quality ✅

**Status**: PASS - Python best practices will be followed.

**Compliance**:
- PEP 8 style guide compliance
- Type hints for all function signatures
- Docstrings for all public functions and classes
- Descriptive variable and function names
- Context managers for file operations
- Functions kept focused and under 50 lines
- Composition over inheritance
- Maximum nesting depth of 4 levels

### IV. Simplicity ✅

**Status**: PASS - Solution prioritizes simplicity using Firecrawl API.

**Compliance**:
- Single CLI tool with focused responsibility
- Leverages external API instead of building complex crawling logic
- Standard library usage where possible (pathlib, argparse, logging)
- No premature optimization or over-engineering
- YAGNI principles applied - only implement required features
- Delete unused code; don't comment out

**Constitution Check Result**: ✅ ALL GATES PASSED - Proceed to Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/001-website-crawler/
├── plan.md              # This file (/speckit.plan command output)
├── spec.md              # Feature specification
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── firecrawl-api.yaml  # Firecrawl API contract
└── checklists/
    └── requirements.md  # Specification quality checklist
```

### Source Code (repository root)

```text
src/
├── __init__.py
├── crawler.py           # Main crawler orchestration logic
├── firecrawl_client.py  # Firecrawl API client wrapper with error handling
├── url_utils.py         # URL validation, boundary checking, filename generation
├── file_writer.py       # File system operations, directory creation
└── cli.py               # Command-line interface (argparse, logging setup)

tests/
├── __init__.py
├── contract/            # Contract tests for Firecrawl API interactions
│   └── test_firecrawl_api.py
├── integration/         # Integration tests for end-to-end crawling
│   └── test_crawler_workflow.py
└── unit/                # Unit tests for individual components
    ├── test_firecrawl_client.py
    ├── test_url_utils.py
    └── test_file_writer.py

README.md                # Installation, usage, configuration
requirements.txt         # Python dependencies
pyproject.toml          # Project metadata and build configuration
.gitignore              # Git ignore patterns
```

**Structure Decision**: Single project structure (Option 1) is appropriate because:
- This is a standalone CLI tool, not a web or mobile application
- All code runs in a single Python process
- No separation between frontend/backend needed
- Tests organized by type (unit, integration, contract) following Python best practices

## Complexity Tracking

> No constitution violations requiring justification. All gates passed.

No complexity tracking required. The solution aligns with all constitutional principles:
- API-First: Uses Firecrawl instead of custom implementation
- Network Error Handling: Core requirement with comprehensive design
- Code Quality: Python best practices followed
- Simplicity: Focused, single-purpose tool leveraging external services
