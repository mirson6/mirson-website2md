---

description: "Task list for Website to Markdown Crawler implementation"
---

# Tasks: Website to Markdown Crawler

**Input**: Design documents from `/specs/001-website-crawler/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are optional per constitution. Only include tests if explicitly requested by user.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- Paths shown below assume single project structure

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create project directory structure (src/, tests/, tests/contract/, tests/integration/, tests/unit/)
- [x] T002 Initialize Python project with pyproject.toml including project metadata, dependencies, and build configuration
- [x] T003 [P] Create requirements.txt with firecrawl-py>=0.0.1 and requests>=2.31.0
- [x] T004 [P] Create .gitignore file for Python (exclude __pycache__, *.pyc, venv/, .env, output/)
- [x] T005 [P] Create README.md with project overview, installation instructions, and usage examples

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T006 Create CrawlConfig dataclass in src/config.py with validation for start_url, max_pages, timeout, and output settings
- [x] T007 [P] Implement JobStatus enum (PENDING, IN_PROGRESS, COMPLETED, FAILED, CANCELLED) in src/models.py
- [x] T008 [P] Implement CrawlJob dataclass in src/models.py with job tracking, status properties, and progress calculation
- [x] T009 [P] Implement CircuitBreaker class in src/firecrawl_client.py with failure tracking, state management (closed/open/half-open), and can_attempt logic
- [x] T010 [P] Implement retry_with_backoff decorator in src/firecrawl_client.py with exponential backoff, max_retries, and circuit breaker integration
- [x] T011 Implement setup_logging function in src/cli.py with configurable log levels, console handler, and structured formatter
- [x] T012 [P] Implement is_allowed_url function in src/url_utils.py with domain validation, path boundary checking (/VBA/), and exception handling
- [x] T013 [P] Implement sanitize_filename function in src/url_utils.py with invalid character removal, length limiting (255 chars), and safe character replacement
- [x] T014 Create FirecrawlClient wrapper class in src/firecrawl_client.py with API base URL configuration, authentication header setup, and timeout management

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Single Page Conversion (Priority: P1) 🎯 MVP

**Goal**: Convert a single VBA documentation page to Markdown file

**Independent Test**: Run tool with `--url https://dict.thinktrader.net/VBA/start_now.html --max-pages 1` and verify one `.md` file is created with proper content

### Implementation for User Story 1

- [x] T015 [P] [US1] Implement scrape_url method in FirecrawlClient class in src/firecrawl_client.py to POST to /v2/scrape endpoint with URL and formats parameter
- [x] T016 [P] [US1] Implement ScrapedPage dataclass in src/models.py with url, markdown, metadata (title, sourceURL), success flag, and error_message fields
- [x] T017 [P] [US1] Implement generate_filename function in src/url_utils.py with priority logic (title → URL path → hash fallback) and .md extension
- [x] T018 [P] [US1] Implement MarkdownFile dataclass in src/models.py with content, title, source_url, relative_path, and frontmatter generation methods
- [x] T019 [US1] Implement write_markdown_file function in src/file_writer.py with directory creation (pathlib.Path.mkdir(parents=True)), atomic file writing, and permission error handling
- [x] T020 [US1] Implement CrawlResult dataclass in src/models.py with pages_scraped list, statistics (total, successful, failed), errors list, and generate_summary method
- [x] T021 [US1] Implement scrape_single_page function in src/crawler.py that uses FirecrawlClient.scrape_url, creates ScrapedPage from response, converts to MarkdownFile, and writes to disk
- [x] T022 [US1] Implement CLI argument parser in src/cli.py with argparse for --url (required), --output-dir, --max-pages, --timeout, and --verbose flags
- [x] T023 [US1] Implement main function in src/cli.py that configures logging, parses arguments, calls scrape_single_page for max-pages=1, and prints CrawlResult.generate_summary

**Checkpoint**: At this point, User Story 1 should be fully functional - single page conversion works independently ✅ MVP COMPLETE

---

## Phase 4: User Story 2 - Multi-Page Crawling (Priority: P2)

**Goal**: Crawl all pages within /VBA/ path using Firecrawl's batch crawling API

**Independent Test**: Run tool with starting URL and verify all linked pages within /VBA/ are converted to separate .md files

### Implementation for User Story 2

- [ ] T024 [P] [US2] Implement submit_crawl_job method in FirecrawlClient class in src/firecrawl_client.py to POST to /v2/crawl endpoint with url, limit, and scrapeOptions
- [ ] T025 [P] [US2] Implement check_crawl_status method in FirecrawlClient class in src/firecrawl_client.py to GET /v2/crawl/{job_id} with retry logic and status parsing
- [ ] T026 [P] [US2] Implement poll_crawl_job method in FirecrawlClient class in src/firecrawl_client.py that calls check_crawl_status in a loop with poll_interval until job is_finished
- [ ] T027 [P] [US2] Implement filter_allowed_pages function in src/crawler.py that iterates through API results, validates each URL with is_allowed_url, and tracks skipped pages
- [ ] T028 [P] [US2] Implement deduplicate_urls function in src/crawler.py using set to track seen URLs and skip duplicates (respecting FR-010)
- [ ] T029 [US2] Implement crawl_multiple_pages function in src/crawler.py that submits crawl job, polls for completion, filters results by boundary, deduplicates, and converts each to MarkdownFile
- [ ] T030 [US2] Update main function in src/cli.py to call crawl_multiple_pages when max-pages > 1, handle both single-page and multi-page modes, and print comprehensive summary

**Checkpoint**: At this point, User Stories 1 AND 2 should both work - multi-page crawling with boundary enforcement

---

## Phase 5: User Story 3 - Structured Output Organization (Priority: P3)

**Goal**: Organize Markdown files in directory structure matching URL hierarchy

**Independent Test**: Crawl site with nested URLs (e.g., /VBA/chapter1/page.html) and verify output directory mirrors URL structure

### Implementation for User Story 3

- [ ] T031 [P] [US3] Implement _generate_relative_path static method in MarkdownFile class in src/models.py with URL parsing, /VBA/ prefix removal, .html suffix removal, and nested path extraction
- [ ] T032 [P] [US3] Implement from_scraped_page classmethod in MarkdownFile class in src/models.py that calls _generate_relative_path and sets absolute_path from output_dir
- [ ] T033 [P] [US3] Implement generate_frontmatter method in MarkdownFile class in src/models.py with YAML delimiters, title, source_url, and scraped_at timestamp
- [ ] T034 [P] [US3] Implement with_frontmatter method in MarkdownFile class in src/models.py that prepends frontmatter to content
- [ ] T035 [US3] Update write_markdown_file function in src/file_writer.py to create nested directories using pathlib.Path(parents=True) and handle directory-level file conflicts
- [ ] T036 [US3] Update scrape_single_page and crawl_multiple_pages functions in src/crawler.py to use MarkdownFile.from_scraped_page and write_markdown_file with nested directory support

**Checkpoint**: All user stories should now be independently functional with complete directory structure support

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T037 [P] Add comprehensive error logging throughout all modules with contextual information (URL, operation, error type, timestamp) per Constitution Principle II
- [ ] T038 [P] Add network request logging to FirecrawlClient methods with request details (URL, method, body), response status, and timing information
- [ ] T039 [P] Add progress reporting to poll_crawl_job function in src/firecrawl_client.py that logs job status, completion percentage, and page counts
- [ ] T040 [P] Add graceful degradation for Firecrawl service unavailability in FirecrawlClient with clear error messages suggesting service startup
- [ ] T041 [P] Add type hints to all function signatures in src/ modules per Constitution Principle III (Code Quality)
- [ ] T042 [P] Add docstrings to all public functions and classes in src/ modules per Constitution Principle III (Code Quality)
- [ ] T043 [P] Review and optimize function lengths in src/ modules to keep functions under 50 lines per Constitution Principle III
- [ ] T044 Validate all PEP 8 style requirements across src/ directory (black formatting, flake8 linting)
- [ ] T045 Test quickstart.md examples by running all documented use cases and verifying expected output

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - User Story 1 (P1): Can start after Foundational (Phase 2) - No dependencies on other stories
  - User Story 2 (P2): Can start after Foundational (Phase 2) - May integrate with US1 components but should be independently testable
  - User Story 3 (P3): Can start after Foundational (Phase 2) - Enhances US1/US2 with directory structure
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Reuses components from US1 (FirecrawlClient, models) but functionally independent
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Extends MarkdownFile and file_writer from US1/US2

### Within Each User Story

- Models before services/functions
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- **Setup Phase**: T003, T004, T005 can run in parallel (different files)
- **Foundational Phase**: T007, T008, T009, T010, T012, T013 can run in parallel (different files/modules)
- **User Story 1**: T015, T016, T017, T018 can run in parallel (different files, no dependencies)
- **User Story 2**: T024, T025, T026, T027, T028 can run in parallel (different functions, no blocking dependencies)
- **User Story 3**: T031, T032, T033, T034 can run in parallel (different methods in same class but independent logic)
- **Polish Phase**: T037, T038, T039, T040, T041, T042, T043 can run in parallel (different files/functions)

---

## Parallel Example: User Story 1

```bash
# Launch all core components for User Story 1 together:
Task T015: "Implement scrape_url method in FirecrawlClient class in src/firecrawl_client.py"
Task T016: "Implement ScrapedPage dataclass in src/models.py"
Task T017: "Implement generate_filename function in src/url_utils.py"
Task T018: "Implement MarkdownFile dataclass in src/models.py"

# After parallel tasks complete, continue with sequential integration:
Task T019: "Implement write_markdown_file function in src/file_writer.py"
Task T020: "Implement CrawlResult dataclass in src/models.py"
# ... and so on
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T005)
2. Complete Phase 2: Foundational (T006-T014) - CRITICAL, blocks all stories
3. Complete Phase 3: User Story 1 (T015-T023)
4. **STOP and VALIDATE**: Test single-page conversion independently
5. Demo/verify: Run `python -m src.cli --url https://dict.thinktrader.net/VBA/start_now.html --max-pages 1`

**MVP Scope**: Single page conversion with URL validation, filename generation, and file writing

### Incremental Delivery

1. Foundation (Phase 1 + 2) → Infrastructure ready
2. Add User Story 1 (Phase 3) → Test independently → Deliver MVP
3. Add User Story 2 (Phase 4) → Test independently → Deliver multi-page crawling
4. Add User Story 3 (Phase 5) → Test independently → Deliver structured output
5. Polish (Phase 6) → Final production-ready tool

Each story adds value without breaking previous stories.

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (T001-T014)
2. Once Foundational is done:
   - Developer A: User Story 1 (T015-T023)
   - Developer B: User Story 2 (T024-T030)
   - Developer C: User Story 3 (T031-T036)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies, can run in parallel
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Constitution compliance verified: API-First (uses Firecrawl), Network Error Handling (circuit breaker + retry), Code Quality (type hints, docstrings, PEP 8), Simplicity (minimal dependencies, standard library usage)
- Total tasks: 45 (plus optional tests if requested)
- Setup: 5 tasks
- Foundational: 9 tasks (BLOCKS all user stories)
- User Story 1: 9 tasks (MVP)
- User Story 2: 7 tasks
- User Story 3: 6 tasks
- Polish: 9 tasks
