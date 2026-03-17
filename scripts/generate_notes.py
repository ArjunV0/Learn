#!/usr/bin/env python3
"""
Markdown note generator for learning syllabus.
Reads syllabus.json + prompt_template.txt, generates .md files via OpenRouter,
and keeps image_prompts.json in sync automatically.

Usage:
    python3 generate_notes.py                          # generate all phases and topics
    python3 generate_notes.py --phase 1               # generate only phase 1
    python3 generate_notes.py --phase 1 --topic-id 3  # generate one specific topic
    python3 generate_notes.py --dry-run               # preview without generating
    python3 generate_notes.py --force                 # overwrite existing files
"""

import json
import os
import sys
import time
import argparse
import requests
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent          # project root (LEARN/)
SCRIPTS_DIR = Path(__file__).parent         # scripts/

load_dotenv(ROOT / ".env")

# ── Configuration ─────────────────────────────────────────────────────────────

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
MODEL              = os.environ.get("NOTES_MODEL", "openrouter/hunter-alpha")
BASE_URL           = "https://openrouter.ai/api/v1"

RETRY_ATTEMPTS     = 3
RETRY_DELAY        = 5    # seconds between retries
REQUEST_DELAY      = 2    # seconds between successful requests

SYLLABUS_FILE      = str(ROOT / "syllabus.json")
TEMPLATE_FILE      = str(SCRIPTS_DIR / "prompt_template.txt")
IMAGE_PROMPTS_FILE = str(SCRIPTS_DIR / "image_prompts.json")

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_json(filepath: str) -> dict:
    with open(filepath, "r") as f:
        return json.load(f)


def load_template(filepath: str) -> str:
    with open(filepath, "r") as f:
        return f.read()


def build_prompt(template: str, topic: dict, phase_name: str) -> str:
    subtopics_formatted = "\n".join(f"  - {s}" for s in topic["subtopics"])
    return (
        template
        .replace("{title}", topic["title"])
        .replace("{phase_name}", phase_name)
        .replace("{subtopics}", subtopics_formatted)
        .replace("{diagram_filename}", topic.get("diagram_filename", topic["filename"].replace(".md", ".png")))
    )


def ensure_dir(path: str):
    Path(path).mkdir(parents=True, exist_ok=True)


# ── Image Prompt Sync ─────────────────────────────────────────────────────────

def load_image_prompts(filepath: str) -> list:
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r") as f:
        return json.load(f)


def save_image_prompts(filepath: str, entries: list):
    with open(filepath, "w") as f:
        json.dump(entries, f, indent=2)


def build_image_prompt(topic: dict, phase: dict) -> str:
    diagram_filename = topic.get("diagram_filename", topic["filename"].replace(".md", ".png"))
    components = "\n".join(f"- {s}" for s in topic["subtopics"])
    return (
        f"Create a clean, minimal, ByteByteGo-style system diagram for: {topic['title']}\n\n"
        f"Requirements:\n"
        f"- White background\n"
        f"- Flat design (no 3D, no gradients)\n"
        f"- Clear labeled components (boxes)\n"
        f"- Arrows showing flow direction\n"
        f"- Use simple colors (blue, grey, black)\n"
        f"- Consistent spacing and alignment\n"
        f"- Professional engineering diagram style\n\n"
        f"Diagram should clearly show:\n"
        f"A visual representation of {topic['title']} covering the key concepts listed below.\n\n"
        f"Components to include:\n"
        f"{components}\n\n"
        f"Flow requirements:\n"
        f"- Show step-by-step data movement\n"
        f"- Label arrows with actions (e.g., 'Request', 'Cache Hit', 'DB Query', 'Response')\n"
        f"- Show cause-and-effect relationships between components\n\n"
        f"Style constraints:\n"
        f"- No clutter\n"
        f"- No unnecessary decoration\n"
        f"- Easy to understand at a glance\n"
        f"- Similar to system design interview diagrams\n\n"
        f"Output:\n"
        f"- High clarity architecture diagram\n"
        f"- Suitable for learning documentation"
    )


def upsert_image_prompt(topic: dict, phase: dict, image_prompts_file: str):
    """Add or update the image prompt entry for this topic."""
    diagram_filename = topic.get("diagram_filename", topic["filename"].replace(".md", ".png"))
    images_folder    = os.path.join(phase["folder"], "images")
    output_path      = os.path.join(images_folder, diagram_filename)

    entries = load_image_prompts(image_prompts_file)

    # Find existing entry by filename to update, or assign new id
    existing_idx = next((i for i, e in enumerate(entries) if e.get("filename") == diagram_filename), None)
    next_id      = (max((e.get("id", 0) for e in entries), default=0) + 1) if existing_idx is None else entries[existing_idx]["id"]

    entry = {
        "id":          next_id,
        "phase":       phase["phase"],
        "filename":    diagram_filename,
        "output_path": output_path,
        "prompt":      build_image_prompt(topic, phase),
    }

    if existing_idx is not None:
        entries[existing_idx] = entry
        action = "updated"
    else:
        entries.append(entry)
        action = "added"

    # Keep sorted by phase then id
    entries.sort(key=lambda e: (e.get("phase", 0), e.get("id", 0)))
    save_image_prompts(image_prompts_file, entries)
    return action


def call_openrouter(prompt: str):
    """
    Call OpenRouter chat completions. Returns the markdown string or None on failure.
    """
    if not OPENROUTER_API_KEY:
        print("  ERROR: OPENROUTER_API_KEY not set. Add it to your .env file.")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/local/learn",
        "X-Title": "Backend Learning Notes",
    }

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
    }

    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            response = requests.post(
                f"{BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
                timeout=180,
            )

            if response.status_code != 200:
                print(f"  Attempt {attempt}/{RETRY_ATTEMPTS} failed — HTTP {response.status_code}")
                print(f"  {response.text[:200]}")
                if attempt < RETRY_ATTEMPTS:
                    time.sleep(RETRY_DELAY)
                continue

            result = response.json()
            content = result["choices"][0]["message"]["content"]

            if not content or not content.strip():
                print(f"  Attempt {attempt}/{RETRY_ATTEMPTS} returned empty content.")
                if attempt < RETRY_ATTEMPTS:
                    time.sleep(RETRY_DELAY)
                continue

            return content.strip()

        except requests.exceptions.Timeout:
            print(f"  Attempt {attempt}/{RETRY_ATTEMPTS} timed out.")
            if attempt < RETRY_ATTEMPTS:
                time.sleep(RETRY_DELAY)
        except requests.exceptions.RequestException as e:
            print(f"  Attempt {attempt}/{RETRY_ATTEMPTS} request error: {e}")
            if attempt < RETRY_ATTEMPTS:
                time.sleep(RETRY_DELAY)
        except (KeyError, IndexError) as e:
            print(f"  ERROR parsing response: {e}")
            print(f"  Response: {response.text[:400]}")
            return None

    return None


def generate_topic(topic: dict, phase: dict, template: str, output_path: str,
                   image_prompts_file: str, force: bool, dry_run: bool) -> str:
    """
    Returns: 'generated' | 'skipped' | 'failed' | 'dry_run'
    """
    if dry_run:
        prompt = build_prompt(template, topic, phase["name"])
        print(f"  PROMPT PREVIEW ({len(prompt)} chars):")
        print(f"  {prompt[:200].replace(chr(10), ' ')}...")
        img_action = upsert_image_prompt(topic, phase, image_prompts_file)
        print(f"  IMAGE PROMPT → {img_action} in {image_prompts_file}")
        return "dry_run"

    if not force and os.path.exists(output_path):
        print(f"  SKIPPED — already exists. Use --force to overwrite.")
        # Still sync image prompt in case it's missing
        img_action = upsert_image_prompt(topic, phase, image_prompts_file)
        print(f"  IMAGE PROMPT → {img_action} in {image_prompts_file}")
        return "skipped"

    prompt = build_prompt(template, topic, phase["name"])
    print(f"  Calling {MODEL}...")

    markdown = call_openrouter(prompt)
    if not markdown:
        print(f"  FAILED — no content returned after {RETRY_ATTEMPTS} attempts.")
        return "failed"

    ensure_dir(str(Path(output_path).parent))
    with open(output_path, "w") as f:
        f.write(markdown)

    size_kb = os.path.getsize(output_path) / 1024
    print(f"  SAVED → {output_path} ({size_kb:.1f} KB, {len(markdown.splitlines())} lines)")

    # Sync image prompt entry
    img_action = upsert_image_prompt(topic, phase, image_prompts_file)
    print(f"  IMAGE PROMPT → {img_action} in {image_prompts_file}")

    return "generated"


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    global MODEL

    parser = argparse.ArgumentParser(description="Generate markdown learning notes from syllabus.json")
    parser.add_argument("--syllabus",  default=SYLLABUS_FILE,  help=f"Syllabus JSON file (default: {SYLLABUS_FILE})")
    parser.add_argument("--template",  default=TEMPLATE_FILE,  help=f"Prompt template file (default: {TEMPLATE_FILE})")
    parser.add_argument("--phase",     type=int, default=None,  help="Only generate topics in this phase number")
    parser.add_argument("--topic-id",  type=int, default=None,  help="Only generate the topic with this id (requires --phase)")
    parser.add_argument("--model",     default=None,            help=f"Override OpenRouter model (default: {MODEL})")
    parser.add_argument("--image-prompts", default=IMAGE_PROMPTS_FILE, help=f"Image prompts JSON to sync (default: {IMAGE_PROMPTS_FILE})")
    parser.add_argument("--force",         action="store_true",        help="Overwrite existing .md files")
    parser.add_argument("--dry-run",       action="store_true",        help="Preview prompts without calling the API")
    args = parser.parse_args()

    if args.model:
        MODEL = args.model

    if args.topic_id and args.phase is None:
        print("ERROR: --topic-id requires --phase to also be specified.")
        sys.exit(1)

    # Load files
    for f in [args.syllabus, args.template]:
        if not os.path.exists(f):
            print(f"ERROR: File not found: {f}")
            sys.exit(1)

    syllabus = load_json(args.syllabus)
    template = load_template(args.template)

    # Filter phases
    phases = syllabus["phases"]
    if args.phase is not None:
        phases = [p for p in phases if p["phase"] == args.phase]
        if not phases:
            print(f"ERROR: Phase {args.phase} not found in syllabus.")
            sys.exit(1)

    # Count total topics
    total = sum(
        len([t for t in p["topics"] if args.topic_id is None or t["id"] == args.topic_id])
        for p in phases
    )

    print(f"Model         : {MODEL}")
    print(f"Topics        : {total}")
    print(f"Image prompts : {args.image_prompts}")
    print(f"Force         : {args.force}")
    print(f"Dry run       : {args.dry_run}")
    print("─" * 60)

    results = {"generated": 0, "skipped": 0, "failed": [], "dry_run": 0}
    counter = 0

    for phase in phases:
        topics = phase["topics"]
        if args.topic_id is not None:
            topics = [t for t in topics if t["id"] == args.topic_id]
            if not topics:
                print(f"ERROR: Topic id={args.topic_id} not found in phase {phase['phase']}.")
                sys.exit(1)

        print(f"\n── Phase {phase['phase']}: {phase['name']} ──")
        print(f"   Output folder: {phase['folder']}/\n")

        for topic in topics:
            counter += 1
            output_path = os.path.join(phase["folder"], topic["filename"])
            print(f"[{counter}/{total}] {topic['filename']}")

            status = generate_topic(
                topic=topic,
                phase=phase,
                template=template,
                output_path=output_path,
                image_prompts_file=args.image_prompts,
                force=args.force,
                dry_run=args.dry_run,
            )

            if status == "generated":
                results["generated"] += 1
            elif status == "skipped":
                results["skipped"] += 1
            elif status == "failed":
                results["failed"].append(f"Phase {phase['phase']} / {topic['filename']}")
            elif status == "dry_run":
                results["dry_run"] += 1

            # Delay between requests
            if status == "generated" and counter < total:
                time.sleep(REQUEST_DELAY)

    # Summary
    print("\n" + "─" * 60)
    print("SUMMARY")
    print(f"  Generated : {results['generated']}")
    print(f"  Skipped   : {results['skipped']}")
    print(f"  Dry run   : {results['dry_run']}")
    print(f"  Failed    : {len(results['failed'])}")

    if results["failed"]:
        print("\nFailed topics:")
        for f in results["failed"]:
            print(f"  - {f}")
        sys.exit(1)


if __name__ == "__main__":
    main()
