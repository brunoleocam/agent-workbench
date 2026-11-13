# Architecture patterns

Each pattern below solves a specific problem and costs something to operate. Reach for one when the brief or a measured signal shows the problem, and record the choice in an ADR.

## CQRS (Command Query Responsibility Segregation)

Separate the model that changes data (commands) from the model that reads it (queries). In the simple form, writes go through domain logic on normalized tables while reads come from views or read-optimized tables. In the full form, the read side is a separate store fed by events.

### When to use
- Reads and writes have very different shapes or loads: complex validation on writes, many differently shaped screens or reports on reads.
- Read models need to be denormalized for speed and the write model must stay normalized for correctness.

### When not to use
- A CRUD application where the screen is the table. You pay for two models and synchronization with no gain.
- When the team cannot accept that the read side lags the write side.

## Event Sourcing

Store the sequence of events that changed an entity ("ItemAdded", "OrderPaid") instead of only its current state. Current state is rebuilt by replaying events; read models are projections.

### When to use
- The history itself is a requirement: audit, finance, ledgers, "what did this look like on that date".
- Several projections of the same history are needed, and new ones will be added later.

### When not to use
- When only the current state matters. Event schemas become permanent, replays need snapshots as streams grow, and fixing bad data means writing compensating events.
- As a first project in the pattern on a deadline. The learning curve is steep.

## Saga

A business transaction that spans several services or steps, each with a local transaction and a compensating action that undoes it ("reserve seat" and "release seat"). **Orchestrated**: one coordinator tells each step what to do. **Choreographed**: each step reacts to the previous step's event.

### When to use
- A process crosses services or external systems that cannot share one database transaction (payment provider, stock service, shipping).
- Partial failure must leave the system consistent through compensation.

### When not to use
- When everything lives in one database. Use a database transaction.
- Choreography with more than three or four steps: the flow becomes hard to follow. Prefer orchestration there.

## Circuit breaker

Wrap calls to a dependency. After a number of failures, the breaker opens and calls fail fast for a while; then a few trial calls decide whether to close it again.

### When to use
- Calls to a dependency that can be slow or down (third-party API, another service), where waiting on timeouts would exhaust threads, connections, or the user's patience.
- When there is a useful fallback: a cached value, a degraded response, a queued retry.

### When not to use
- Calls to your own primary database in a single-service app: if the database is down, failing fast changes little.
- Without timeouts. A breaker does not replace a timeout on every outbound call.

## Rate limiting

Cap how many requests a client, user, key, or IP may make in a period. **Token bucket**: tokens refill at a steady rate and each request spends one, which allows short bursts. **Sliding window**: count requests in the last N seconds, which is smoother than fixed windows that reset at once.

### When to use
- Public APIs, login and password reset endpoints, expensive endpoints, and any endpoint open to abuse.
- To protect a shared resource from one noisy tenant.

### When not to use
- As the only protection against a denial-of-service attack; that needs the edge (CDN, provider) too.
- In process memory when there are several instances, unless an approximate per-instance limit is acceptable. Use a shared counter otherwise.

## Replication

Copy data from a primary database to one or more replicas. Replicas serve reads and can be promoted if the primary fails. Replication is usually asynchronous, so replicas lag behind.

### When to use
- Reads dominate the database load (see step 5 in `scaling-stages.md`).
- The availability target needs a standby that can take over.

### When not to use
- To scale writes. Every write still goes to the primary.
- For reads that must see the user's own write immediately, unless they are routed to the primary.

## Sharding

Split data across several databases by a shard key (tenant id, user id, region). Each shard holds a part of the data and takes a part of the writes. A **hot shard** appears when the key concentrates load (one huge tenant). **Rebalancing** moves data when shards grow unevenly; consistent hashing or a directory of key ranges makes it easier.

### When to use
- Write volume or data size exceeds one primary after indexes, caching, replicas, archiving, and a bigger machine.
- Data is naturally isolated by a key and most queries stay inside one key.

### When not to use
- Before the simpler steps above. Cross-shard queries, transactions, and reporting become application problems.
- When the key is unclear or most queries cross keys. Consider partitioning inside one database or a managed distributed database first.

## Load balancing algorithms

A load balancer spreads requests across instances and removes unhealthy ones by health check.

- **Round robin**: each instance in turn. Fine when requests cost about the same.
- **Least connections**: the instance with the fewest open connections. Better when request cost varies or connections are long (WebSocket, streaming).
- **Consistent hashing**: the same key goes to the same instance, and adding an instance moves only a fraction of the keys. Useful for caches and partitioned workloads.
- **Sticky sessions**: the same client goes to the same instance. It hides state kept in process memory, and that is its cost: uneven load, and lost sessions when an instance dies or a deploy rolls. Prefer stateless instances.

### When to use
- More than one instance of a service (step 4 in `scaling-stages.md`), or zero-downtime deploys with rolling updates.

### When not to use
- Sticky sessions as a substitute for moving session state out of the process.

## Polling, Server-Sent Events, and WebSocket

Ways to get fresh data to the client.

- **Polling**: the client asks every N seconds. Simplest, works everywhere, wastes requests and adds up to N seconds of delay. Long polling holds the request until there is news.
- **Server-Sent Events (SSE)**: one long HTTP response that the server writes events into, one way, server to client. Reconnects automatically and works through most proxies. Good for live scores, notifications, progress, dashboards.
- **WebSocket**: a two-way persistent connection. Needed for chat, collaborative editing, games: when the client also sends frequent messages.

### When to use
- Polling when updates are rare, a delay of seconds is fine, or the client count is small.
- Server-Sent Events when updates flow from server to client and the client rarely sends anything back.
- WebSocket when both sides send messages often.

### When not to use
- WebSocket for one-way updates: it costs more to scale (sticky or shared connection state, no HTTP caching) than SSE.
- Any persistent connection without planning for the connection count: each open connection holds memory on the server and through the load balancer, and a fan-out to many clients needs a pub/sub layer between instances.
