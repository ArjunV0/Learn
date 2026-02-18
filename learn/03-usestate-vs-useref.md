# Module 3: React State — useState vs useRef

## The Core Difference

Both `useState` and `useRef` persist values across re-renders. The critical difference:

| | `useState` | `useRef` |
|---|---|---|
| **Triggers re-render on change** | YES | NO |
| **Returns** | `[value, setValue]` | `{ current: value }` |
| **When to use** | Data the UI displays | Values the UI doesn't need to know about |

---

## How React Rendering Works (Simplified)

Understanding this is essential to choosing between the two.

```
1. Something changes (state update, prop change)
2. React calls your component function again
3. The function returns new JSX
4. React compares old JSX vs new JSX (diffing)
5. React updates only the DOM elements that changed
```

**Key insight:** Every `setState` call triggers step 1. Every re-render means your entire component function runs again.

---

## useState: For UI Data

Use `useState` when **changing the value should update what the user sees.**

```tsx
function Counter() {
  const [count, setCount] = useState(0)

  return (
    <div>
      <p>Count: {count}</p>                    {/* displayed in UI */}
      <button onClick={() => setCount(c => c + 1)}>+</button>
    </div>
  )
}
```

When `setCount` is called:
1. `count` updates to new value
2. Component re-renders
3. `<p>Count: 1</p>` shows the new value

**If this were `useRef`:**
```tsx
const countRef = useRef(0)
countRef.current += 1  // value changes but... nothing happens on screen!
```

The ref updates silently. No re-render. The UI still shows the old value.

---

## useRef: For Silent References

Use `useRef` when you need to **hold onto something without triggering a re-render.**

### Case 1: DOM Element Access
```tsx
function AutoFocusInput() {
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    inputRef.current?.focus()  // imperative: "focus this element!"
  }, [])

  return <input ref={inputRef} />
}
```

React gives you a reference to the actual DOM element. You call `.focus()` directly — this is **imperative** (giving commands), not **declarative** (describing what should render).

### Case 2: Audio/Video Elements
```tsx
function Player() {
  const audioRef = useRef<HTMLAudioElement>(null)

  const play = () => audioRef.current?.play()    // imperative
  const pause = () => audioRef.current?.pause()  // imperative

  return <audio ref={audioRef} src="/song.mp3" />
}
```

**Why not useState?**
- You never display the audio element object in JSX
- Calling `.play()` or `.pause()` doesn't need a re-render
- Storing it in state would cause unnecessary re-renders every time the audio ref is assigned

### Case 3: Tracking Previous Values
```tsx
function usePrevious<T>(value: T): T | undefined {
  const ref = useRef<T>()

  useEffect(() => {
    ref.current = value  // updates after render, no re-render triggered
  })

  return ref.current
}
```

### Case 4: Interval/Timeout IDs
```tsx
function Stopwatch() {
  const intervalRef = useRef<NodeJS.Timeout>()

  const start = () => {
    intervalRef.current = setInterval(tick, 1000)
  }

  const stop = () => {
    clearInterval(intervalRef.current)  // need the ID to stop it
  }
}
```

The interval ID is a behind-the-scenes value. Displaying it would be meaningless.

---

## The Mental Model

Ask yourself: **"Does the UI need to change when this value changes?"**

- **YES** → `useState` (theme, song title, search query, loading state, error messages)
- **NO** → `useRef` (DOM elements, audio/video, timers, previous values, abort controllers)

---

## Common Mistakes

### Mistake 1: Using state for non-UI values
```tsx
// Bad — causes unnecessary re-renders
const [intervalId, setIntervalId] = useState<NodeJS.Timeout>()

// Good — silent storage
const intervalRef = useRef<NodeJS.Timeout>()
```

### Mistake 2: Using ref for UI values
```tsx
// Bad — UI won't update
const nameRef = useRef("Alice")
return <p>{nameRef.current}</p>  // shows "Alice" forever even if you change it

// Good — UI updates on change
const [name, setName] = useState("Alice")
return <p>{name}</p>  // updates when setName is called
```

### Mistake 3: Reading ref during render
```tsx
// Risky — ref.current might not be set yet during the first render
function Bad() {
  const ref = useRef<HTMLDivElement>(null)
  const width = ref.current?.offsetWidth  // undefined on first render!

  return <div ref={ref}>Width: {width}</div>
}

// Good — read refs in effects or event handlers
function Good() {
  const ref = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(0)

  useEffect(() => {
    if (ref.current) setWidth(ref.current.offsetWidth)
  }, [])

  return <div ref={ref}>Width: {width}</div>
}
```

---

## Deep Dive: What `useRef` Actually Returns

```ts
const myRef = useRef(initialValue)
// Returns: { current: initialValue }
```

It's literally just an object with a `.current` property. React guarantees:
1. The same object is returned every render (referential stability)
2. Mutating `.current` does NOT trigger a re-render
3. The object persists for the full lifetime of the component

You could simulate it with a module-level variable, but `useRef` scopes it to the component instance (important when multiple instances exist).

---

## useRef + useEffect: The Imperative Escape Hatch

React is declarative ("describe what should render"), but sometimes you need to interact with imperative browser APIs. The pattern:

```tsx
function VideoPlayer({ src, isPlaying }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null)

  // Bridge between declarative (isPlaying prop) and imperative (.play()/.pause())
  useEffect(() => {
    if (isPlaying) {
      videoRef.current?.play()
    } else {
      videoRef.current?.pause()
    }
  }, [isPlaying])

  return <video ref={videoRef} src={src} />
}
```

This is exactly the pattern your `PlayerContext.tsx` uses for audio playback.

---

## Related Concepts
- **Re-renders:** How React updates the UI (understanding this is key to choosing state vs ref)
- **Imperative vs Declarative:** Refs enable imperative operations in a declarative framework
- **useCallback / useMemo:** Other hooks that help control re-renders (see Module 4 for context usage)
- **Controlled vs Uncontrolled components:** Refs power uncontrolled form inputs

---

## Summary

```
Need to show it in the UI? ──── YES → useState
                             └── NO → useRef

Need to call methods on it? ─── YES → useRef (DOM, audio, video, canvas)
                             └── NO → probably useState

Will re-render cause problems? ── YES → useRef
                                └── NO → useState is fine
```
