# PlayNext - Learning Modules

A structured learning guide covering all the concepts raised in the PR review comments.

## Modules

| # | Module | File | Key Concepts |
|---|--------|------|-------------|
| 1 | [Constants & Magic Values](./01-constants-and-magic-values.md) | `01` | Magic strings, `as const`, enums vs constants, single source of truth |
| 2 | [Utility Functions & DRY](./02-utility-functions-and-dry.md) | `02` | DRY principle, when to extract, naming, pure functions |
| 3 | [React State: useState vs useRef](./03-usestate-vs-useref.md) | `03` | Re-renders, refs, imperative vs declarative, DOM access |
| 4 | [React Context Pattern (null + guard)](./04-react-context-pattern.md) | `04` | createContext, custom hooks, fail-fast, provider pattern |
| 5 | [SSR, Hydration & "use client"](./05-ssr-hydration-use-client.md) | `05` | Server rendering, hydration, window checks, Next.js lifecycle |
| 6 | [Error Handling Strategies](./06-error-handling.md) | `06` | Silent failures, error boundaries, result objects, throw vs return |
| 7 | [Readable Code & Conditionals](./07-readable-code-conditionals.md) | `07` | Named booleans, JSX readability, early returns, compound conditions |
| 8 | [Separation of Concerns & Service Layer](./08-separation-of-concerns.md) | `08` | Route vs service, testability, single responsibility, layered architecture |
| 9 | [Array Methods & Algorithms](./09-array-methods-and-algorithms.md) | `09` | findIndex, modulo wrapping, map/filter/reduce, functional patterns |

## How to Use

1. Read each module in order (they build on each other)
2. Each module has: **Concept**, **Why It Matters**, **Bad vs Good Code**, **Related Concepts**
3. After learning, check `CHECKLIST.md` for the actual code changes to make

## Related Files
- [CHECKLIST.md](./CHECKLIST.md) - All PR changes mapped to branches
