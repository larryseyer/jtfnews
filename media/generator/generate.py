#!/usr/bin/env python3
"""
JTF News Background Image Generator
====================================
Generates photorealistic 4K background images for all four seasons
using Stability AI's API with parallel processing.

Usage:
    python generate.py --season spring --count 1920
    python generate.py --season all --count 1920
    python generate.py --season summer --count 100 --start-from 500

Requirements:
    - STABILITY_API_KEY environment variable set
    - pip install -r requirements.txt
"""

import os
import sys
import json
import time
import random
import asyncio
import aiohttp
import aiofiles
import argparse
import hashlib
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from tqdm import tqdm
from PIL import Image
import io

# Load environment variables
load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

STABILITY_API_KEY = os.getenv("STABILITY_API_KEY")
STABILITY_API_URL = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"
UPSCALE_API_URL = "https://api.stability.ai/v1/generation/esrgan-v1-x2plus/image-to-image/upscale"

# Generation settings
DEFAULT_WIDTH = 1536  # SDXL supports up to 1536 in one dimension
DEFAULT_HEIGHT = 896  # 16:9 aspect ratio (close to 1536x864)
UPSCALE_TO_4K = True  # Upscale to 3840x2160 after generation
CFG_SCALE = 7.5
STEPS = 40
SAMPLER = "K_DPM_2_ANCESTRAL"

# Parallel processing
MAX_CONCURRENT_REQUESTS = 5  # Be respectful to the API
REQUEST_DELAY = 0.5  # Seconds between starting new requests
RETRY_ATTEMPTS = 3
RETRY_DELAY = 5  # Seconds between retries

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
PROMPTS_FILE = SCRIPT_DIR / "prompts.json"
PROGRESS_FILE = SCRIPT_DIR / "progress.json"

# =============================================================================
# PROMPT GENERATION
# =============================================================================

def load_prompts():
    """Load prompts configuration from JSON file."""
    with open(PROMPTS_FILE, 'r') as f:
        return json.load(f)

def generate_prompt(prompts_data, season):
    """Generate a single random prompt for the given season."""
    season_data = prompts_data["seasons"][season]
    global_style = prompts_data["global_style"]
    quality_suffixes = prompts_data["quality_suffixes"]

    # Pick random elements
    scene = random.choice(season_data["scenes"])
    base = scene["base"]
    variation = random.choice(scene["variations"])
    time_of_day = random.choice(season_data["times_of_day"])
    weather = random.choice(season_data["weather"])
    quality = random.choice(quality_suffixes)
    color_palette = season_data["color_palette"]
    atmosphere = season_data["atmosphere"]

    # Construct the prompt
    prompt = f"{base}, {variation}, {time_of_day}, {weather}, {season} season atmosphere, {color_palette} color palette, {atmosphere} mood, {global_style}, {quality}"

    return prompt

def get_negative_prompt(prompts_data):
    """Get the negative prompt."""
    return prompts_data["negative_prompt"]

def generate_all_prompts(prompts_data, season, count):
    """Generate a list of unique prompts for the given season."""
    prompts = []
    seen_hashes = set()

    attempts = 0
    max_attempts = count * 10  # Prevent infinite loop

    while len(prompts) < count and attempts < max_attempts:
        prompt = generate_prompt(prompts_data, season)
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:8]

        if prompt_hash not in seen_hashes:
            seen_hashes.add(prompt_hash)
            prompts.append({
                "prompt": prompt,
                "hash": prompt_hash,
                "index": len(prompts)
            })

        attempts += 1

    return prompts

# =============================================================================
# PROGRESS TRACKING
# =============================================================================

def load_progress():
    """Load progress from file."""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_progress(progress):
    """Save progress to file."""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)

def get_completed_indices(progress, season):
    """Get set of completed image indices for a season."""
    if season not in progress:
        progress[season] = {"completed": [], "failed": []}
    return set(progress[season]["completed"])

def mark_completed(progress, season, index):
    """Mark an image index as completed."""
    if season not in progress:
        progress[season] = {"completed": [], "failed": []}
    if index not in progress[season]["completed"]:
        progress[season]["completed"].append(index)
    save_progress(progress)

def mark_failed(progress, season, index, error):
    """Mark an image index as failed."""
    if season not in progress:
        progress[season] = {"completed": [], "failed": []}
    progress[season]["failed"].append({"index": index, "error": str(error)})
    save_progress(progress)

# =============================================================================
# IMAGE GENERATION
# =============================================================================

async def generate_image(session, prompt_data, season, negative_prompt, semaphore, progress, pbar):
    """Generate a single image using Stability AI API."""
    async with semaphore:
        index = prompt_data["index"]
        prompt = prompt_data["prompt"]
        prompt_hash = prompt_data["hash"]

        # Filename format: season_XXXXX_hash.png
        filename = f"{season}_{index:05d}_{prompt_hash}.png"
        output_path = PROJECT_ROOT / season / filename

        # Skip if already exists
        if output_path.exists():
            mark_completed(progress, season, index)
            pbar.update(1)
            return True

        headers = {
            "Authorization": f"Bearer {STABILITY_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        payload = {
            "text_prompts": [
                {"text": prompt, "weight": 1.0},
                {"text": negative_prompt, "weight": -1.0}
            ],
            "cfg_scale": CFG_SCALE,
            "width": DEFAULT_WIDTH,
            "height": DEFAULT_HEIGHT,
            "samples": 1,
            "steps": STEPS,
            "sampler": SAMPLER
        }

        for attempt in range(RETRY_ATTEMPTS):
            try:
                async with session.post(STABILITY_API_URL, headers=headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()

                        # Decode and save image
                        import base64
                        image_data = base64.b64decode(data["artifacts"][0]["base64"])

                        # Optionally upscale to 4K
                        if UPSCALE_TO_4K:
                            image_data = await upscale_image(session, image_data, headers)

                        # Save the image
                        async with aiofiles.open(output_path, 'wb') as f:
                            await f.write(image_data)

                        # Also save a metadata file with the prompt
                        meta_path = output_path.with_suffix('.json')
                        meta = {
                            "prompt": prompt,
                            "negative_prompt": negative_prompt,
                            "season": season,
                            "index": index,
                            "generated_at": datetime.now().isoformat(),
                            "settings": {
                                "width": DEFAULT_WIDTH,
                                "height": DEFAULT_HEIGHT,
                                "cfg_scale": CFG_SCALE,
                                "steps": STEPS,
                                "sampler": SAMPLER,
                                "upscaled": UPSCALE_TO_4K
                            }
                        }
                        async with aiofiles.open(meta_path, 'w') as f:
                            await f.write(json.dumps(meta, indent=2))

                        mark_completed(progress, season, index)
                        pbar.update(1)

                        # Small delay to be nice to the API
                        await asyncio.sleep(REQUEST_DELAY)
                        return True

                    elif response.status == 429:
                        # Rate limited - wait and retry
                        wait_time = RETRY_DELAY * (attempt + 1)
                        print(f"\nRate limited, waiting {wait_time}s...")
                        await asyncio.sleep(wait_time)

                    else:
                        error_text = await response.text()
                        print(f"\nAPI error {response.status}: {error_text[:200]}")
                        await asyncio.sleep(RETRY_DELAY)

            except Exception as e:
                print(f"\nRequest error: {e}")
                await asyncio.sleep(RETRY_DELAY)

        # All retries failed
        mark_failed(progress, season, index, "Max retries exceeded")
        pbar.update(1)
        return False

async def upscale_image(session, image_data, headers):
    """Upscale image to 4K using Stability AI's upscaler."""
    try:
        # First, we need to upscale 2x using ESRGAN
        # Then potentially resize to exact 4K dimensions

        import base64

        # For the upscale API, we need to send as multipart form data
        form_data = aiohttp.FormData()
        form_data.add_field('image', image_data, filename='image.png', content_type='image/png')
        form_data.add_field('width', '3072')  # 2x width (1536 * 2 = 3072)

        upscale_headers = {
            "Authorization": headers["Authorization"],
            "Accept": "image/png"
        }

        async with session.post(UPSCALE_API_URL, headers=upscale_headers, data=form_data) as response:
            if response.status == 200:
                upscaled_data = await response.read()

                # Resize to exact 4K dimensions using PIL
                img = Image.open(io.BytesIO(upscaled_data))
                img_resized = img.resize((3840, 2160), Image.Resampling.LANCZOS)

                # Convert back to bytes
                output_buffer = io.BytesIO()
                img_resized.save(output_buffer, format='PNG', optimize=True)
                return output_buffer.getvalue()
            else:
                # If upscale fails, just resize the original
                print(f"\nUpscale API returned {response.status}, using local resize")
                img = Image.open(io.BytesIO(image_data))
                img_resized = img.resize((3840, 2160), Image.Resampling.LANCZOS)
                output_buffer = io.BytesIO()
                img_resized.save(output_buffer, format='PNG', optimize=True)
                return output_buffer.getvalue()

    except Exception as e:
        print(f"\nUpscale error: {e}, using local resize")
        # Fallback to simple resize
        img = Image.open(io.BytesIO(image_data))
        img_resized = img.resize((3840, 2160), Image.Resampling.LANCZOS)
        output_buffer = io.BytesIO()
        img_resized.save(output_buffer, format='PNG', optimize=True)
        return output_buffer.getvalue()

async def generate_season(season, count, start_from=0):
    """Generate all images for a single season."""
    print(f"\n{'='*60}")
    print(f"Generating {count} images for {season.upper()}")
    print(f"{'='*60}\n")

    # Load prompts and progress
    prompts_data = load_prompts()
    progress = load_progress()
    negative_prompt = get_negative_prompt(prompts_data)

    # Generate prompt list
    all_prompts = generate_all_prompts(prompts_data, season, count)

    # Filter to only pending (skip completed)
    completed = get_completed_indices(progress, season)
    pending_prompts = [p for p in all_prompts if p["index"] not in completed and p["index"] >= start_from]

    if not pending_prompts:
        print(f"All {count} images for {season} already generated!")
        return

    print(f"Pending: {len(pending_prompts)} images (skipping {len(completed)} completed)")

    # Ensure output directory exists
    output_dir = PROJECT_ROOT / season
    output_dir.mkdir(exist_ok=True)

    # Create semaphore for rate limiting
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    # Create progress bar
    pbar = tqdm(total=len(pending_prompts), desc=f"{season.capitalize()}", unit="img")

    # Create aiohttp session and generate
    async with aiohttp.ClientSession() as session:
        tasks = [
            generate_image(session, prompt_data, season, negative_prompt, semaphore, progress, pbar)
            for prompt_data in pending_prompts
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

    pbar.close()

    # Summary
    successful = sum(1 for r in results if r is True)
    failed = len(results) - successful

    print(f"\n{season.capitalize()} complete: {successful} successful, {failed} failed")

    return successful, failed

# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate JTF News background images using Stability AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python generate.py --season spring --count 100    # Generate 100 spring images
    python generate.py --season all --count 1920      # Generate 1920 images for each season
    python generate.py --season summer --start-from 500  # Resume from index 500
    python generate.py --test                         # Generate 1 test image per season
        """
    )

    parser.add_argument(
        "--season",
        choices=["spring", "summer", "fall", "winter", "all"],
        default="all",
        help="Which season to generate (default: all)"
    )

    parser.add_argument(
        "--count",
        type=int,
        default=1920,
        help="Number of images per season (default: 1920)"
    )

    parser.add_argument(
        "--start-from",
        type=int,
        default=0,
        help="Start from this index (for resuming, default: 0)"
    )

    parser.add_argument(
        "--test",
        action="store_true",
        help="Test mode: generate just 1 image per season"
    )

    parser.add_argument(
        "--no-upscale",
        action="store_true",
        help="Skip upscaling to 4K (faster, smaller files)"
    )

    parser.add_argument(
        "--concurrent",
        type=int,
        default=MAX_CONCURRENT_REQUESTS,
        help=f"Max concurrent API requests (default: {MAX_CONCURRENT_REQUESTS})"
    )

    args = parser.parse_args()

    # Validate API key
    if not STABILITY_API_KEY:
        print("ERROR: STABILITY_API_KEY environment variable not set!")
        print("Please set it in your .env file or export it:")
        print("  export STABILITY_API_KEY=sk-...")
        sys.exit(1)

    # Apply settings
    global UPSCALE_TO_4K, MAX_CONCURRENT_REQUESTS
    UPSCALE_TO_4K = not args.no_upscale
    MAX_CONCURRENT_REQUESTS = args.concurrent

    # Determine count
    count = 1 if args.test else args.count

    # Determine seasons to process
    if args.season == "all":
        seasons = ["spring", "summer", "fall", "winter"]
    else:
        seasons = [args.season]

    # Print configuration
    print("\n" + "="*60)
    print("JTF News Background Image Generator")
    print("="*60)
    print(f"Seasons: {', '.join(seasons)}")
    print(f"Images per season: {count}")
    print(f"Total images: {len(seasons) * count}")
    print(f"Upscale to 4K: {UPSCALE_TO_4K}")
    print(f"Concurrent requests: {MAX_CONCURRENT_REQUESTS}")
    print(f"Output: {PROJECT_ROOT}")
    print("="*60)

    # Estimate cost
    cost_per_image = 0.01  # Approximate
    total_cost = len(seasons) * count * cost_per_image
    print(f"\nEstimated cost: ~${total_cost:.2f}")

    if not args.test:
        print("\nStarting in 5 seconds... (Ctrl+C to cancel)")
        time.sleep(5)

    # Generate images
    start_time = time.time()
    total_successful = 0
    total_failed = 0

    for season in seasons:
        try:
            successful, failed = asyncio.run(
                generate_season(season, count, args.start_from)
            )
            total_successful += successful
            total_failed += failed
        except KeyboardInterrupt:
            print("\n\nInterrupted by user. Progress saved.")
            sys.exit(0)
        except Exception as e:
            print(f"\nError generating {season}: {e}")
            total_failed += count

    # Final summary
    elapsed = time.time() - start_time
    print("\n" + "="*60)
    print("GENERATION COMPLETE")
    print("="*60)
    print(f"Total successful: {total_successful}")
    print(f"Total failed: {total_failed}")
    print(f"Time elapsed: {elapsed/60:.1f} minutes")
    print(f"Average per image: {elapsed/max(total_successful,1):.1f} seconds")
    print("="*60)

if __name__ == "__main__":
    main()
