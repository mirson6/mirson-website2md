# Feature Specification: Website to Markdown Crawler

**Feature Branch**: `001-website-crawler`
**Created**: 2026-01-10
**Status**: Draft
**Input**: User description: "开发一个 Python 脚本，用于将网站内容转换为 Markdown 文档。输入：起始 URL 为 https://dict.thinktrader.net/VBA/start_now.html 范围限制：必须严格限制爬取 https://dict.thinktrader.net/VBA/ 路径下的子链接，忽略其他域名的链接。功能：遍历该路径下的所有页面。将所有页面的内容保存为单独的 .md 文件。文件名基于页面标题或 URL 路径生成，保持目录结构整洁。"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Single Page Conversion (Priority: P1)

User needs to convert a single webpage from the VBA documentation site into a Markdown file for offline reference and archiving.

**Why this priority**: This is the core minimum viable product. Converting a single page validates the entire conversion pipeline (fetching, parsing, Markdown generation, file writing) without the complexity of crawling logic.

**Independent Test**: Can be fully tested by running the tool with a single URL and verifying that one correctly formatted .md file is created with proper content extraction.

**Acceptance Scenarios**:

1. **Given** a valid VBA documentation URL, **When** the crawler processes that single page, **Then** a Markdown file is created with the page's content properly formatted
2. **Given** a URL with HTML content, **When** converting to Markdown, **Then** headings, lists, links, and code blocks are preserved in Markdown format
3. **Given** a page with a title, **When** saving the Markdown file, **Then** the filename is derived from the page title or URL path

---

### User Story 2 - Multi-Page Crawling (Priority: P2)

User needs to crawl all pages within the VBA documentation section to create a complete offline documentation set.

**Why this priority**: Once single-page conversion works, multi-page crawling provides the primary value - automated archival of entire documentation sections. This depends on User Story 1's conversion logic.

**Independent Test**: Can be fully tested by starting from the VBA start page and verifying that all linked pages within the /VBA/ path are converted to separate .md files.

**Acceptance Scenarios**:

1. **Given** the starting VBA documentation URL, **When** the crawler discovers links, **Then** it only follows links within https://dict.thinktrader.net/VBA/ and ignores external domains
2. **Given** multiple VBA documentation pages, **When** crawling completes, **Then** each page is saved as a separate .md file
3. **Given** a page linking to already-visited URLs, **When** the crawler encounters duplicates, **Then** it skips re-processing to avoid redundant work

---

### User Story 3 - Structured Output Organization (Priority: P3)

User needs the generated Markdown files organized in a directory structure that reflects the website's hierarchy for easy navigation.

**Why this priority**: Directory organization enhances usability but is not essential for basic functionality. The files can be reorganized manually if needed.

**Independent Test**: Can be fully tested by crawling a site with nested URL paths (e.g., /VBA/chapter1/page.html) and verifying that the output directory structure mirrors the URL hierarchy.

**Acceptance Scenarios**:

1. **Given** URLs with nested paths (e.g., /VBA/chapter1/lesson1.html), **When** saving files, **Then** directories are created to match the URL path structure
2. **Given** multiple pages at the same directory level, **When** saving, **Then** files are organized in the same output directory
3. **Given** filename conflicts (same page title in different directories), **When** saving, **Then** each file is saved in its respective directory without overwriting

---

### Edge Cases

- What happens when a webpage is unreachable or returns an error (404, 500, timeout)?
- What happens when a page has no extractable title or the title generates an invalid filename?
- What happens when the website structure contains circular references (loops)?
- What happens when HTML content is malformed or improperly structured?
- What happens when the target URL path contains no links (single page)?
- What happens when file permissions prevent writing to the output directory?
- What happens when Markdown conversion encounters unsupported HTML elements (e.g., complex tables, embedded media)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept a starting URL as input parameter
- **FR-002**: System MUST restrict crawling to URLs within https://dict.thinktrader.net/VBA/ path only
- **FR-003**: System MUST ignore links to external domains or paths outside /VBA/
- **FR-004**: System MUST fetch and parse HTML content from webpages
- **FR-005**: System MUST convert HTML content to Markdown format
- **FR-006**: System MUST preserve document structure (headings, paragraphs, lists, code blocks, links) during conversion
- **FR-007**: System MUST generate filenames based on page title when available, or URL path when title is unavailable
- **FR-008**: System MUST save each page as a separate .md file
- **FR-009**: System MUST create directory structure matching URL path hierarchy
- **FR-010**: System MUST track visited URLs to avoid processing duplicates
- **FR-011**: System MUST handle network errors gracefully (timeouts, connection failures, HTTP errors)
- **FR-012**: System MUST report which pages were successfully converted and which failed
- **FR-013**: System MUST validate/sanitize filenames to be valid on the target filesystem
- **FR-014**: System MUST create output directories if they do not exist
- **FR-015**: System MUST provide a summary report of total pages processed, succeeded, and failed

### Key Entities

- **Web Page**: A document fetched from a URL containing HTML content, metadata (title, links), and convertible to Markdown
- **URL**: A web address specifying the location of a page, must be validated to belong to the allowed domain path
- **Markdown File**: A text file containing converted page content in Markdown format with .md extension
- **Crawl Queue**: An ordered collection of URLs to be processed, tracking pending and visited states
- **Conversion Result**: Record of a page conversion including source URL, output file path, and success/failure status

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: User can initiate the crawler with a single command providing the starting URL
- **SC-002**: 100% of pages within the /VBA/ path are successfully converted to Markdown when network is stable
- **SC-003**: 0% of pages outside the /VBA/ path are crawled (strict boundary enforcement)
- **SC-004**: All generated Markdown files are readable and contain the expected content structure
- **SC-005**: Output directory structure matches the URL path hierarchy for nested pages
- **SC-006**: Crawler completes processing of 100 pages in under 5 minutes on standard network connection
- **SC-007**: Network errors are logged with sufficient detail for troubleshooting (URL, error type, timestamp)
- **SC-008**: User can verify conversion success through a summary report showing pages processed, succeeded, and failed

## Assumptions

1. The target website (dict.thinktrader.net) is accessible and returns HTML content
2. HTML content follows standard web conventions (semantic HTML, parseable structure)
3. Markdown conversion prioritizes readability over pixel-perfect reproduction
4. Output directory will be in the current working directory or specified by the user
5. The tool runs in an environment with internet connectivity
6. Standard filesystem permissions allow creating directories and files in the output location
7. Page titles are in a format that can be sanitized to valid filenames (most common cases)
8. The website does not require authentication or special headers for basic content access
9. JavaScript-rendered content is not required (static HTML only)
10. The crawl depth is limited to the /VBA/ path section (not infinite recursive crawling)
