# Module 2: Utility Functions & DRY Principle

## The DRY Principle

**DRY = Don't Repeat Yourself**

Every piece of knowledge (logic, data, rules) should exist in **one place** in your codebase. If the same logic appears in two places, any change requires updating both — and forgetting one creates bugs.

---

## When to Extract a Utility Function

### Rule of Thumb
- **Used once:** Keep it inline (don't over-abstract)
- **Used twice:** Consider extracting if the logic is non-trivial
- **Used three+ times:** Definitely extract

### Signs You Need a Utility
1. You're copy-pasting logic between files
2. A code reviewer says "this should be reusable"
3. The inline logic is hard to read at a glance
4. You're writing the same transformation in multiple places

---

## Example: Theme Toggle

### Before (inline logic)
```ts
// ThemeProvider.tsx
setTheme(prev => prev === "dark" ? "light" : "dark")

// SettingsPage.tsx (same logic duplicated)
const nextTheme = currentTheme === "dark" ? "light" : "dark"
```

### After (utility function)
```ts
// utils/theme.ts
export const getOppositeTheme = (theme: Theme): Theme =>
  theme === DARK ? LIGHT : DARK

// ThemeProvider.tsx
setTheme(prev => getOppositeTheme(prev))

// SettingsPage.tsx
const nextTheme = getOppositeTheme(currentTheme)
```

---

## Example: Duration Formatting

### Before (trapped inside one component)
```ts
// SearchResults.tsx
function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, "0")}`
}
```

### After (shared utility)
```ts
// lib/utils/format.ts
export function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, "0")}`
}

// Now usable from SearchResults, PlayerBar, QueueList, etc.
```

---

## Example: Array Helpers

```ts
// lib/utils/array.ts
export const isNonEmpty = <T>(arr: T[]): boolean => arr.length > 0
export const isEmpty = <T>(arr: T[]): boolean => arr.length === 0
```

These seem trivial, but they:
- Read like English: `if (isNonEmpty(results))` vs `if (results.length > 0)`
- Centralize the definition of "empty" (what if you later need to handle `null`?)

---

## Pure Functions

The best utility functions are **pure functions** — they:
1. **Always return the same output** for the same input
2. **Have no side effects** (don't modify external state, make API calls, etc.)

```ts
// Pure — same input always gives same output
const getOppositeTheme = (theme: Theme): Theme =>
  theme === DARK ? LIGHT : DARK

// Pure — only depends on its arguments
const formatDuration = (seconds: number): string => {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, "0")}`
}

// NOT pure — depends on external state
const getCurrentTheme = () => document.body.className  // side effect: reads DOM
```

**Why care about purity?**
- Easy to test (no mocking needed)
- Easy to reason about (no hidden dependencies)
- Can be safely called from anywhere without worrying about order or timing

---

## Where to Put Utilities

```
lib/
  utils/
    format.ts     ← formatDuration, formatDate, formatCurrency
    theme.ts      ← getOppositeTheme
    array.ts      ← isNonEmpty, isEmpty
    artwork.ts    ← getArtworkUrl
    index.ts      ← re-exports everything for clean imports
```

The `index.ts` barrel file:
```ts
// lib/utils/index.ts
export { formatDuration } from "./format"
export { getOppositeTheme } from "./theme"
export { isNonEmpty, isEmpty } from "./array"
export { getArtworkUrl } from "./artwork"
```

Now consumers import cleanly:
```ts
import { formatDuration, isNonEmpty } from "@/lib/utils"
```

---

## Anti-Patterns: When NOT to Extract

### Premature abstraction
```ts
// Don't do this — used only once, the inline version is clearer
const isGreaterThanZero = (n: number) => n > 0
const isStringLight = (s: string) => s === "light"
```

### Abstracting things that differ
```ts
// These LOOK similar but serve different purposes — don't force them together
const formatSongDuration = (s: number) => `${Math.floor(s/60)}:${(s%60).toString().padStart(2,"0")}`
const formatCountdown = (s: number) => `${Math.floor(s/60)}m ${s%60}s remaining`
```

### The Rule of Three
Wait until you have **three** instances of duplication before extracting. Two instances might be coincidence. Three is a pattern.

---

## Related Concepts
- **Constants (Module 1):** Constants and utilities work together — utilities use constants
- **Single Responsibility Principle:** Each function does one thing
- **Composition:** Small utilities combine to solve bigger problems
- **Testability:** Pure utility functions are the easiest code to unit test

---

## Summary

| Principle | Application |
|-----------|------------|
| DRY | Extract repeated logic into one function |
| Pure Functions | No side effects, same input = same output |
| Naming | Function name should describe the transformation |
| Placement | `lib/utils/` for shared, feature folder for feature-specific |
| Rule of Three | Extract after seeing 3 instances, not before |
