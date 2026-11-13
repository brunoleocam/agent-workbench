# Caching

A cache trades freshness for speed. Add one when a measured read path is too slow or too expensive after indexes and query fixes, and write down for each cached item how stale it may be.

## Where the cache lives

- **HTTP and CDN**: `Cache-Control`, `ETag`, and a CDN in front of static assets and public pages. Cheapest, and often enough.
- **In process**: a map or LRU inside the app. No network hop, no new service. Each instance has its own copy, so instances may disagree for up to the TTL. Good for a single instance and for data that changes rarely (configuration, catalog).
- **Distributed** (Redis, Valkey, Memcached): shared by all app instances. Needed when there are several instances and they must agree, or when the cached set does not fit in each process. One more service to run and secure.

## Read and write strategies

- **Cache-aside** (lazy loading): the app reads the cache; on a miss it reads the database and fills the cache. Simple and the usual default. The first read after expiry is slow, and a write must invalidate or update the key.
- **Write-through**: every write goes to the cache and the database together. Reads are always warm; writes are slower; data nobody reads still fills the cache.
- **Write-behind** (write-back): writes go to the cache and reach the database later, in batches. Fast writes, but data is lost if the cache fails before the flush. Use only when losing recent writes is acceptable and written down.

## TTL and invalidation

- Every key has a TTL, even when it is also invalidated on write. The TTL caps the damage of a missed invalidation.
- Invalidate on write: delete the key after the database commit, not before. Deleting is safer than updating, because two concurrent updates can leave the older value in the cache.
- Version keys (`product:42:v7`) when many keys depend on one change.
- Write the freshness rule into section 4 of `ARCHITECTURE.md`: "product price: invalidated on write, TTL 10 min".

## Stampede

When a popular key expires, many requests miss at the same time and all hit the database.

- **Lock or single flight**: one request rebuilds the value; the others wait or get the stale value.
- **Early refresh**: refresh the value in the background shortly before it expires, or with a probability that grows as expiry approaches.
- **Jitter**: add a random offset to TTLs so keys written together do not expire together.

## Never cache without care

- **Per-user data under a shared key**: a key without the user or tenant id serves one user's data to another. Every per-user or per-tenant key includes the id.
- **Permission and authorization data**: a cached "is admin" outlives a revoked role. Keep TTLs short, invalidate on change, or do not cache it.
- **Secrets and tokens**: not in a shared cache unless encrypted and required.
- **Responses that depend on headers** (language, auth): the CDN key must include them (`Vary`), or the response must not be cached publicly.
- **Errors**: caching a failure for the full TTL turns a short outage into a long one. Cache errors briefly, if at all.

## Measuring

Track the hit rate, the latency with and without the cache, and the memory used. A cache with a hit rate under about 50% may cost more than it saves.
