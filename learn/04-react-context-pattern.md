# Module 4: React Context Pattern (null + Guard Hook)

## What Problem Does Context Solve?

Without context, passing data through many levels of components requires **prop drilling:**

```tsx
// Without context — prop drilling nightmare
<App theme="dark">
  <Layout theme="dark">
    <Sidebar theme="dark">
      <NavItem theme="dark">     {/* 4 levels deep just to pass theme! */}
```

Context lets any descendant access the data directly:

```tsx
// With context — any child can access theme
<ThemeProvider>        {/* provides theme */}
  <Layout>
    <Sidebar>
      <NavItem />      {/* useTheme() — gets theme directly */}
```

---

## The Three Parts of Context

```tsx
// 1. CREATE the context (with a default value)
const ThemeContext = createContext<ThemeContextValue | null>(null)

// 2. PROVIDE the context (wraps the component tree)
function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(DEFAULT_THEME)
  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}

// 3. CONSUME the context (any descendant component)
function NavItem() {
  const { theme } = useTheme()  // custom hook that reads context
}
```

---

## Why `null` as Default Value?

`createContext` requires a default value. You have two choices:

### Option A: Provide a real default
```tsx
const ThemeContext = createContext<ThemeContextValue>({
  theme: "light",
  toggleTheme: () => {},  // does nothing — silent failure
})
```

**Problem:** If someone forgets to wrap with `<ThemeProvider>`, the app uses this dummy default. `toggleTheme()` does nothing. No error. The developer spends hours debugging why the theme won't change.

### Option B: Use `null` + guard hook (recommended)
```tsx
const ThemeContext = createContext<ThemeContextValue | null>(null)

function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext)
  if (context === null) {
    throw new Error("useTheme must be used within a <ThemeProvider>")
  }
  return context
}
```

**Benefit:** If someone forgets the provider, they get an **immediate, clear error message** telling them exactly what's wrong. This is the **fail-fast** principle — errors should be loud and early, not quiet and late.

---

## Fail-Fast Principle

A core software engineering principle:

> **Fail fast:** When something goes wrong, fail immediately and visibly rather than continuing with bad data and failing later in a confusing way.

| Fail Fast (Good) | Fail Slow (Bad) |
|---|---|
| Throws error when provider is missing | Silently uses empty default |
| Error message says exactly what's wrong | App "works" but theme never changes |
| Developer fixes it in 30 seconds | Developer debugs for hours |

This principle applies everywhere:
- **Type checking:** Catch type errors at compile time, not runtime
- **Input validation:** Reject bad data at the API boundary, not deep in business logic
- **Context hooks:** Throw when provider is missing, don't return dummy values

---

## The Complete Pattern

Here's the full, production-ready context pattern:

```tsx
// ThemeProvider.tsx
import { createContext, useCallback, useContext, useMemo, useState } from "react"

// --- Types ---
type Theme = "light" | "dark"

interface ThemeContextValue {
  theme: Theme
  toggleTheme: () => void
}

// --- Context (null default = fail-fast) ---
const ThemeContext = createContext<ThemeContextValue | null>(null)

// --- Provider ---
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<Theme>("light")

  const toggleTheme = useCallback(() => {
    setTheme(prev => prev === "dark" ? "light" : "dark")
  }, [])

  // useMemo prevents the value object from being recreated every render
  const value = useMemo(() => ({ theme, toggleTheme }), [theme, toggleTheme])

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  )
}

// --- Custom Hook (the guard) ---
export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error("useTheme must be used within a <ThemeProvider>")
  }
  return context
}
```

### Why `useMemo` on the value?

Without `useMemo`:
```tsx
// New object created EVERY render — triggers re-render of ALL consumers
value={{ theme, toggleTheme }}
```

Even if `theme` hasn't changed, `{ theme, toggleTheme }` is a new object reference each render. Every consumer sees a "new" value and re-renders.

With `useMemo`:
```tsx
// Same object reference unless theme or toggleTheme actually changes
const value = useMemo(() => ({ theme, toggleTheme }), [theme, toggleTheme])
```

Only re-renders consumers when the actual data changes.

### Why `useCallback` on `toggleTheme`?

Same idea — without `useCallback`, `toggleTheme` is a new function every render, which would cause `useMemo` to see a changed dependency and recreate the value object anyway.

---

## Context Composition

Real apps often have multiple contexts:

```tsx
// app/layout.tsx
export default function RootLayout({ children }) {
  return (
    <ThemeProvider>
      <PlayerProvider>
        <SearchProvider>
          {children}
        </SearchProvider>
      </PlayerProvider>
    </ThemeProvider>
  )
}
```

Each context is independent. Each has its own `null` + guard pattern. A component can consume multiple contexts:

```tsx
function PlayerBar() {
  const { theme } = useTheme()
  const { currentSong, isPlaying } = usePlayer()
  // ...
}
```

---

## When NOT to Use Context

Context is for **global or semi-global state** (theme, auth, player, locale). Don't use it for:

- **Frequently changing values** (mouse position, scroll position) — causes too many re-renders
- **Local component state** (form inputs, toggle states) — `useState` is simpler
- **Server state** (API data) — use React Query, SWR, or similar

**Rule of thumb:** If only one component (and its children) need the data, use `useState` + props. If unrelated components across the tree need it, use context.

---

## Related Concepts
- **useState / useRef (Module 3):** Context uses state internally
- **useMemo / useCallback:** Optimize context value to prevent unnecessary re-renders
- **Provider Pattern:** A design pattern where a wrapper component provides data to its children
- **Dependency Injection:** Context is React's version of DI — components receive dependencies from above, not by importing directly

---

## Summary

| Concept | Implementation |
|---------|---------------|
| Create with null | `createContext<T \| null>(null)` |
| Guard hook | `if (!context) throw new Error(...)` |
| Memoize value | `useMemo(() => ({ ... }), [deps])` |
| Stable callbacks | `useCallback(() => { ... }, [deps])` |
| Fail-fast | Loud error > silent wrong behavior |
