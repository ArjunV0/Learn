# Backend Integration

## 1. Overview

The individual components — API server, PostgreSQL, Redis, and a job queue — don't create a production system in isolation. Integration is about understanding how these pieces fit together, how data flows between them, and how the system behaves as a whole.

This chapter is about mental models, not new syntax. After learning each component independently, this is where you step back and see the full picture.

---

## 2. Why This Matters

**Where it is used:**
- Every production backend is an integrated system. A checkout flow touches the API, database, cache, payment service, and queue all in one user action.

**Problems it solves:**
- Knowing each component individually is not enough. Integration bugs, ordering errors, and architectural mistakes only appear when components are combined.
- Understanding data flow helps you debug: when something breaks, you need to reason about which component and which transition failed.

**Why engineers must understand this:**
- This is what separates a developer who can build a feature from an engineer who can design a system.
- System thinking — how components interact, fail, and recover — is what senior engineers are evaluated on.

---

## 3. Core Concepts (Deep Dive)

### 3.1 API + Database + Cache: The Standard Read Pattern

**Explanation:**
The most common integration pattern: a REST API reads from a PostgreSQL database, with Redis in front as a cache.

**Request flow:**

```
Client Request
      ↓
API Handler
      ↓
Check Redis (cache)
  ├── HIT  → Return cached data (fast path)
  └── MISS → Query PostgreSQL
                  ↓
             Store in Redis (with TTL)
                  ↓
             Return data to client
```

**Write flow:**

```
Client writes (POST/PUT/DELETE)
      ↓
API Handler validates input
      ↓
Write to PostgreSQL (source of truth)
      ↓
Invalidate or update Redis cache
      ↓
Return response to client
```

**Key principle:**
PostgreSQL is always the source of truth. Redis is a read optimization layer. When in doubt about which is correct, trust the database.

**Where bugs live in this pattern:**
- Cache not invalidated on write → stale data served
- Cache TTL too long → users see outdated info for extended periods
- Cache written before the database write succeeds → cache has data the DB doesn't

**Correct order:** Write to DB first. Invalidate/update cache second.

---

### 3.2 API + Queue + Worker: The Async Processing Pattern

**Explanation:**
The API accepts a request and immediately enqueues a job. A separate worker process consumes the job and does the heavy work asynchronously.

**Flow:**

```
Client Request (POST /orders)
      ↓
API Handler
  1. Validate input
  2. Write order to PostgreSQL (status: 'pending')
  3. Enqueue job: { type: 'process_order', orderId: 123 }
  4. Return 202 Accepted to client immediately
      ↓
Worker (running separately)
  1. Dequeues job
  2. Fetches order from DB
  3. Charges payment (external API)
  4. Sends confirmation email
  5. Updates order status to 'completed' in DB
  6. Acknowledges job (removes from queue)
```

**Client experience:**
User gets an immediate response. The system processes in the background. A polling endpoint or webhook notifies when complete.

**Why return 202 Accepted:**
HTTP 202 means "I received your request and I'm working on it." It's the correct semantic for async operations. 200 means "done." For a background job, you're not done yet.

---

### 3.3 Logging

**Explanation:**
Logs are the audit trail of your system. When something goes wrong in production (and it will), logs are how you reconstruct what happened.

**What to log:**

| Event | What to include |
|-------|----------------|
| Incoming request | Method, path, user ID, request ID |
| Database query | Query type, table, duration |
| Cache hit/miss | Key, hit or miss, source |
| Job enqueued | Job type, payload ID |
| Job completed | Job ID, duration |
| Job failed | Job ID, error message, retry count |
| External API call | Service, endpoint, duration, status code |
| Error | Stack trace, user context, request ID |

**Structured logging:**
Log in JSON format, not plain text. Structured logs can be searched, filtered, and aggregated by log management systems (Datadog, Grafana Loki, CloudWatch).

```json
{
  "level": "info",
  "requestId": "abc-123",
  "userId": 42,
  "action": "cache_miss",
  "key": "user:42:profile",
  "duration_ms": 0.8,
  "timestamp": "2024-01-15T14:30:00Z"
}
```

**Correlation IDs:**
Generate a unique request ID at the API layer. Pass it through every downstream call (DB query log, cache log, job payload). This allows you to trace a single request through all logs across all systems.

---

### 3.4 Error Handling

**Explanation:**
Errors in an integrated system can come from anywhere: invalid input, database failures, cache unavailability, external API errors, job failures. How you handle errors defines the reliability of your system.

**Categories of errors:**

| Type | Example | Handling |
|------|---------|----------|
| Validation error | Invalid email format | Return 400, clear message, no logging needed |
| Not found | User ID doesn't exist | Return 404 |
| Database error | Connection failed | Return 500, log the error with context |
| External API error | Stripe timeout | Retry with backoff, return 503 or queue the job |
| Unexpected error | NullPointerException | Return 500, log full stack trace |

**Error response format — be consistent:**
```json
{
  "error": "VALIDATION_ERROR",
  "message": "Email is required",
  "requestId": "abc-123"
}
```

**Never expose internal details to clients:**
Stack traces, SQL errors, file paths, library names — these belong in server logs, not in API responses. They are information for attackers.

**Key principle:**
Handle errors at the appropriate layer. Validation errors are handled at the API. Database errors are caught and translated to meaningful responses. Jobs retry on transient failures and move to DLQ on persistent ones.

---

### 3.5 How a Complete Request Flows

Let's trace a "user places an order" flow through the full stack:

```
1. POST /orders
   ↓
2. API: Validate request body (required fields, types)
   ↓
3. API: Check auth — GET session:{token} from Redis
   → 401 if not found
   ↓
4. API: Check rate limit — INCR rate_limit:{userId} in Redis
   → 429 if exceeded
   ↓
5. DB: BEGIN transaction
6. DB: INSERT INTO orders (user_id, items, status='pending')
7. DB: UPDATE inventory SET stock = stock - 1 WHERE product_id = X
8. DB: COMMIT
   ↓
9. Queue: Enqueue job { type: 'process_payment', orderId: 123 }
   ↓
10. API: Return 202 Accepted { orderId: 123, status: 'pending' }
   ↓
11. Worker: Dequeue job
12. Worker: Fetch order from DB (not from cache — needs fresh data)
13. Worker: Call Stripe API to charge card
14. Worker: UPDATE orders SET status = 'completed'
15. Worker: Enqueue job { type: 'send_confirmation_email', orderId: 123 }
16. Worker: Acknowledge job
   ↓
17. Email Worker: Send order confirmation email
```

Each step involves a different component. A failure at step 13 (Stripe down) triggers a retry. A failure at step 7 (inventory update) triggers a rollback that also rolls back step 6.

---

## 4. Simple Example

```
// Integrated API handler (pseudo-code)

async function createOrder(req, res) {
  const requestId = generateUUID();

  try {
    // Logging
    logger.info({ requestId, userId: req.user.id, action: 'create_order_start' });

    // Validation
    if (!req.body.items?.length) {
      return res.status(400).json({ error: 'VALIDATION_ERROR', message: 'Items required' });
    }

    // Database transaction
    const order = await db.transaction(async (trx) => {
      const o = await trx.insert('orders', { userId: req.user.id, status: 'pending' });
      await trx.update('inventory', { stock: db.raw('stock - 1') }, { productId: item.productId });
      return o;
    });

    // Cache invalidation (user's order list may be cached)
    await redis.del(`user:${req.user.id}:orders`);

    // Async job
    await queue.add('process_payment', { orderId: order.id, requestId });

    logger.info({ requestId, orderId: order.id, action: 'create_order_queued' });

    return res.status(202).json({ orderId: order.id, status: 'pending' });

  } catch (err) {
    logger.error({ requestId, err: err.message, stack: err.stack, action: 'create_order_failed' });
    return res.status(500).json({ error: 'INTERNAL_ERROR', requestId });
  }
}
```

---

## 5. System Perspective

**In production:**
- The bottleneck in most systems is the database. Cache aggressively to protect it.
- Workers and API servers scale independently. Under a job backlog, add workers. Under request load, add API servers. Neither affects the other.
- Use health check endpoints for each component: `/health` should verify DB connectivity, Redis connectivity, and queue broker connectivity.

**Under high traffic:**
- Caching protects the DB. The DB should only receive reads for cache misses and all writes.
- The queue absorbs bursts. An API that can handle 10,000 requests/minute can enqueue 10,000 jobs/minute even if workers can only process 1,000/minute — the backlog clears over time.
- Connection pooling for PostgreSQL is mandatory at scale. Each API server thread should share a pool, not open new connections per request.

**Under failure:**
- Single point of failure analysis: what happens if PostgreSQL goes down? Redis? The queue broker? Each component's failure should have a defined behavior.
- Circuit breakers: if Redis is unavailable, don't retry every request — fast-fail and fall back to direct DB reads.
- Graceful degradation: the system operates in a reduced capacity (slower, without caching) rather than returning errors entirely.

---

## 6. Diagram Section

![Diagram Placeholder](./images/backend-integration.png)

**What the diagram should show:**
- A full system architecture diagram:
  - Client at the top
  - API Server in the middle (connected to Redis, PostgreSQL, and Queue)
  - Redis to the upper-right (labeled "Cache / Sessions / Rate Limit")
  - PostgreSQL to the lower-right (labeled "Source of Truth")
  - Queue in the center-right (labeled "Job Queue")
  - Worker at the bottom (consuming from Queue, connecting to PostgreSQL and external APIs)
- Arrows with labels: "Read (Cache-Aside)", "Write (Invalidate)", "Enqueue", "Dequeue", "Execute"
- A separate flowchart: the full "place order" request traced through all components

---

## 7. Common Mistakes

**1. Using cache as source of truth**
If a write to the DB fails, the cache should not be updated. If a write to the DB succeeds, the cache must be invalidated. The DB is always the authority.

**2. Not using transactions for multi-table writes**
An order creation that inserts to `orders` and updates `inventory` must be in one transaction. Partial success corrupts your data.

**3. Logging at the wrong level**
Logging every SQL query at `INFO` level in production generates noise and cost. Use `DEBUG` for verbose output, `INFO` for meaningful events, `ERROR` for actual errors.

**4. Not including a correlation ID**
Without request IDs, you cannot trace a single user's request through logs from the API, worker, and database. Every log line should carry the request ID.

**5. Exposing internal errors to clients**
Returning raw stack traces or SQL errors in API responses is a security vulnerability. Translate errors to user-safe messages.

**6. Designing workers that hit the cache**
Workers should read fresh data from the database. The cache is for the read path from the API. A payment worker reading stale cached order data can process incorrect amounts.

---

## 8. Interview / Thinking Questions

1. Trace a user registration request through your system: API → DB → Cache → Queue. What happens at each step, and what failures are possible?

2. Your API writes to the database and then updates the cache. The database write succeeds but then the process crashes before updating the cache. What state is your system in? How do you handle this?

3. How does a request ID (correlation ID) help you debug a production issue?

4. You have an API server, a cache, a database, and a worker. Which of these should you scale first when you start seeing slow API responses under high load?

5. What is graceful degradation? Give an example of how your system should behave when Redis is unavailable.

---

## 9. Build It Yourself

**Task: Build a complete integrated mini-backend**

Build a small "task management" API that integrates all components:

**Features:**
1. `POST /register` — create user, store password hash in PostgreSQL, enqueue welcome email job
2. `POST /login` — verify credentials, create Redis session, return session token
3. `GET /tasks` — protected endpoint, read from Redis cache first, fall back to PostgreSQL
4. `POST /tasks` — create task in PostgreSQL, invalidate task list cache, enqueue "send task reminder" job (fires after 1 hour)
5. `DELETE /tasks/:id` — soft delete in PostgreSQL, invalidate cache

**Requirements:**
- Every endpoint logs: request ID, user ID, action, duration
- Rate limit: 20 requests/minute per user
- Worker handles: welcome email, task reminder email
- All multi-step DB operations use transactions
- Return proper HTTP status codes (200, 201, 202, 400, 401, 429, 500)

This project forces you to integrate all Phase 1 concepts in one working system.

---

## 10. Use AI vs Think Yourself

### Use AI For:
- Boilerplate for connecting multiple services (DB client, Redis client, queue)
- Generating consistent error response schemas
- Writing repetitive CRUD handlers
- Setting up Docker Compose for local development (PostgreSQL + Redis + your app)

### Must Understand Yourself:
- Where each piece of data should live and why (DB vs cache vs job payload)
- The correct ordering of operations (write DB first, then update cache — not the other way)
- How your system fails at each integration point — what is the user experience?
- When to use a transaction vs when it's not needed
- How to trace a request through the system end-to-end when debugging

---

## 11. Key Takeaways

- Integration is about data flow, ordering, and failure modes — not just connecting components.
- PostgreSQL is the source of truth. Redis accelerates reads. The queue decouples slow operations.
- Write to the database first. Update the cache after. Never the reverse.
- Correlation IDs make distributed debugging possible. Every log entry needs one.
- Design for failure at every integration point. What happens when each component is unavailable?
- The Phase 1 capstone project should combine all of these — API + PostgreSQL + Redis + Queue + Worker — into one working system.
