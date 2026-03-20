# Product PRD

## 1. Objective

Build a local web crawler and search system that exposes two capabilities: index and search. Indexing must crawl from an origin URL up to depth `k`, and search must return results shaped as `(relevant_url, origin_url, depth)`. Search must remain available while indexing is still active.

## 2. Scope

This prototype includes local execution on localhost, recursive crawling to a maximum depth, a visited set to avoid duplicate crawling, queue-based crawling, filesystem-based persistence, simple relevance ranking using frequency and depth, a web UI for starting crawls, viewing status, and searching, and real-time polling for crawler status. The system is intentionally single-machine and simple.

## 3. Core User Flows

### Flow A — Start crawl

The user enters an origin URL, max depth, hit rate, max URLs, and queue capacity. The system creates a crawler job, starts a background thread, and shows the crawler status page.

### Flow B — Monitor crawl

The user opens a crawler status page and sees the current status, processed count, queue depth, throttled status, logs, and queue preview.

### Flow C — Search

The user enters a query and receives results shaped as `(relevant_url, origin_url, depth)`. Search may return partial results while indexing is still ongoing.

## 4. Functional Requirements

1. The system shall expose an indexing capability that accepts an origin URL and depth `k`.
2. The indexer shall crawl pages recursively up to depth `k`.
3. The indexer shall not crawl the same page twice.
4. The system shall manage crawl load using back pressure.
5. The system shall expose a search capability that accepts a query string.
6. The searcher shall return triples of `(relevant_url, origin_url, depth)`.
7. The searcher shall work while indexing is active.
8. The system shall provide a UI for starting crawls and searches.
9. The system shall display crawler state including queue depth and throttling status.
10. The system shall persist crawl artifacts to local storage.
11. The system may support partial recovery after interruption.

## 5. Non-Functional Requirements

The system must run on a single local machine, use native language functionality for core crawler behavior, remain thread-safe for shared indexing and search state, stay understandable and maintainable, prefer correctness and clarity over feature breadth, and be runnable by a reviewer without external infrastructure.

## 6. System Components

### Crawler Service

Starts and manages crawler jobs.

### Search Service

Executes query lookup over indexed data.

### Storage Layer

Stores crawler metadata, queue state, logs, visited URLs, and word index files.

### Web UI

Provides pages for crawl creation, crawl status, and search.

## 7. Data and Storage Model

The system uses the following storage files:

- `storage/visited_urls.data`
- `storage/crawlers/{crawler_id}.data.json`
- `storage/logs/{crawler_id}.log`
- `storage/queues/{crawler_id}.queue`
- `storage/words/a.data` through `z.data` and `misc.data`

The visited file prevents duplicate crawling. The crawler data file stores job metadata and counters. The queue file supports visibility and partial recovery. The log file supports observability. The word files support search through alphabetical partitioning.

## 8. Relevance Definition

Relevance is defined by keyword frequency in indexed page content, with shallower crawl depth used as a secondary preference. Results are sorted by total frequency descending, depth ascending, and relevant URL ascending as a tie-breaker.

## 9. Back Pressure Behavior

Back pressure is implemented using a configurable hit rate delay between requests and a configurable queue capacity per crawler job. When the queue reaches capacity, additional discovered links are not enqueued, crawler state marks itself as throttled, and throttling is visible in the UI.

## 10. UI Requirements

The UI provides three pages:

- A crawler creation page that shows the crawler form and previous crawler jobs
- A crawler status page that shows status, counts, queue preview, throttled state, timestamps, and live logs
- A search page that accepts queries and renders result triples

## 11. Assumptions

- HTML pages are fetched through simple HTTP GET requests
- Only `text/html` pages are indexed
- Exact keyword matching is sufficient for prototype search
- Filesystem storage is acceptable for prototype scope
- The crawler runs on one machine only
- Query-time partial results are acceptable while indexing is active

## 12. Out of Scope

This prototype does not include distributed crawling, advanced ranking such as PageRank, fuzzy search, NLP or semantic search, robots.txt compliance enforcement, authentication, full browser rendering for JavaScript-heavy sites, or database-backed persistence.

## 13. Success Criteria

Success means a reviewer can start a crawl from an origin URL and depth, duplicate page crawls do not occur, search returns the expected triples, search works during active indexing, queue depth and throttling are visible, the project runs locally, and all required deliverables are present.
