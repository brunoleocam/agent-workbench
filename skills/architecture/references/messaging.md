# Messaging and asynchronous work

Move work out of the request path when the user does not need to wait for it, when it is slow or unreliable, or when bursts exceed what can be done in real time. Every asynchronous flow trades immediacy for resilience and adds eventual consistency that the user may see.

## Queue and pub/sub

- **Queue** (work queue): each message is processed by one consumer. Use for jobs: send an email, process a video, generate a report. Examples: RabbitMQ, SQS, a database-backed job queue, Redis-based job libraries.
- **Pub/sub** (topic): each message reaches every subscriber. Use when several independent parts react to the same fact: "order paid" updates stock, sends an email, and feeds analytics. Examples: Kafka, SNS, RabbitMQ exchanges, NATS.
- Early on, a job table in the existing database with a worker that polls it is often enough, and avoids a new service.

## Event-driven architecture

Components publish facts that happened ("OrderPaid", past tense) instead of calling each other. The publisher does not know who listens.

- Gains: loose coupling, new consumers without changing the publisher, natural buffering of bursts.
- Costs: the flow is harder to follow and to debug; consistency between components is eventual; event schemas become a contract that needs versioning.
- Keep events small and stable: an id, the type, the time, a schema version, and the data consumers need.

## The dual write problem

A handler writes to the database and then publishes a message. If the process crashes between the two, or the publish fails, the database says the order was paid and nobody else ever hears about it. Publishing first has the opposite failure. Two systems cannot be updated atomically without help.

### The outbox pattern

1. In the same database transaction as the business change, insert a row into an `outbox` table with the message.
2. A separate relay reads unsent outbox rows, publishes them, and marks them sent.
3. If the relay crashes after publishing and before marking, the message is published again. Consumers must therefore be idempotent.

Change data capture (reading the database log) is a variant of the same idea. Record the choice in section 5 of `ARCHITECTURE.md`.

## Delivery guarantees and idempotency

- **At most once**: the message may be lost, never duplicated. Rarely what you want.
- **At least once**: the message is never lost but may arrive more than once. The usual guarantee of real brokers.
- "Exactly once" end to end is at least once plus idempotent processing.

Ways to make a consumer idempotent:

- An **idempotency key** in the message; the consumer records processed keys in a table with a unique constraint, in the same transaction as its own change, and skips keys it has seen.
- Operations that are naturally idempotent: "set status to paid" rather than "add 10 to balance".
- For public APIs that clients may retry, accept an `Idempotency-Key` header and return the stored response on a repeat.

## Retries, backoff, and dead letters

- Retry transient failures with **exponential backoff and jitter** (for example 1 s, 2 s, 4 s, plus a random offset) and a maximum number of attempts.
- Do not retry errors that will fail again (validation, permission): send them straight to the dead letter queue.
- A **dead letter queue** keeps messages that failed every attempt, with the error. Alert on its size, and have a way to inspect and replay messages.
- Set a timeout on every handler. A stuck consumer holds a message hostage.

## Ordering

- Most queues do not guarantee global order. Partitioned logs (Kafka) keep order per partition key, for example per order id.
- Design consumers so order rarely matters: carry a version or timestamp in the message and ignore older updates.
- When order matters for one entity, route all its messages through the same partition or key.

## What to write in ARCHITECTURE.md

For each asynchronous flow in section 5: the producer, the consumers, the broker or table, the delivery guarantee, the idempotency mechanism, the retry policy, the dead letter handling, and how the publish stays consistent with the database (outbox or the reason it does not matter).
