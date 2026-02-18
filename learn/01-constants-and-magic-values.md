# Module 1: Constants & Magic Values

## What is a Magic Value?

A "magic value" is any hardcoded literal (string, number, URL fragment) used directly in your code without a name explaining what it is.

```ts
// These are all magic values:
setTheme("light")                              // magic string
coverUrl.replace("100x100", "300x300")         // magic strings
if (retryCount > 3)                            // magic number
fetch("https://itunes.apple.com/search")       // magic URL
```

The word "magic" is ironic — there's nothing magical about them. They're called magic because **a reader has to guess what they mean and why they have that specific value.**

---

## Why Magic Values Are Bad

### 1. Typos become silent bugs
```ts
// No error — TypeScript sees two different strings, both valid
if (theme === "ligth") { ... }  // typo, will never match
```

### 2. Changes require hunting
If `"light"` appears in 8 files and you rename it to `"day"`, you must find and update all 8. Miss one and you have a bug.

### 3. No discoverability
A new developer sees `"300x300"` and has no idea why. A constant named `ARTWORK_SIZE_LARGE` is self-documenting.

---

## The Fix: Named Constants

### Basic Constants
```ts
// constants.ts
export const LIGHT = "light" as const
export const DARK = "dark" as const
export const DEFAULT_THEME = LIGHT
```

Usage:
```ts
import { DEFAULT_THEME, DARK, LIGHT } from "@/lib/constants"

const [theme, setTheme] = useState<Theme>(DEFAULT_THEME)

// Typo now gives a compile error:
if (theme === LIGTH) { ... }  // TS Error: Cannot find name 'LIGTH'
```

### What Does `as const` Do?

Without `as const`:
```ts
const LIGHT = "light"  // TypeScript infers type: string
```

With `as const`:
```ts
const LIGHT = "light" as const  // TypeScript infers type: "light" (literal type)
```

The literal type is narrower and more precise. It means TypeScript knows the exact value, not just that it's some string.

### Deriving Types from Constants
```ts
export const LIGHT = "light" as const
export const DARK = "dark" as const

// The type is automatically: "light" | "dark"
export type Theme = typeof LIGHT | typeof DARK
```

Now the type and the runtime values are always in sync. If you add a third theme:
```ts
export const SYSTEM = "system" as const
export type Theme = typeof LIGHT | typeof DARK | typeof SYSTEM
```

One place to add it, the type updates automatically.

---

## Constants for URLs and API Values

```ts
// Bad
const response = await fetch("https://itunes.apple.com/search")
coverUrl.replace("100x100", "300x300")

// Good
const ITUNES_SEARCH_URL = "https://itunes.apple.com/search"
const ARTWORK_SIZE_SMALL = "100x100"
const ARTWORK_SIZE_LARGE = "300x300"

const response = await fetch(ITUNES_SEARCH_URL)
coverUrl.replace(ARTWORK_SIZE_SMALL, ARTWORK_SIZE_LARGE)
```

---

## Constants vs Enums

TypeScript offers `enum` but modern TS prefers `const` objects or plain constants:

```ts
// Enum approach (works but has quirks)
enum Theme {
  Light = "light",
  Dark = "dark",
}

// Const object approach (preferred in modern TS)
export const THEMES = {
  LIGHT: "light",
  DARK: "dark",
} as const

export type Theme = (typeof THEMES)[keyof typeof THEMES]
// Result: "light" | "dark"
```

**Why prefer const objects over enums?**
- Enums generate extra JavaScript code at runtime
- Enums can have surprising behavior with reverse mappings
- Const objects are plain JavaScript — what you see is what you get
- Const objects work better with tree-shaking (dead code elimination)

---

## Where to Put Constants

```
lib/
  constants.ts          ← App-wide constants (themes, API URLs)
features/
  player/
    player.constants.ts ← Feature-specific constants
  search/
    search.constants.ts
```

**Rule of thumb:**
- Used in 1 file → local constant at the top of that file
- Used across a feature → `feature.constants.ts`
- Used across the app → `lib/constants.ts`

---

## Related Concepts
- **Single Source of Truth (SSOT):** Every piece of data should have exactly one authoritative definition
- **DRY Principle:** Don't Repeat Yourself (see Module 2)
- **Type Safety:** Constants + TypeScript catch errors at compile time instead of runtime

---

## Summary

| Bad | Good |
|-----|------|
| `"light"` scattered everywhere | `DEFAULT_THEME` defined once |
| `"100x100"` with no explanation | `ARTWORK_SIZE_SMALL` |
| `"https://itunes..."` hardcoded | `ITUNES_SEARCH_URL` |
| `type Theme = "light" \| "dark"` | `type Theme = typeof LIGHT \| typeof DARK` |
