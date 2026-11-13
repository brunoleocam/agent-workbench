# Choosing data stores

Choose by access pattern and consistency need, not by popularity. Write down the queries the system runs most often, how fresh each answer must be, and how the data grows. Then pick.

## Start with a relational database

For most products the first store should be a relational database (PostgreSQL, MySQL, SQLite for a single instance). Reasons:

- Transactions across several rows and tables, which money, stock, bookings, and permissions need.
- Constraints (unique, foreign key, check) that keep bad data out without application code.
- Ad hoc queries and reports without designing for them up front.
- Mature tooling for backups, migrations, replicas, and monitoring.
- PostgreSQL alone also covers JSON documents, full-text search, and geospatial queries well enough for a long time.

Signals that justify a second store, each with a number when possible:

- Search with relevance ranking, typo tolerance, or facets over millions of documents that the database's text search cannot serve within the latency target.
- Time series with a write rate or retention the relational store cannot keep cheaply.
- Files and media: always object storage, never database rows or the server's disk.
- A hot key-value read path that the database and an in-process cache cannot serve within the latency target.

Every additional store is one more thing to back up, secure, monitor, and keep consistent with the primary. Record each one in an ADR.

## Relational

- Shines: structured data with relationships, transactions, constraints, reporting.
- Consistency: strong within a transaction (ACID).
- Do not use for: large binary files; append-only telemetry at very high rates; schemaless data whose shape is unknown and never queried by field.

## Document (MongoDB, Firestore, Couchbase)

- Shines: aggregates read and written as a whole (a product with its variants, a form submission), with shapes that vary per record.
- Consistency: strong per document; multi-document transactions exist but are the exception.
- Do not use for: data with many relationships queried from several directions; reporting across collections; when the real reason is "we do not want to write migrations".

## Key-value (Redis, Valkey, DynamoDB in its simplest use)

- Shines: lookup by key with very low latency: sessions, caches, rate-limit counters, feature flags, locks with expiry.
- Consistency: depends on the product; in-memory stores may lose recent writes on failure unless configured for persistence.
- Do not use for: the only copy of data you cannot lose, unless persistence and replication are configured and tested; queries by anything other than the key.

## Wide-column (Cassandra, ScyllaDB, Bigtable)

- Shines: very high write throughput, data partitioned by a known key, queries designed up front (timelines, messages by conversation, events by device).
- Consistency: tunable, often eventual.
- Do not use for: ad hoc queries, joins, transactions, or small datasets. The operational cost is high.

## Full-text search (Elasticsearch, OpenSearch, Meilisearch, Typesense)

- Shines: relevance ranking, typo tolerance, facets, autocomplete.
- Consistency: near real time; the index lags the source of truth.
- Do not use for: the source of truth. Feed it from the primary store (through events or an outbox) and be able to rebuild it from scratch.

## Time series (TimescaleDB, InfluxDB, Prometheus for metrics)

- Shines: append-only measurements with timestamps, aggregation over time windows, retention and downsampling.
- Consistency: usually strong per write, built for append.
- Do not use for: business entities that are updated in place.

## Object storage (S3 and compatible services)

- Shines: files of any size, media, backups, exports, static assets behind a CDN. Cheap and durable.
- Consistency: strong read-after-write on the main providers today; listing may lag on some compatible services.
- Do not use for: data you query by field; many tiny updates to the same object.

## Questions to answer before adding a store

1. Which queries does it serve that the current store cannot serve within the target, with the measurement?
2. What is the source of truth, and how is this store kept consistent with it?
3. How is it backed up and restored, and who operates it?
4. What does it cost per month at the brief's load?
