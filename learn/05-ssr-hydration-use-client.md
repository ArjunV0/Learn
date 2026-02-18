# Module 5: SSR, Hydration & "use client"

## What is Server-Side Rendering (SSR)?

When a user requests a page, the server:
1. Runs your React components as functions
2. Generates the HTML output
3. Sends that HTML to the browser

The user sees content **immediately** — no waiting for JavaScript to download and run.

```
Traditional SPA (Client-Side Rendering):
Browser: blank page → download JS → run JS → render UI
User sees: .........[loading].......[content]

SSR:
Server: runs components → generates HTML → sends to browser
Browser: shows HTML instantly → downloads JS → hydrates
User sees: [content].....................[interactive]
```

---

## What is Hydration?

After the server sends HTML, React needs to "wake up" on the client side. This process is called **hydration:**

1. Browser receives server-rendered HTML (user sees content)
2. Browser downloads the JavaScript bundle
3. React runs your components again in the browser
4. React **attaches event listeners** to the existing HTML
5. The page becomes interactive

**Key point:** React runs your component code **twice** — once on the server, once on the client.

```
Server Render          Client Hydration
─────────────          ─────────────────
Runs component         Runs component AGAIN
Produces HTML          Attaches event handlers
No DOM exists          DOM exists (from server HTML)
No window/document     window/document available
No user interaction    Enables clicks, typing, etc.
```

---

## The "use client" Directive

```tsx
"use client"

import { useState } from "react"

export function ThemeToggle() {
  const [theme, setTheme] = useState("light")
  // ...
}
```

### What "use client" MEANS:
- This is a **Client Component** — it can use hooks (`useState`, `useEffect`, `useRef`), event handlers, and browser APIs
- It marks the **boundary** between server and client components

### What "use client" does NOT mean:
- ~~"This only runs in the browser"~~ **WRONG**
- ~~"This skips server rendering"~~ **WRONG**
- ~~"window is always available here"~~ **WRONG**

**Client components are still server-rendered.** Next.js renders them on the server to generate the initial HTML, then hydrates them on the client. The "use client" directive means they CAN use client features, not that they ONLY run on the client.

---

## Why `typeof window === "undefined"` is Still Needed

During SSR, there is no browser. Browser APIs don't exist:

```ts
// During SSR, these will all crash:
window.localStorage.getItem("theme")   // ReferenceError: window is not defined
document.body.className                // ReferenceError: document is not defined
navigator.userAgent                    // ReferenceError: navigator is not defined
```

The guard check:
```ts
if (typeof window === "undefined") return []
```

This says: "If we're on the server, skip this and return a safe default."

### Why `typeof` instead of direct check?

```ts
// This crashes if window doesn't exist:
if (window === undefined) { }  // ReferenceError!

// This is safe — typeof never throws:
if (typeof window === "undefined") { }  // safe, returns "undefined" as a string
```

`typeof` on an undeclared variable returns the string `"undefined"` instead of throwing.

---

## The Next.js Component Lifecycle

```
1. SERVER RENDER (Node.js)
   ├── Server Components run → generate HTML
   ├── Client Components ("use client") run → generate HTML
   │   ├── useState: initializes with initial value
   │   ├── useEffect: DOES NOT RUN (server has no effects)
   │   ├── useRef: initializes with initial value
   │   └── window/document: DO NOT EXIST
   └── HTML sent to browser

2. CLIENT HYDRATION (Browser)
   ├── Browser shows server HTML immediately
   ├── JavaScript downloads
   ├── Client Components hydrate:
   │   ├── useState: re-initializes (must match server!)
   │   ├── useEffect: NOW RUNS (browser environment ready)
   │   ├── useRef: re-initializes
   │   └── window/document: NOW AVAILABLE
   └── Page is now interactive
```

---

## Common SSR Patterns

### Pattern 1: Guard with typeof window
```ts
function loadRecentSearches(): string[] {
  if (typeof window === "undefined") return []
  const stored = localStorage.getItem("searches")
  return stored ? JSON.parse(stored) : []
}
```

### Pattern 2: useEffect for client-only code
```tsx
function ThemeProvider({ children }) {
  const [theme, setTheme] = useState("light")
  const [isMounted, setIsMounted] = useState(false)

  useEffect(() => {
    // This only runs on the client, after hydration
    const saved = localStorage.getItem("theme")
    if (saved) setTheme(saved)
    setIsMounted(true)
  }, [])

  // Prevent flash of wrong theme during hydration
  if (!isMounted) return null  // or a skeleton/placeholder

  return <ThemeContext.Provider value={...}>{children}</ThemeContext.Provider>
}
```

**Why `isMounted`?** Without it, the server renders with `"light"` theme, but the user's preference might be `"dark"`. You'd see a flash of light theme before it switches. The `isMounted` check prevents rendering until the client has read the saved preference.

### Pattern 3: Dynamic import with `ssr: false`
```tsx
// For components that absolutely cannot run on the server
import dynamic from "next/dynamic"

const AudioVisualizer = dynamic(() => import("./AudioVisualizer"), {
  ssr: false,  // completely skip server rendering for this component
})
```

---

## Hydration Mismatches

If the server renders different HTML than the client expects, React warns about a **hydration mismatch:**

```tsx
// Bad — different output on server vs client
function Greeting() {
  return <p>The time is {new Date().toLocaleTimeString()}</p>
  // Server: "10:00:00 AM"
  // Client: "10:00:01 AM"  ← mismatch!
}

// Good — defer client-only values to useEffect
function Greeting() {
  const [time, setTime] = useState("")
  useEffect(() => {
    setTime(new Date().toLocaleTimeString())
  }, [])
  return <p>The time is {time}</p>
  // Server: ""
  // Client initial: "" (matches!)
  // Client after effect: "10:00:01 AM"
}
```

---

## Server Components vs Client Components

Next.js App Router adds **Server Components** (the default):

| | Server Components | Client Components |
|---|---|---|
| Directive | None (default) | `"use client"` |
| Runs on | Server only | Server (SSR) + Client (hydration) |
| Can use hooks | No | Yes |
| Can use browser APIs | No | Yes (after hydration) |
| Can access DB/filesystem | Yes | No |
| Sent to client | Only the HTML output | JS code + HTML |

---

## Related Concepts
- **useState/useEffect (Module 3):** Effects only run on client; state initializes on both
- **Hydration mismatch:** Server and client must produce identical initial HTML
- **Progressive enhancement:** SSR provides content even before JS loads
- **Time to First Byte (TTFB):** SSR improves perceived performance

---

## Summary

| Fact | Implication |
|------|------------|
| `"use client"` components still SSR | `window` checks are still needed |
| `typeof window === "undefined"` | Safe way to detect server environment |
| `useEffect` runs only on client | Put browser API calls in effects |
| Server and client must match | Don't render dynamic values during SSR |
| `isMounted` pattern | Prevents hydration mismatch for client-dependent state |
