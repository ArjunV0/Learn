#!/usr/bin/env python3
"""
Image generator for backend learning notes.
Reads image_prompts.json and generates images using Seedream via OpenRouter.

Usage:
    python generate_images.py
    python generate_images.py --prompts image_prompts.json
    python generate_images.py --id 3          # generate only image with id=3
    python generate_images.py --dry-run       # print prompts, don't generate
"""

import json
import os
import sys
import time
import argparse
import base64
import requests
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent          # project root (LEARN/)
SCRIPTS_DIR = Path(__file__).parent         # scripts/

load_dotenv(ROOT / ".env")

# ── Configuration ────────────────────────────────────────────────────────────

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
MODEL = "bytedance-seed/seedream-4.5"          # Seedream on OpenRouter
BASE_URL = "https://openrouter.ai/api/v1"

IMAGE_SIZE = "1024x1024"               # width x height
IMAGE_FORMAT = "png"
RETRY_ATTEMPTS = 3
RETRY_DELAY = 5                        # seconds between retries

DEFAULT_PROMPTS_FILE = str(SCRIPTS_DIR / "image_prompts.json")

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_prompts(filepath: str) -> list[dict]:
    with open(filepath, "r") as f:
        return json.load(f)


def ensure_output_dir(output_path: str):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)


def save_image_from_url(url: str, output_path: str):
    """Download image from URL and save to disk."""
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    with open(output_path, "wb") as f:
        f.write(response.content)


def save_image_from_b64(b64_data: str, output_path: str):
    """Decode base64 image and save to disk."""
    image_bytes = base64.b64decode(b64_data)
    with open(output_path, "wb") as f:
        f.write(image_bytes)


def generate_image(prompt: str, output_path: str) -> bool:
    """
    Call OpenRouter image generation API.
    Returns True on success, False on failure.
    """
    if not OPENROUTER_API_KEY:
        print("  ERROR: OPENROUTER_API_KEY environment variable not set.")
        print("  Export it: export OPENROUTER_API_KEY=your_key_here")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/local/learn",   # optional but good practice
        "X-Title": "Backend Learning Notes",
    }

    # OpenRouter image models use the chat completions endpoint
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
                timeout=120,
            )

            if response.status_code != 200:
                print(f"  Attempt {attempt}/{RETRY_ATTEMPTS} failed — HTTP {response.status_code}")
                print(f"  Response: {response.text[:300]}")
                if attempt < RETRY_ATTEMPTS:
                    time.sleep(RETRY_DELAY)
                continue

            result = response.json()
            message = result["choices"][0]["message"]

            ensure_output_dir(output_path)

            # Seedream returns image in message.images list
            images = message.get("images") or []
            if images:
                block = images[0]
                url = block["image_url"]["url"]
                if url.startswith("data:"):
                    b64_data = url.split(",", 1)[1]
                    save_image_from_b64(b64_data, output_path)
                else:
                    save_image_from_url(url, output_path)
                return True

            # Fallback: check content field (list of blocks or plain string)
            content = message.get("content")
            if isinstance(content, list):
                for block in content:
                    if block.get("type") == "image_url":
                        url = block["image_url"]["url"]
                        if url.startswith("data:"):
                            save_image_from_b64(url.split(",", 1)[1], output_path)
                        else:
                            save_image_from_url(url, output_path)
                        return True
            elif isinstance(content, str) and content.startswith(("http", "data:")):
                if content.startswith("data:"):
                    save_image_from_b64(content.split(",", 1)[1], output_path)
                else:
                    save_image_from_url(content.strip(), output_path)
                return True

            print(f"  ERROR: No image found in response.")
            print(f"  Message keys: {list(message.keys())}")
            return False

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
            print(f"  Full response: {response.text[:500]}")
            return False

    return False


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    global MODEL
    parser = argparse.ArgumentParser(description="Generate diagram images for learning notes.")
    parser.add_argument(
        "--prompts",
        default=DEFAULT_PROMPTS_FILE,
        help="Path to the JSON prompts file (default: image_prompts.json)",
    )
    parser.add_argument(
        "--id",
        type=int,
        default=None,
        help="Generate only the entry with this id (default: generate all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print prompts and output paths without generating images",
    )
    parser.add_argument(
        "--model",
        default=None,
        help=f"OpenRouter model to use (default: {MODEL})",
    )
    args = parser.parse_args()

    if args.model:
        MODEL = args.model

    # Load prompts
    if not os.path.exists(args.prompts):
        print(f"ERROR: Prompts file not found: {args.prompts}")
        sys.exit(1)

    prompts = load_prompts(args.prompts)

    # Filter by id if specified
    if args.id is not None:
        prompts = [p for p in prompts if p.get("id") == args.id]
        if not prompts:
            print(f"ERROR: No entry found with id={args.id}")
            sys.exit(1)

    total = len(prompts)
    print(f"Model    : {MODEL}")
    print(f"Total    : {total} image(s) to generate")
    print(f"Dry run  : {args.dry_run}")
    print("─" * 60)

    results = {"success": [], "failed": [], "skipped": []}

    for i, entry in enumerate(prompts, 1):
        image_id    = entry.get("id", i)
        filename    = entry["filename"]
        output_path = entry["output_path"]
        prompt      = entry["prompt"]

        print(f"\n[{i}/{total}] id={image_id} → {output_path}")

        if args.dry_run:
            print(f"  PROMPT: {prompt[:120]}...")
            results["skipped"].append(filename)
            continue

        # Skip if file already exists
        if os.path.exists(output_path):
            print(f"  SKIPPED — file already exists. Delete it to regenerate.")
            results["skipped"].append(filename)
            continue

        print(f"  Generating with {MODEL}...")
        success = generate_image(prompt, output_path)

        if success:
            size_kb = os.path.getsize(output_path) / 1024
            print(f"  SAVED → {output_path} ({size_kb:.1f} KB)")
            results["success"].append(filename)
        else:
            print(f"  FAILED → {filename}")
            results["failed"].append(filename)

        # Small delay between requests to avoid rate limiting
        if i < total:
            time.sleep(1)

    # Summary
    print("\n" + "─" * 60)
    print("SUMMARY")
    print(f"  Generated : {len(results['success'])}")
    print(f"  Failed    : {len(results['failed'])}")
    print(f"  Skipped   : {len(results['skipped'])}")

    if results["failed"]:
        print("\nFailed files:")
        for f in results["failed"]:
            print(f"  - {f}")
        sys.exit(1)


if __name__ == "__main__":
    main()
