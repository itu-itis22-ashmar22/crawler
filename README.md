# Web Crawler Demo

## Overview

This project is a local prototype web crawler and live search engine built in Python with Flask. It starts from an origin URL, crawls up to a maximum depth, prevents duplicate crawling with a global visited set, writes indexed words into filesystem buckets, and supports searching while crawler jobs are still active.

## Features

- Background crawler jobs
- Visited URL deduplication
- Configurable crawl depth
- Configurable hit rate
- Queue-capacity-based back pressure
- Live crawler status page
- Filesystem-backed word index
- Live search over indexed content
- Local execution on localhost

## Architecture

### Crawler Service

Handles crawler creation, validation, background execution, HTML fetching, parsing, indexing, logging, queue updates, and crawl-state persistence.

### Search Service

Handles query execution by reading the word bucket files, aggregating matching records, and sorting results by frequency first and depth second.

### Storage Layer

Handles crawler metadata, queue state, logs, visited URLs, and alphabetical word bucket files on the local filesystem.

### Web UI

Handles crawl creation, crawler status viewing, and search through three local Flask pages.

## Storage Layout

```text
storage/
├── crawlers/
├── logs/
├── queues/
├── words/
└── visited_urls.data
```

- `storage/visited_urls.data`: one normalized URL per line to prevent duplicate crawling.
- `storage/crawlers/{crawler_id}.data.json`: crawler metadata, counters, status, and timestamps.
- `storage/logs/{crawler_id}.log`: append-only crawler events for visibility and debugging.
- `storage/queues/{crawler_id}.queue`: current queue state as `depth<TAB>url`.
- `storage/words/a.data` through `z.data` and `misc.data`: word index records stored as `word<TAB>relevant_url<TAB>origin_url<TAB>depth<TAB>frequency`.

## How to Run

```bash
python -m venv .venv
```

Activate the virtual environment.

```bash
pip install -r requirements.txt
python app.py
```

Then open the local Flask address in a browser, usually [http://127.0.0.1:5000](http://127.0.0.1:5000).

## How to Use

### Start a crawler

Open `/crawler`, enter the origin URL, max depth, hit rate, max URLs, and queue capacity, then submit the form.

### Monitor a crawler

Open the crawler status page to watch the current status, processed count, discovered count, queued count, throttled state, queue preview, and live log tail.

### Search

Open `/search`, enter a query, and review results shown as `(relevant_url, origin_url, depth)`. If crawlers are still running, repeated searches may return more results over time.

## Search Semantics

Search is exact normalized-token match over indexed page content. Each matching record links a query word to a relevant URL, its origin URL, crawl depth, and frequency. Results are aggregated and sorted by:

- Total frequency descending
- Depth ascending
- Relevant URL ascending

## Back Pressure

Each crawler supports a configurable hit rate delay between requests and a configurable queue capacity. Once the queue reaches capacity, additional discovered links are not enqueued, the crawler logs `THROTTLED`, and crawler state exposes whether it is currently throttled.

## Example Workflow

Start a crawl from the Wikipedia main page with depth `1`, hit rate `1`, max URLs `5`, and queue capacity `20`. Open the status page and watch processed pages, queue updates, and logs. Open `/search` in another tab, query a known indexed word, and repeat the query while the crawler is still running to observe new results appearing over time.

## Limitations

- Filesystem storage instead of database-backed persistence
- One URL at a time per crawler job
- Exact-match search only
- No robots.txt enforcement
- No JavaScript rendering for dynamic sites
- No advanced ranking beyond keyword frequency and crawl depth
- Restart-friendly persistence, but no automatic job resume

## Future Improvements

- Move metadata and indexing to a database or key-value store
- Use a more efficient index structure for larger crawls
- Improve crawl politeness, retries, and resilience
- Add stronger recovery semantics and operational monitoring
- Expand ranking beyond simple keyword frequency and depth
