# Backend Engineering Self-Study

A structured, self-paced backend engineering curriculum.
Each topic is a deep-dive chapter: mental models, system thinking, diagrams, and practical exercises.

---

## Project Structure

```
LEARN/
├── README.md                        # This file
├── .env                             # API keys (never commit)
├── syllabus.json                    # Master input — all phases and topics
│
├── scripts/
│   ├── generate_notes.py            # Generates .md chapters from syllabus
│   ├── generate_images.py           # Generates diagrams from image_prompts.json
│   ├── prompt_template.txt          # 11-section chapter template
│   └── image_prompts.json           # Auto-managed — do not edit by hand
│
└── Roadmap/
    └── phase-1/                     # Generated content per phase
        ├── 01-postgresql-fundamentals.md
        ├── 02-sql-deep-dive.md
        ├── 03-indexing.md
        ├── 04-transactions-and-data-integrity.md
        ├── 05-database-performance.md
        ├── 06-redis-caching.md
        ├── 07-advanced-redis.md
        ├── 08-background-jobs-and-queues.md
        ├── 09-backend-integration.md
        └── images/
            └── *.png                # Generated diagrams
```

---

## Setup

**1. Install dependencies**

```bash
pip install requests python-dotenv
```

**2. Configure API keys**

Create a `.env` file in the project root:

```env
OPENROUTER_API_KEY=sk-or-your-key-here

# Optional: override the default notes model
# NOTES_MODEL=openrouter/hunter-alpha
```

---

## Generating Content

### Generate Chapter Notes

Reads `syllabus.json` and `scripts/prompt_template.txt`, writes `.md` files to `Roadmap/phase-N/`.
Also automatically updates `scripts/image_prompts.json` for every topic processed.

```bash
# Generate all phases and topics
python3 scripts/generate_notes.py

# Generate only a specific phase
python3 scripts/generate_notes.py --phase 1

# Generate one topic
python3 scripts/generate_notes.py --phase 1 --topic-id 3

# Preview prompts without calling the API
python3 scripts/generate_notes.py --dry-run

# Regenerate existing files
python3 scripts/generate_notes.py --force
```

### Generate Diagrams

Reads `scripts/image_prompts.json` (auto-managed), writes `.png` files into each phase's `images/` folder.

```bash
# Generate all diagrams
python3 scripts/generate_images.py

# Generate one diagram by id
python3 scripts/generate_images.py --id 3

# Preview prompts without calling the API
python3 scripts/generate_images.py --dry-run

# Use a different image model
python3 scripts/generate_images.py --model bytedance-seed/seedream-4.5
```

---

## Typical Workflow

```
1. Add/edit a phase or topic in syllabus.json
        ↓
2. python3 scripts/generate_notes.py --phase N
   → writes Roadmap/phase-N/XX-topic.md
   → updates scripts/image_prompts.json
        ↓
3. python3 scripts/generate_images.py
   → writes Roadmap/phase-N/images/topic.png
        ↓
4. Open the .md file and study
```

---

## Adding a New Phase

1. Open `syllabus.json`
2. Add a new object to the `"phases"` array:

```json
{
  "phase": 2,
  "name": "System Architecture",
  "folder": "Roadmap/phase-2",
  "topics": [
    {
      "id": 1,
      "title": "Your Topic Title",
      "filename": "01-your-topic.md",
      "diagram_filename": "your-topic.png",
      "subtopics": [
        "Subtopic one",
        "Subtopic two"
      ]
    }
  ]
}
```

3. Run `python3 scripts/generate_notes.py --phase 2`

---

## Chapter Structure

Every generated chapter follows the same 11-section format:

| Section | Purpose |
|---------|---------|
| 1. Overview | Simple explanation of the topic |
| 2. Why This Matters | Real-world usage and motivation |
| 3. Core Concepts | Deep dive with analogies |
| 4. Simple Example | Minimal focused code/pseudo |
| 5. System Perspective | Behavior under load and failure |
| 6. Diagram | Visual reference |
| 7. Common Mistakes | What beginners get wrong |
| 8. Interview Questions | Questions that test real understanding |
| 9. Build It Yourself | Practical implementation task |
| 10. Use AI vs Think Yourself | What to delegate vs own |
| 11. Key Takeaways | Core insights to remember |

---

## Curriculum

### Phase 1 — Backend Core

| # | Topic | File |
|---|-------|------|
| 1 | PostgreSQL Fundamentals | `Roadmap/phase-1/01-postgresql-fundamentals.md` |
| 2 | SQL Deep Dive | `Roadmap/phase-1/02-sql-deep-dive.md` |
| 3 | Indexing | `Roadmap/phase-1/03-indexing.md` |
| 4 | Transactions & Data Integrity | `Roadmap/phase-1/04-transactions-and-data-integrity.md` |
| 5 | Database Performance | `Roadmap/phase-1/05-database-performance.md` |
| 6 | Redis & Caching | `Roadmap/phase-1/06-redis-caching.md` |
| 7 | Advanced Redis | `Roadmap/phase-1/07-advanced-redis.md` |
| 8 | Background Jobs & Queues | `Roadmap/phase-1/08-background-jobs-and-queues.md` |
| 9 | Backend Integration | `Roadmap/phase-1/09-backend-integration.md` |

### Phase 2 — System Architecture *(coming next)*

---

## Key Principles

> "How will this behave under load, failure, and scale?"

- PostgreSQL is the source of truth. Redis is a read optimization layer.
- Design for failure at every integration point.
- Idempotency is non-negotiable in async systems.
- Measure before optimizing. Use `EXPLAIN ANALYZE`, not intuition.
- Understand the tool before you use it. Never delegate the mental model to AI.
