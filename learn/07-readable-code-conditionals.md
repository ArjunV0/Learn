# Module 7: Readable Code & Conditionals

## Why Readability Matters

Code is **read far more often than it is written.** You write a line once but it gets read by:
- You, 3 months from now (you won't remember what you meant)
- Teammates reviewing your PR
- Future developers maintaining the code

> "Any fool can write code that a computer can understand. Good programmers write code that humans can understand." — Martin Fowler

---

## Problem: Complex Inline Conditionals

```tsx
// Hard to parse at a glance
{isQueryEmpty && recentSearches.length > 0 && (
  <div className="recent-searches">
    {recentSearches.map(s => <RecentItem key={s} query={s} />)}
  </div>
)}
```

When reading this, your brain has to:
1. Parse `isQueryEmpty` — ok, the query is empty
2. Parse `recentSearches.length > 0` — and there are recent searches
3. Combine them — so we show recent searches when there's no query and history exists
4. Then read the JSX

That's a lot of mental work for every reader, every time.

---

## Solution 1: Named Boolean Variables

Extract conditions into descriptively named variables:

```tsx
const hasRecentSearches = recentSearches.length > 0
const shouldShowRecentSearches = isQueryEmpty && hasRecentSearches

// Now the JSX reads like English
{shouldShowRecentSearches && (
  <div className="recent-searches">
    {recentSearches.map(s => <RecentItem key={s} query={s} />)}
  </div>
)}
```

The variable name tells you **why** we're showing it, not just **what** the conditions are.

---

## Solution 2: Helper Functions for Reusable Checks

```ts
// lib/utils/array.ts
export const isNonEmpty = <T>(arr: T[]): boolean => arr.length > 0
export const isEmpty = <T>(arr: T[]): boolean => arr.length === 0
```

```tsx
const shouldShowRecentSearches = isQueryEmpty && isNonEmpty(recentSearches)
```

**When to extract a helper vs just a variable:**
- Variable: Used in one component, context-specific
- Helper function: Used across multiple components, generic check

---

## Solution 3: Early Returns

Instead of deeply nested conditionals, return early for edge cases:

### Before (nested)
```tsx
function SearchResults({ query, results, isLoading, error }) {
  return (
    <div>
      {error ? (
        <ErrorMessage>{error}</ErrorMessage>
      ) : isLoading ? (
        <Spinner />
      ) : results.length > 0 ? (
        <ul>{results.map(r => <ResultItem key={r.id} result={r} />)}</ul>
      ) : (
        <EmptyState>No results found</EmptyState>
      )}
    </div>
  )
}
```

### After (early returns)
```tsx
function SearchResults({ query, results, isLoading, error }) {
  if (error) return <ErrorMessage>{error}</ErrorMessage>
  if (isLoading) return <Spinner />
  if (results.length === 0) return <EmptyState>No results found</EmptyState>

  return (
    <ul>
      {results.map(r => <ResultItem key={r.id} result={r} />)}
    </ul>
  )
}
```

Each condition is handled independently. No nesting. The "happy path" (results exist) is the final return, unindented.

---

## Solution 4: Extract Sub-Components

When a section of JSX is complex, extract it:

### Before
```tsx
{isLoading ? (
  <>
    {Array.from({ length: 6 }).map((_, i) => (
      <div key={i} className="animate-pulse bg-gray-200 rounded-lg h-48" />
    ))}
  </>
) : (
  albums.map(album => (
    <AlbumCard key={album.id} album={album} onClick={onAlbumClick} />
  ))
)}
```

### After
```tsx
function AlbumSkeletons({ count = 6 }: { count?: number }) {
  return (
    <>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="animate-pulse bg-gray-200 rounded-lg h-48" />
      ))}
    </>
  )
}

// In the parent:
{isLoading ? <AlbumSkeletons /> : <AlbumGrid albums={albums} onClick={onAlbumClick} />}
```

---

## Ternary vs && vs if/else

### When to use `&&` (logical AND)
```tsx
// Good — simple show/hide
{isLoggedIn && <LogoutButton />}

// Bad — complex, hard to read
{isLoggedIn && hasPermission && !isLoading && items.length > 0 && <ItemList />}
```

### When to use ternary `? :`
```tsx
// Good — simple either/or
{isPlaying ? <PauseIcon /> : <PlayIcon />}

// Bad — nested ternaries
{isLoading ? <Spinner /> : error ? <Error /> : data ? <Results /> : <Empty />}
```

### When to use if/else (early returns)
```tsx
// Good — multiple exclusive states
if (isLoading) return <Spinner />
if (error) return <Error />
if (!data) return <Empty />
return <Results />
```

### Rule of thumb:
- **1 condition, show/hide** → `&&`
- **1 condition, either/or** → ternary
- **2+ conditions** → early returns or named variables

---

## Gotcha: `&&` with Numbers

```tsx
// BUG! When count is 0, this renders "0" on screen
{count && <ItemList items={items} />}

// Fix: explicitly convert to boolean
{count > 0 && <ItemList items={items} />}
// or
{Boolean(count) && <ItemList items={items} />}
```

`&&` returns the first falsy value. `0` is falsy, and React renders `0` as text. `false`, `null`, and `undefined` are not rendered.

---

## Naming Conventions for Booleans

Good boolean names start with `is`, `has`, `should`, `can`, or `did`:

```ts
// State
const isLoading = true
const isPlaying = false
const hasError = error !== null

// Derived
const hasRecentSearches = recentSearches.length > 0
const shouldShowPlayer = currentSong !== null
const canSubmit = isValid && !isLoading
const isQueryEmpty = query.trim().length === 0
```

**Avoid negatives in names:**
```ts
// Bad — double negatives are confusing
if (!isNotReady) { ... }

// Good
if (isReady) { ... }
```

---

## Related Concepts
- **Clean Code:** Robert C. Martin's principles for readable software
- **Cognitive complexity:** How hard code is to understand (fewer branches = lower complexity)
- **Component composition:** Breaking UI into small, focused components
- **Guard clauses:** Early returns that handle edge cases upfront

---

## Summary

| Technique | When to Use |
|-----------|------------|
| Named boolean variables | Complex `&&` or ternary conditions |
| Helper functions (`isNonEmpty`) | Same check used across components |
| Early returns | Multiple exclusive states (loading, error, empty, data) |
| Sub-components | Complex JSX blocks within conditionals |
| Avoid nested ternaries | Always — use early returns instead |
