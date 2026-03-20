# Recommendation

## Next Steps for Production

This prototype should move from filesystem storage to a more durable and query-efficient storage layer. Visited URLs, crawler metadata, queues, and index data should be stored in a database or key-value store, and crawler workers should be separated more cleanly from search-serving components so indexing can scale with safer incremental updates.

Production deployment would also need stronger throttling and crawl politeness, better monitoring for crawler health and search latency, improved recovery and concurrency behavior, and a more sophisticated relevance model than simple keyword frequency and crawl depth.
