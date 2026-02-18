# Module 9: Array Methods & Algorithms

## Why Array Methods Matter

JavaScript arrays have built-in methods that replace manual loops. They're:
- **More readable** (name describes the operation)
- **Less error-prone** (no off-by-one bugs)
- **Composable** (chain them together)

---

## The Big Four: map, filter, find, reduce

### `map` — Transform every element
```ts
const songs = [
  { id: 1, title: "Song A", duration: 180 },
  { id: 2, title: "Song B", duration: 240 },
]

// Transform songs to just their titles
const titles = songs.map(song => song.title)
// ["Song A", "Song B"]
```

**Mental model:** "For each item, create a new item." Same length in, same length out.

### `filter` — Keep elements matching a condition
```ts
const longSongs = songs.filter(song => song.duration > 200)
// [{ id: 2, title: "Song B", duration: 240 }]
```

**Mental model:** "Keep only items that pass the test." Same or shorter length.

### `find` — Get the first matching element
```ts
const songB = songs.find(song => song.title === "Song B")
// { id: 2, title: "Song B", duration: 240 }

const songC = songs.find(song => song.title === "Song C")
// undefined (not found)
```

**Mental model:** "Find the first one that matches." Returns one item or `undefined`.

### `reduce` — Accumulate into a single value
```ts
const totalDuration = songs.reduce((total, song) => total + song.duration, 0)
// 420

// Build an object from an array
const songMap = songs.reduce((map, song) => {
  map[song.id] = song
  return map
}, {} as Record<number, Song>)
// { 1: { id: 1, ... }, 2: { id: 2, ... } }
```

**Mental model:** "Combine all items into one result." Returns a single value of any type.

---

## `findIndex` — The Hero of This PR

`findIndex` is like `find`, but returns the **index** instead of the element:

```ts
const queue = [
  { id: "a", title: "Song A" },
  { id: "b", title: "Song B" },
  { id: "c", title: "Song C" },
]

queue.findIndex(song => song.id === "b")  // 1
queue.findIndex(song => song.id === "z")  // -1 (not found)
```

### Before (manual loop — the current code probably)
```ts
function findNextIndex(queue: Song[], currentId: string): number {
  for (let i = 0; i < queue.length; i++) {
    if (queue[i].id === currentId) {
      if (i + 1 < queue.length) {
        return i + 1
      }
      return 0  // wrap around
    }
  }
  return 0  // not found
}
```

### After (findIndex + modulo)
```ts
function findNextIndex(queue: Song[], currentId: string): number {
  const currentIndex = queue.findIndex(song => song.id === currentId)
  return (currentIndex + 1) % queue.length
}
```

Same behavior, 2 lines instead of 10.

---

## Modular Arithmetic (the `%` Operator)

The modulo operator `%` returns the remainder after division:

```
10 % 3 = 1    (10 / 3 = 3 remainder 1)
7 % 2 = 1     (7 / 2 = 3 remainder 1)
6 % 3 = 0     (6 / 3 = 2 remainder 0)
```

### Why It's Perfect for Wrapping

When you have a circular list (like a song queue that loops), modulo wraps the index back to 0:

```
Queue: [A, B, C, D]   (length = 4)
Indices: 0, 1, 2, 3

Current: A (index 0) → Next: (0 + 1) % 4 = 1 → B ✓
Current: B (index 1) → Next: (1 + 1) % 4 = 2 → C ✓
Current: C (index 2) → Next: (2 + 1) % 4 = 3 → D ✓
Current: D (index 3) → Next: (3 + 1) % 4 = 0 → A ✓ (wraps!)
```

Without modulo:
```ts
const nextIndex = currentIndex + 1
if (nextIndex >= queue.length) {
  nextIndex = 0  // manual wrap
}
```

With modulo:
```ts
const nextIndex = (currentIndex + 1) % queue.length  // automatic wrap
```

### Previous Song (going backwards)
```ts
// Going backwards needs a trick because -1 % 4 = -1 in JavaScript (not 3)
const prevIndex = (currentIndex - 1 + queue.length) % queue.length

// Index 0: (0 - 1 + 4) % 4 = 3 → wraps to last song ✓
// Index 3: (3 - 1 + 4) % 4 = 2 → normal previous ✓
```

Adding `queue.length` before the modulo ensures the number is positive.

---

## Chaining Array Methods

You can chain methods for complex transformations:

```ts
const topArtists = songs
  .filter(song => song.playCount > 100)          // keep popular songs
  .map(song => song.artist)                       // extract artist names
  .filter((artist, i, arr) => arr.indexOf(artist) === i)  // remove duplicates
  .slice(0, 10)                                   // take top 10

// Or with Set for deduplication:
const topArtists = [...new Set(
  songs
    .filter(song => song.playCount > 100)
    .map(song => song.artist)
)].slice(0, 10)
```

---

## Other Useful Array Methods

### `some` — Does ANY element match?
```ts
const hasLongSong = songs.some(s => s.duration > 300)  // true/false
```

### `every` — Do ALL elements match?
```ts
const allShort = songs.every(s => s.duration < 180)  // true/false
```

### `includes` — Is this value in the array?
```ts
const themes = ["light", "dark"]
themes.includes("light")  // true
themes.includes("auto")   // false
```

### `flatMap` — Map + flatten one level
```ts
const artists = [
  { name: "Band A", songs: ["X", "Y"] },
  { name: "Band B", songs: ["Z"] },
]
artists.flatMap(a => a.songs)  // ["X", "Y", "Z"]
```

### `at` — Access by index (supports negative)
```ts
const arr = [10, 20, 30, 40]
arr.at(0)    // 10
arr.at(-1)   // 40 (last element!)
arr.at(-2)   // 30 (second to last)
```

---

## for Loop vs Array Methods — When to Use Which

| Use Array Methods When | Use for Loop When |
|----------------------|-------------------|
| Transforming data (map, filter) | You need `break` or `continue` |
| The operation is a pure transformation | You're modifying external state |
| Readability matters (almost always) | Performance is critical (rare) |
| You want to chain operations | You need access to indices in a complex way |

In practice, **array methods are the right choice 95% of the time** in modern JavaScript.

---

## Edge Cases to Watch

### Empty arrays
```ts
[].findIndex(x => true)  // -1
[].find(x => true)       // undefined
[].map(x => x * 2)       // []
[].filter(x => true)     // []
[].reduce((a, b) => a + b, 0)  // 0 (uses initial value)
[].reduce((a, b) => a + b)     // TypeError! (no initial value, no elements)
```

Always provide an initial value to `reduce` when the array might be empty.

### findIndex returning -1
```ts
const index = queue.findIndex(s => s.id === currentId)
// If not found, index = -1
// (-1 + 1) % queue.length = 0 → happens to be correct (starts from beginning)
// But this is accidental! Better to handle explicitly:

if (index === -1) return 0  // or throw, or return -1
return (index + 1) % queue.length
```

---

## Related Concepts
- **Immutability:** Array methods return new arrays, they don't modify the original
- **Functional programming:** map/filter/reduce are core FP operations
- **Module 2 (Utilities):** Array helpers like `isNonEmpty` are utility functions
- **Big O notation:** map/filter/find are O(n), includes is O(n), Set.has is O(1)

---

## Summary

| Method | Does | Returns |
|--------|------|---------|
| `map` | Transform each element | New array (same length) |
| `filter` | Keep matching elements | New array (same or shorter) |
| `find` | First matching element | Element or `undefined` |
| `findIndex` | Index of first match | Number (`-1` if not found) |
| `some` | Any match? | `boolean` |
| `every` | All match? | `boolean` |
| `reduce` | Accumulate into one value | Anything |
| `%` (modulo) | Wrap around circular lists | Remainder |
