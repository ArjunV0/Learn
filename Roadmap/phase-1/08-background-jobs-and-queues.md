# Background Jobs & Queues

## 1. Overview

Not everything a user triggers should be done immediately, in the same HTTP request.

Sending an email, resizing an image, generating a PDF, syncing data with a third-party service — these are operations that are slow, error-prone, or irrelevant to what the user is waiting for. Making the user wait for all of this is poor UX and fragile architecture.

Background jobs solve this: the API responds immediately ("got it, we're processing"), and the actual work happens asynchronously — in a separate process, at its own pace, with its own retry logic.

A queue is the mechanism that connects the API (which creates the job) to the worker (which executes it).

---

## 2. Why This Matters

**Where it is used:**
- Email/SMS notifications after a user action
- Image processing, video transcoding
- Payment processing, refunds
- Report generation
- Webhooks to external services
- Scheduled recurring tasks (cleanup jobs, billing cycles)

**Problems it solves:**
- Slow third-party APIs: your API doesn't have to wait for Stripe, Twilio, or SendGrid to respond.
- Transient failures: if the email service is down, retry the job later rather than failing the request.
- Traffic spikes: queue absorbs bursts. Workers process at a steady rate. The system doesn't collapse under load.

**Why engineers must understand this:**
- Async processing is one of the most common architectural patterns. Almost every production backend uses it.
- Getting retry logic and idempotency wrong creates real bugs: duplicate emails, double-charged payments, inconsistent state.

---

## 3. Core Concepts (Deep Dive)

### 3.1 Why Async Processing Exists

**Explanation:**
The synchronous request-response model has constraints:
- HTTP timeouts: browsers and clients time out after 30–60 seconds
- User experience: users shouldn't wait 10 seconds for an email confirmation to send
- Reliability: a failure in a downstream service (email provider) shouldn't fail your API

**Intuition:**
When you book a flight online, the website confirms your booking immediately. The seat assignment, boarding pass generation, and email sending all happen in the background. You don't wait at the checkout page for all of that.

---

### 3.2 Queue Basics

**Explanation:**
A queue is a data structure where jobs are added at one end (enqueue/produce) and consumed at the other end (dequeue/consume). It follows FIFO (First In, First Out) by default.

```
Producer (API) → [Job 1] [Job 2] [Job 3] → Consumer (Worker)
                  ←←← Queue ←←←
```

**Key concepts:**

**Job/Message:**
A unit of work. Typically a JSON object containing all the context needed to do the work:
```json
{
  "type": "send_welcome_email",
  "userId": 42,
  "email": "alice@example.com"
}
```

**Producer:**
The part of the system that creates and enqueues jobs. Usually your API server.

**Consumer / Worker:**
The separate process that reads from the queue and executes the job.

**Queue Broker:**
The system that stores and routes jobs between producers and consumers. Common options: Redis (BullMQ), RabbitMQ, AWS SQS, Kafka (for streaming, slightly different model).

---

### 3.3 Worker Systems

**Explanation:**
A worker is a long-running process that polls the queue, picks up jobs, executes them, and marks them as complete (or failed).

**Worker lifecycle per job:**
```
1. Pick up next available job from queue
2. Mark job as "processing" (lock it so other workers don't pick it up)
3. Execute the job logic
4. On success: acknowledge/remove the job
5. On failure: mark as failed, increment retry count
```

**Concurrency:**
You can run multiple workers in parallel to increase throughput. Each worker picks up a different job.

**Intuition:**
A restaurant kitchen. Orders (jobs) come in on a ticket rail (queue). Multiple chefs (workers) each grab a ticket, cook the dish, and deliver it. If one chef gets sick mid-order (failure), the ticket goes back on the rail for another chef.

---

### 3.4 Retry Mechanisms

**Explanation:**
Jobs fail. Third-party APIs are down, network blips occur, bugs exist. A good queue system retries failed jobs automatically.

**Retry with exponential backoff:**
Don't retry immediately — wait progressively longer between attempts.

```
Attempt 1: immediate
Attempt 2: wait 5 seconds
Attempt 3: wait 25 seconds
Attempt 4: wait 125 seconds
...
Max attempts: 5 (then move to dead letter queue)
```

**Why exponential backoff:**
If a service is down, hammering it with retries every second makes it worse. Backing off gives the service time to recover.

**Dead Letter Queue (DLQ):**
Jobs that exceed the maximum retry count are moved to a DLQ. They don't disappear — they wait for manual inspection or a separate recovery process.

**Intuition:**
A DLQ is the "undeliverable mail" bin at a post office. The system didn't throw the letter away — it's there waiting for someone to investigate why it couldn't be delivered.

---

### 3.5 Idempotency — The Critical Concept

**Explanation:**
An operation is idempotent if executing it multiple times produces the same result as executing it once.

**Why it matters for jobs:**
A job might be executed more than once — network glitches, worker crashes after execution but before acknowledgment, or bugs. If your job is not idempotent, duplicate execution causes real problems.

**Examples:**

| Operation | Idempotent? | Fix if not |
|-----------|-------------|------------|
| Send welcome email | No — user gets 2 emails | Track sent status in DB, check before sending |
| Charge a credit card | No — user gets charged twice | Use idempotency key with Stripe API |
| Set user status = 'verified' | Yes — setting same value twice is fine | Already idempotent |
| Increment view count | No — count inflated | Use "process each job ID at most once" pattern |

**Design principle:**
Before implementing a job, ask: "If this runs twice, what happens?" If the answer is bad, add an idempotency check.

---

## 4. Simple Example

```
// API server: enqueue a job
app.post('/users/register', async (req, res) => {
  const user = await db.createUser(req.body);

  // Respond immediately — don't wait for the email
  res.json({ success: true, userId: user.id });

  // Enqueue the email job
  await queue.add('send_welcome_email', {
    userId: user.id,
    email: user.email
  });
});

// Worker: process the job
queue.process('send_welcome_email', async (job) => {
  const { userId, email } = job.data;

  // Idempotency check
  const alreadySent = await db.query(
    'SELECT 1 FROM sent_emails WHERE user_id = $1 AND type = $2',
    [userId, 'welcome']
  );
  if (alreadySent) return;  // Already done, skip

  await emailService.send(email, 'Welcome!', welcomeTemplate);

  await db.query(
    'INSERT INTO sent_emails (user_id, type) VALUES ($1, $2)',
    [userId, 'welcome']
  );
});
```

---

## 5. System Perspective

**In production:**
- BullMQ (Redis-backed) is the standard for Node.js. Celery (Python), Sidekiq (Ruby) are popular in their ecosystems.
- Separate your workers from your API servers — they scale independently. More jobs? Add more workers.
- Monitor queue depth. If jobs are piling up faster than workers consume them, you need more workers or a faster execution path.

**Under high traffic:**
- Queues absorb bursts: 10,000 registration emails during a product launch don't overwhelm your email provider. Workers process them at a controlled rate.
- Backpressure: if the queue grows indefinitely, you have a capacity problem. Set queue size limits and alert on high depth.
- Priority queues: not all jobs are equal. Payment confirmations should be processed before weekly digest emails.

**Under failure:**
- If a worker crashes mid-job, the job must be re-queued. This is why most queue systems use a "visibility timeout" — a job is locked for N seconds while being processed. If the worker doesn't acknowledge within that window, the queue releases the job for another worker.
- At-least-once delivery: most queues guarantee delivery at least once (may be more). This is why idempotency is mandatory.
- Exactly-once delivery is nearly impossible to guarantee in distributed systems. Design around at-least-once.

---

## 6. Diagram Section

![Diagram Placeholder](./images/background-jobs-queues.png)

**What the diagram should show:**
- Left box: "API Server" with an arrow labeled "enqueue job" pointing to the queue
- Center: Queue shown as a horizontal pipe with job boxes [Job A] [Job B] [Job C]
- Right: Multiple "Worker" boxes pulling from the queue
- Below the Worker: arrows for "Success → ACK (remove job)" and "Failure → Retry with backoff → DLQ after max attempts"
- A separate small diagram showing exponential backoff: Attempt 1, 2, 3, 4, 5 on a timeline with increasing gaps

---

## 7. Common Mistakes

**1. Not designing for idempotency**
Assuming a job runs exactly once is wrong. It will run more than once eventually. The consequences range from duplicate emails to double-charged users.

**2. Doing synchronous work in the API handler that should be async**
Calling `sendEmail()` or `generatePDF()` directly in the request handler and making the user wait. Offload anything slow or non-critical to a queue.

**3. Not monitoring queue depth**
A queue silently filling up means your workers can't keep up. Without alerting on queue depth, you don't know until the backlog is hours deep.

**4. Storing too much data in the job payload**
Store the minimum needed (IDs, not full objects). Data in the job payload can become stale by the time the job runs. Fetch fresh data in the worker.

**5. Not handling the DLQ**
Jobs in the DLQ are failing for a reason. Ignoring the DLQ means important operations (payment webhooks, critical emails) silently stop happening.

**6. Treating queues as guaranteed ordered delivery**
Most job queues don't guarantee strict ordering under concurrency. If order matters, design explicitly for it (sequence numbers, dependency chains).

---

## 8. Interview / Thinking Questions

1. When should you use a background job instead of handling the operation synchronously in an HTTP request?

2. What is idempotency? Why is it required for background jobs, and how do you implement it?

3. Explain exponential backoff. Why is it better than retrying immediately on failure?

4. Your worker processes a payment confirmation job and the worker crashes after sending the confirmation but before acknowledging the queue. What happens next, and what must your job implementation handle?

5. How do you scale a background job system to handle 10x more jobs? What are the limits of that scaling?

---

## 9. Build It Yourself

**Task: Build a job queue system with retries**

1. Set up BullMQ (Node.js) or Celery (Python) with Redis as the broker
2. Build a job type: `send_email` with fields `{to, subject, body}`
3. Build a producer: an API endpoint `POST /send` that enqueues the job and returns 202 Accepted immediately
4. Build a worker that processes the job — simulate with `console.log` or use a real email service
5. Add idempotency: store a `job_id` in the database, skip if already processed
6. Simulate failure: make the worker throw an error 70% of the time — observe retries with exponential backoff
7. Let a job fail all retries — observe it land in the DLQ
8. Add a `GET /queue/stats` endpoint that shows: pending jobs, active jobs, failed jobs (DLQ depth)

---

## 10. Use AI vs Think Yourself

### Use AI For:
- BullMQ / Celery configuration boilerplate
- Setting up exponential backoff options in your queue library
- Generating test job payloads
- Syntax for queue event listeners

### Must Understand Yourself:
- Whether a given operation should be synchronous or async — this is an architectural decision
- How to implement idempotency for your specific job type — depends on business logic
- What happens when a job fails all retries — what is the human/system response?
- How many workers you need — requires understanding your job throughput and processing time

---

## 11. Key Takeaways

- Background jobs decouple slow, error-prone, or non-critical operations from the request-response cycle.
- A queue is the bridge between the producer (API) and the consumer (worker).
- Retry with exponential backoff handles transient failures gracefully.
- Idempotency is non-negotiable. Jobs will run more than once. Design for it.
- The Dead Letter Queue is your safety net — always monitor it.
- Most queues guarantee at-least-once delivery, not exactly-once. Your code must handle duplicates.
