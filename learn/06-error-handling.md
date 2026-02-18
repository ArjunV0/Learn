# Module 6: Error Handling Strategies

## The Core Problem: Silent Failures

```ts
// This is the code that was reviewed:
if (!response.ok) return []
```

This **swallows the error**. The calling code gets an empty array and thinks "no results found." But the real situation might be:
- The API server is down (500)
- The user's auth token expired (401)
- The URL is wrong (404)
- Rate limiting kicked in (429)

The user sees no results and no error message. They might retry, think the search is broken, or give up. The developer gets no signal that something failed.

---

## Principle: Errors Should Be Visible

> If something goes wrong, the code that handles the result should **know** something went wrong.

Three main strategies:

---

## Strategy 1: Throw an Error

```ts
async function fetchSongs(query: string): Promise<Song[]> {
  const response = await fetch(`/api/songs?q=${query}`)

  if (!response.ok) {
    throw new Error(`Failed to fetch songs: ${response.status} ${response.statusText}`)
  }

  return response.json()
}
```

The **caller** decides how to handle it:
```tsx
function SearchResults() {
  const [songs, setSongs] = useState<Song[]>([])
  const [error, setError] = useState<string | null>(null)

  const search = async (query: string) => {
    try {
      setError(null)
      const results = await fetchSongs(query)
      setSongs(results)
    } catch (err) {
      setError("Something went wrong. Please try again.")
      setSongs([])
    }
  }
}
```

**When to use:** When the caller has the context to handle the error (show a toast, retry, redirect).

---

## Strategy 2: Return a Result Object

Instead of throwing, return an object that explicitly says whether it succeeded or failed:

```ts
type Result<T> =
  | { success: true; data: T }
  | { success: false; error: string }

async function fetchSongs(query: string): Promise<Result<Song[]>> {
  const response = await fetch(`/api/songs?q=${query}`)

  if (!response.ok) {
    return { success: false, error: `API error: ${response.status}` }
  }

  const data = await response.json()
  return { success: true, data }
}
```

The caller:
```tsx
const result = await fetchSongs(query)

if (result.success) {
  setSongs(result.data)
} else {
  setError(result.error)
}
```

**When to use:** When errors are **expected** and part of normal flow (validation errors, not-found, etc.). The caller is forced to handle both cases — you can't accidentally ignore the error.

---

## Strategy 3: Error Boundaries (React-specific)

For unexpected errors that shouldn't crash the whole app:

```tsx
// error-boundary.tsx
"use client"

class ErrorBoundary extends React.Component<Props, State> {
  state = { hasError: false }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  render() {
    if (this.state.hasError) {
      return <p>Something went wrong. Please refresh.</p>
    }
    return this.props.children
  }
}

// Usage — wraps a section of the UI
<ErrorBoundary>
  <SearchResults />    {/* if this throws, ErrorBoundary catches it */}
</ErrorBoundary>
```

Next.js also has built-in `error.tsx` files that act as error boundaries per route segment.

---

## When to Use Which Strategy

| Situation | Strategy |
|-----------|----------|
| API calls that might fail | Throw or Result object |
| User input validation | Result object (errors are expected) |
| Unexpected runtime errors | Error Boundary |
| Third-party API failures | Throw + try/catch at the call site |
| Background operations | Throw + log the error |

---

## Anti-Patterns

### 1. Swallowing errors silently
```ts
// TERRIBLE — error vanishes, impossible to debug
try {
  await fetchSongs(query)
} catch {
  // do nothing
}
```

### 2. Catching too broadly
```ts
// BAD — catches everything, including programming errors
try {
  const response = await fetch(url)
  const data = response.json()  // missing await — TypeError
  setSongs(data.results)
} catch {
  setError("API error")  // actually a code bug, not an API error!
}
```

### 3. Logging but not handling
```ts
// INCOMPLETE — developer sees the error in console, user sees nothing
try {
  const songs = await fetchSongs(query)
  setSongs(songs)
} catch (err) {
  console.error(err)  // and then what? User is stuck staring at a spinner
}
```

### 4. Generic error messages
```ts
// UNHELPFUL — doesn't help the user take action
setError("An error occurred")

// BETTER — tells the user what to do
setError("Unable to load songs. Check your connection and try again.")
```

---

## Error Handling in Fetch: Full Pattern

```ts
async function fetchWithErrorHandling<T>(url: string): Promise<T> {
  let response: Response

  try {
    response = await fetch(url)
  } catch {
    // Network error — server unreachable, no internet, CORS, etc.
    throw new Error("Network error. Please check your connection.")
  }

  if (!response.ok) {
    // Server returned an error status
    throw new Error(`Server error: ${response.status}`)
  }

  try {
    return await response.json()
  } catch {
    // Server returned invalid JSON
    throw new Error("Invalid response from server")
  }
}
```

Three distinct failure points, three distinct error messages.

---

## HTTP Status Codes You Should Know

| Code | Meaning | What to Do |
|------|---------|-----------|
| 200 | OK | Process the response |
| 400 | Bad Request | Fix the request parameters |
| 401 | Unauthorized | Redirect to login |
| 403 | Forbidden | Show "access denied" |
| 404 | Not Found | Show "not found" message |
| 429 | Too Many Requests | Show "slow down" or auto-retry after delay |
| 500 | Internal Server Error | Show generic error, maybe retry |
| 503 | Service Unavailable | Show "try again later" |

---

## Related Concepts
- **try/catch/finally:** JavaScript error handling mechanism
- **Promise rejection:** Unhandled promise rejections crash Node.js
- **Error Boundaries (React):** Catch rendering errors in component trees
- **Defensive programming:** Anticipate what can go wrong and handle it explicitly
- **Fail-fast (Module 4):** Related — errors should surface early and clearly

---

## Summary

| Approach | return [] | throw Error | Result object |
|----------|-----------|-------------|---------------|
| Caller knows about error | No | Yes (must catch) | Yes (must check) |
| UI can show error message | No | Yes | Yes |
| Developer can debug | No | Yes (stack trace) | Partially |
| When to use | Never for API calls | Unexpected failures | Expected failures |
