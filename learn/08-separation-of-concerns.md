# Module 8: Separation of Concerns & Service Layer

## What is Separation of Concerns?

Each piece of code should have **one job**. When a module does too many things, it becomes:
- Hard to test (you have to set up everything just to test one thing)
- Hard to change (modifying one part risks breaking another)
- Hard to understand (you have to hold the whole thing in your head)

---

## The Problem: Fat Route Handlers

Here's a route handler doing too much:

```ts
// app/api/songs/route.ts — does EVERYTHING
export async function GET(request: Request) {
  // 1. Parse and validate the request
  const { searchParams } = new URL(request.url)
  const parsed = schema.safeParse({
    term: searchParams.get("term"),
    limit: Number(searchParams.get("limit")),
  })
  if (!parsed.success) return NextResponse.json({ error: "Invalid" }, { status: 400 })

  // 2. Build the external API request
  const params = new URLSearchParams({
    term: parsed.data.term,
    media: "music",
    limit: String(parsed.data.limit),
  })

  // 3. Call the external API
  const response = await fetch(`https://itunes.apple.com/search?${params}`)
  const json = await response.json()

  // 4. Transform the response
  const songs = json.results.map((r: any) => ({
    id: String(r.trackId),
    title: r.trackName,
    artist: r.artistName,
    coverUrl: r.artworkUrl100.replace("100x100", "300x300"),
  }))

  // 5. Return the response
  return NextResponse.json(songs)
}
```

This single function handles: validation, URL construction, API communication, data transformation, and HTTP response formatting. Five responsibilities.

---

## The Solution: Layered Architecture

Split the code into layers, each with one responsibility:

```
┌─────────────────────────┐
│  Route Handler (route.ts)│  ← HTTP concerns (request/response)
├─────────────────────────┤
│  Service (itunesService) │  ← Business logic (fetch + transform)
├─────────────────────────┤
│  Types / Models          │  ← Data shapes
└─────────────────────────┘
```

### Layer 1: Service (business logic)
```ts
// lib/services/itunesService.ts

import { ITUNES_SEARCH_URL, ARTWORK_SIZE_SMALL, ARTWORK_SIZE_LARGE } from "@/lib/constants"
import type { Song } from "@/types"

interface SearchParams {
  term: string
  limit: number
}

export async function searchSongs({ term, limit }: SearchParams): Promise<Song[]> {
  const params = new URLSearchParams({
    term,
    media: "music",
    limit: String(limit),
  })

  const response = await fetch(`${ITUNES_SEARCH_URL}?${params}`)

  if (!response.ok) {
    throw new Error(`iTunes API error: ${response.status}`)
  }

  const json = await response.json()

  return json.results.map((r: any) => ({
    id: String(r.trackId),
    title: r.trackName,
    artist: r.artistName,
    coverUrl: r.artworkUrl100.replace(ARTWORK_SIZE_SMALL, ARTWORK_SIZE_LARGE),
  }))
}
```

### Layer 2: Route handler (HTTP concerns only)
```ts
// app/api/songs/route.ts

import { searchSongs } from "@/lib/services/itunesService"

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const parsed = schema.safeParse({
    term: searchParams.get("term"),
    limit: Number(searchParams.get("limit")),
  })

  if (!parsed.success) {
    return NextResponse.json({ error: "Invalid parameters" }, { status: 400 })
  }

  try {
    const songs = await searchSongs(parsed.data)
    return NextResponse.json(songs)
  } catch (error) {
    return NextResponse.json({ error: "Failed to fetch songs" }, { status: 502 })
  }
}
```

---

## Why This Is Better

### Testability
```ts
// Test the service WITHOUT an HTTP server
test("searchSongs transforms iTunes response correctly", async () => {
  // Mock fetch to return fake iTunes data
  global.fetch = jest.fn(() => Promise.resolve({
    ok: true,
    json: () => Promise.resolve({ results: [mockItunesResult] }),
  }))

  const songs = await searchSongs({ term: "test", limit: 5 })
  expect(songs[0].title).toBe("Expected Title")
})

// Test the route WITHOUT calling iTunes
test("GET /api/songs returns 400 for missing params", async () => {
  const request = new Request("http://localhost/api/songs")
  const response = await GET(request)
  expect(response.status).toBe(400)
})
```

Without separation, testing the route **always** calls the real iTunes API. Slow, flaky, and rate-limited.

### Reusability
```ts
// Another route can use the same service
// app/api/playlist/route.ts
import { searchSongs } from "@/lib/services/itunesService"

// A server component can use it directly
// app/discover/page.tsx
import { searchSongs } from "@/lib/services/itunesService"
```

### Changeability
If iTunes changes their API or you switch to Spotify:
- **Without separation:** Modify route handlers everywhere
- **With separation:** Change `itunesService.ts` → everything else stays the same

---

## Single Responsibility Principle (SRP)

> A module should have one, and only one, reason to change.

| Module | Responsibility | Reason to Change |
|--------|---------------|-----------------|
| `route.ts` | Handle HTTP request/response | Request format changes |
| `itunesService.ts` | Fetch & transform iTunes data | iTunes API changes |
| `schema.ts` | Validate input parameters | Validation rules change |
| `types.ts` | Define data shapes | Data model changes |

Each has exactly one reason to change. A change to iTunes API format only touches the service. A change to validation rules only touches the schema.

---

## Where to Put Services

```
lib/
  services/
    itunesService.ts     ← External API communication
    searchService.ts     ← Search-specific business logic
  constants.ts
  utils/
    format.ts
```

Or feature-scoped:
```
features/
  home/
    services/
      itunesService.ts
  search/
    services/
      searchService.ts
```

Both are valid. Choose based on team convention.

---

## Deeper: The Three-Layer Architecture

In larger apps, you might see three layers:

```
┌────────────────────┐
│  Controller/Route   │  ← HTTP layer (parse request, format response)
├────────────────────┤
│  Service            │  ← Business logic (rules, orchestration)
├────────────────────┤
│  Repository/Client  │  ← Data access (database, external APIs)
└────────────────────┘
```

For PlayNext:
```
Route (route.ts)
  └── validates request, returns response
Service (itunesService.ts)
  └── orchestrates data fetching, transforms results
Client (itunesClient.ts) — optional for larger apps
  └── raw HTTP calls to iTunes API
```

You don't need all three layers for a small app. Two (route + service) is usually enough.

---

## Related Concepts
- **Dependency Injection:** Pass services as parameters instead of importing directly (helps testing)
- **Repository Pattern:** Abstracts data storage behind an interface
- **Hexagonal Architecture:** Ports and adapters — business logic doesn't know about HTTP or databases
- **Module 6 (Error Handling):** Services should throw meaningful errors; routes should catch and format them

---

## Summary

| Principle | Before | After |
|-----------|--------|-------|
| Single Responsibility | Route does everything | Route handles HTTP, service handles logic |
| Testability | Must mock entire request cycle | Test each layer independently |
| Reusability | Logic trapped in route handler | Service usable from anywhere |
| Changeability | API change affects route handler | API change isolated to service |
