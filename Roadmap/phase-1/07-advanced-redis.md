# Advanced Redis Use

## 1. Overview

Beyond basic caching, Redis is a powerful multi-tool for backend systems. Its data structures and atomic operations make it ideal for problems that would be difficult or expensive to solve with a traditional database.

This chapter covers three production-critical use cases: rate limiting, session storage, and counters. These patterns appear in almost every serious backend system.

---

## 2. Why This Matters

**Where it is used:**
- Rate limiting: every public API (GitHub, Stripe, Twitter) uses rate limiting
- Session storage: authentication in stateless web servers
- Counters: view counts, like counts, inventory levels, distributed atomic increments

**Problems it solves:**
- Rate limiting: prevents API abuse, protects backends from overload
- Sessions: stateless application servers can share session state without sticky routing
- Counters: atomic increments without transaction overhead

**Why engineers must understand this:**
- These are real patterns you will implement or maintain. Understanding the mechanics prevents subtle bugs.
- Redis's atomic single-threaded model is what makes these patterns correct — knowing why matters.

---

## 3. Core Concepts (Deep Dive)

### 3.1 Rate Limiting

**Explanation:**
Rate limiting restricts how many times a client (identified by IP, user ID, or API key) can perform an action within a time window.

**Why Redis for rate limiting:**
- Requests come in from many application server instances simultaneously.
- The counter must be shared and atomic across all instances.
- Redis's atomic `INCR` operation and TTL make this natural.

---

**Pattern 1: Fixed Window Rate Limiting**

One key per client per time window. Increment on each request. Reject if over the limit.

```
Key: rate_limit:{user_id}:{window}  e.g., rate_limit:42:2024-01-15-14:30
Value: request count (integer)
TTL: window duration
```

```
// Pseudo-code
key = "rate_limit:" + userId + ":" + currentMinute()
count = INCR key
if count == 1: EXPIRE key 60   // set TTL on first increment
if count > 100: reject request
```

**Problem:** At the window boundary, a client can make 100 requests at 59 seconds, then 100 more at 61 seconds — 200 requests in a 2-second span.

---

**Pattern 2: Sliding Window Rate Limiting**

More accurate. Uses Redis sorted sets (ZSET). Store each request's timestamp as a score. Count requests within the sliding window.

```
Key: rate_limit:{user_id}
Type: Sorted Set (score = timestamp)

On each request:
1. ZADD key {now} {now}          -- record request
2. ZREMRANGEBYSCORE key 0 {now - 60s}  -- remove old entries
3. ZCARD key                     -- count remaining entries
4. If count > limit: reject
5. EXPIRE key 60                 -- sliding TTL
```

**Tradeoff:** More accurate but uses more memory (one entry per request vs. one integer per window).

---

**Intuition:**
Fixed window is like a bucket that resets every minute. Sliding window is like a moving 60-second view — it always looks at the last 60 seconds, regardless of where you are in the clock.

---

### 3.2 Session Storage

**Explanation:**
A session stores temporary user state after authentication — typically a user ID and relevant claims. The server needs to look up this session on every authenticated request.

**Why Redis for sessions:**

| Option | Problem |
|--------|---------|
| In-memory (single server) | Breaks with multiple app servers or restarts |
| Database (PostgreSQL) | Too slow for every-request lookups |
| JWT (stateless) | Cannot be revoked before expiry |
| Redis | Fast, shared across servers, supports TTL-based expiry |

**Pattern:**

```
On login:
1. Authenticate user
2. Generate a random session token (UUID or CSPRNG)
3. Store: SET session:{token} {userId} EX 86400  (24 hours)
4. Return token to client (cookie or header)

On each request:
1. Extract token from cookie/header
2. Redis GET session:{token}
3. If exists: user is authenticated → proceed
4. If not exists: session expired or invalid → return 401

On logout:
1. DEL session:{token}   -- immediate invalidation
```

**Intuition:**
The token is like a hotel key card. The card itself contains no information — it's just a random code. The hotel (Redis) maps that code to your room number (user ID). When you check out, the card is deactivated immediately.

**Why this beats JWT for certain use cases:**
With JWT, you cannot revoke a token before it expires. With Redis sessions, `DEL session:{token}` invalidates instantly — useful for "log out everywhere" features.

---

### 3.3 Counters

**Explanation:**
Redis's `INCR` / `DECR` commands atomically increment or decrement an integer value. Atomic means: even with 1,000 concurrent requests, each increment is applied exactly once, with no lost updates.

**Why this is powerful:**
In a relational database, incrementing a counter requires a read-then-write inside a transaction to avoid lost updates. In Redis, `INCR` is a single atomic operation — no transaction needed.

```
INCR page_views:{post_id}     -- returns new count
DECR inventory:{product_id}   -- returns new count
INCRBY score:{user_id} 10     -- add 10 to the score
```

**Use cases:**
- Page view counters
- Like / upvote counts
- Inventory levels
- Download counts
- API usage tracking

**High-throughput pattern:**
For extremely hot counters (millions of increments/second), batch-write to the database periodically rather than on every increment:

```
Every 10 seconds:
1. GETSET page_views:{post_id} 0   -- atomically read and reset to 0
2. UPDATE posts SET views = views + {value} WHERE id = {post_id}
```

---

### 3.4 Redis Data Structures Overview

Understanding which Redis data structure to use is key to using it well.

| Structure | Commands | Use Case |
|-----------|----------|---------|
| String | GET, SET, INCR | Cache, counters, sessions |
| Hash | HGET, HSET, HGETALL | Object storage (user profile fields) |
| List | LPUSH, RPOP, LRANGE | Queue, activity feed |
| Set | SADD, SMEMBERS, SINTER | Unique tags, friend lists, deduplication |
| Sorted Set | ZADD, ZRANGE, ZRANK | Leaderboards, sliding window rate limiting, priority queues |

**Intuition for Sorted Sets:**
A sorted set is like a leaderboard. Every member has a score. You can instantly get the top 10, or find someone's rank, or get everyone with a score between X and Y — all in O(log n).

---

## 4. Simple Example

```
// Rate limiting middleware (pseudo-code)

async function rateLimitMiddleware(req, res, next) {
  const key = `rate_limit:${req.ip}`;
  const limit = 100;

  const count = await redis.incr(key);

  if (count === 1) {
    await redis.expire(key, 60);  // set 60s TTL on first request
  }

  if (count > limit) {
    return res.status(429).json({ error: 'Too many requests' });
  }

  next();
}

// Leaderboard with sorted set
await redis.zadd('leaderboard:game1', score, userId);

// Get top 10 players
const top10 = await redis.zrevrange('leaderboard:game1', 0, 9, 'WITHSCORES');

// Get a user's rank
const rank = await redis.zrevrank('leaderboard:game1', userId);
```

---

## 5. System Perspective

**In production:**
- Rate limiting in Redis must handle the case where Redis is unavailable. Options: fail open (allow request), fail closed (reject request), or fall back to a local in-memory counter. Choose based on security requirements.
- Sessions in Redis need replication (`Redis Sentinel` or `Redis Cluster`) for high availability — if the session store goes down, all users are logged out.
- Counters that are only in Redis are lost on Redis restart if persistence isn't configured. For critical counts (inventory), persist to the database periodically.

**Under high traffic:**
- Redis handles millions of operations per second on a single instance. It rarely becomes the bottleneck for rate limiting or counter operations.
- Sorted set operations for sliding window rate limiting are O(log n) — extremely efficient.
- For session lookups, ensure Redis is co-located (low network latency) with your application servers.

**Under failure:**
- Expiry is not guaranteed to happen at exactly the TTL moment — Redis expires lazily (on access) and with a background sweep. Don't rely on exact expiry timing for correctness.
- On Redis restart without persistence, all sessions are lost. Design your login flow to handle this gracefully (redirect to login, don't crash).

---

## 6. Diagram Section

![Diagram Placeholder](./images/advanced-redis.png)

**What the diagram should show:**
- Three separate panels:

**Panel 1 — Rate Limiting:**
Timeline of requests → Redis key with incrementing counter → threshold check → allow or reject

**Panel 2 — Session Storage:**
Login flow: user → app → generate token → Redis SET → token returned to client
Request flow: client with token → app → Redis GET → user ID → process request

**Panel 3 — Counter:**
Multiple app servers all calling INCR on the same key → Redis single-threaded processing → consistent final count (contrast with a database counter where concurrent reads before update cause a lost update)

---

## 7. Common Mistakes

**1. Not handling Redis unavailability in rate limiting**
If Redis goes down and your rate limiter throws an uncaught error, your entire API goes down. Always have a fallback behavior.

**2. Using Redis sessions without replication**
Single Redis instance + no persistence = logout all users on restart or failure. For production session storage, use Redis Sentinel or Cluster.

**3. Race condition in rate limit TTL**
Setting TTL only once at count == 1 can fail if the INCR and EXPIRE are not atomic. Use Lua scripts or `SET key value EX ttl` patterns for atomicity.

**4. Storing too much data in a session**
Sessions stored in Redis should be minimal: just the user ID and essential claims. Don't serialize the entire user object — fetch it from the DB when needed.

**5. Forgetting that Redis counters reset on restart**
If you're using Redis to track inventory, view counts, or other business-critical numbers without flushing to the database, you will lose data on restart.

**6. Not namespacing keys**
`SET user 42` collides with anything else named `user`. Always use structured keys: `session:{token}`, `rate_limit:{ip}:{window}`, `counter:{type}:{id}`.

---

## 8. Interview / Thinking Questions

1. Design a rate limiter that allows 100 requests per minute per user. How does your approach handle the boundary problem (requests at 59s and 61s)?

2. Compare Redis session storage vs. JWT tokens. What does each approach make easy, and what does each approach make hard?

3. Why is `INCR` in Redis safe under concurrency without using a transaction?

4. You need to build a leaderboard for a game with 1 million players. The leaderboard must update in real-time and show a player's rank. Which Redis data structure do you use, and why?

5. Your rate limiter is backed by Redis. Redis goes down. What should your system do?

---

## 9. Build It Yourself

**Task: Build a complete rate limiter + session system**

**Part 1 — Rate Limiter:**
1. Build an Express (or FastAPI) middleware
2. Limit: 10 requests per 60 seconds per IP
3. Return `X-RateLimit-Remaining` header on each response
4. Return 429 with `Retry-After` header when limit exceeded
5. Test with a loop of 15 requests and verify behavior

**Part 2 — Session Storage:**
1. Build `POST /login` — verify credentials, generate UUID token, store in Redis with 1-hour TTL
2. Build `GET /me` — read token from `Authorization` header, look up in Redis, return user info
3. Build `POST /logout` — delete the session key from Redis
4. Test: login → call /me → logout → call /me again (should get 401)

Both parts together form the foundation of an authenticated, rate-limited API.

---

## 10. Use AI vs Think Yourself

### Use AI For:
- Redis command syntax (especially sorted set commands)
- Lua script boilerplate for atomic operations
- Generating test scripts to simulate concurrent requests

### Must Understand Yourself:
- Why Redis INCR is atomic and what that means for counter correctness
- The tradeoff between fixed-window and sliding-window rate limiting — the boundary problem
- Why Redis sessions can be invalidated instantly while JWTs cannot
- What happens in your system when Redis is unavailable — this is a design decision, not a code question

---

## 11. Key Takeaways

- Redis's atomic single-threaded model makes it safe for counters and rate limiting without complex locking.
- Rate limiting requires shared state across all app servers — Redis is the right tool for this.
- Sessions in Redis combine the speed of in-memory storage with the ability to share state across servers and invalidate instantly.
- Sorted sets are the right structure for leaderboards and sliding window rate limiting.
- Always namespace your Redis keys to avoid collisions.
- Design for Redis failure — your system should degrade gracefully, not crash.
