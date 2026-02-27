# JTF News Background Image Generator - Setup Summary

**Date:** February 11, 2026
**Purpose:** Generate 7,680 photorealistic 4K background images for JTF News (1,920 per season)

---

## Project Context

JTF News is a 24/7 automated news stream that:
- Scrapes headlines from 20 public news sources
- Uses Claude AI to strip all editorialization, bias, and opinion
- Requires 2+ unrelated sources for verification
- Streams via OBS to YouTube with calm 4K visuals and natural TTS voice

The background images rotate every 50 seconds and never repeat within 24 hours:
- 86,400 seconds/day ÷ 50 seconds = **1,728 images per day**
- 4 seasons × 1,728 = **6,912 total images needed**

---

## Decision: Online API vs Local Generation

We evaluated two approaches:

| Factor | Local (M4 Max) | Online (Stability API) |
|--------|----------------|------------------------|
| **Time** | ~100 hours (4+ days) | ~4-8 hours |
| **Cost** | Free | ~$80-150 |
| **Reliability** | Risk of crashes/restarts | Cloud-managed |
| **Your Mac** | Tied up for days | Free to use |
| **Parallelism** | 1 image at a time | 10+ concurrent requests |

**Chosen approach: Stability AI API** - The ~$80 cost is worth getting it done in hours instead of days.

---

## What Was Created

### Folder Structure

```
/Users/larryseyer/JTFNews/media/
├── spring/                    # Output: 1,920 spring images
├── summer/                    # Output: 1,920 summer images
├── fall/                      # Output: 1,920 fall images
├── winter/                    # Output: 1,920 winter images
└── generator/
    ├── setup.sh               # One-time setup script ✓
    ├── generate.py            # Main generation script (parallel async) ✓
    ├── prompts.json           # 48 scene types × variations × times × weather ✓
    ├── requirements.txt       # Python dependencies ✓
    ├── .env.example           # API key template ✓
    ├── .env                   # Your API key (needs to be added)
    ├── run_all.sh             # Generate all seasons ✓
    ├── run_spring.sh          # Generate spring only ✓
    ├── run_summer.sh          # Generate summer only ✓
    ├── run_fall.sh            # Generate fall only ✓
    ├── run_winter.sh          # Generate winter only ✓
    ├── status.sh              # Check progress ✓
    ├── README.md              # Documentation ✓
    └── venv/                  # Python virtual environment ✓
```

### Setup Already Completed

- ✅ Created folder structure
- ✅ Created all Python and bash scripts
- ✅ Ran `./setup.sh` - virtual environment created and dependencies installed
- ✅ All scripts made executable

---

## What You Need To Do Tomorrow

### Step 1: Get Stability AI API Key

1. Go to: **https://platform.stability.ai**
2. Create an account (Google, GitHub, or email)
3. Go to **Account → API Keys**
4. Click "Create API Key"
5. Copy the key (starts with `sk-`)
6. Add credits in **Billing** section (~$80-100 for all images)

### Step 2: Save Your API Key

```bash
cd /Users/larryseyer/JTFNews/media/generator
echo 'STABILITY_API_KEY=sk-YOUR-KEY-HERE' > .env
```

### Step 3: Test With 1 Image Per Season

```bash
./run_all.sh --test
```

This generates just 4 images (1 per season) to verify everything works.

### Step 4: Generate All 7,680 Images

```bash
# Parallel mode (faster, ~2-4 hours)
./run_all.sh --parallel

# Or sequential mode (~6-8 hours)
./run_all.sh
```

### Step 5: Monitor Progress

```bash
# Check progress with visual bars
./status.sh

# Watch logs in real-time
tail -f logs/*.log

# Check running processes
ps aux | grep generate.py

# Stop all generators if needed
pkill -f 'python generate.py'
```

---

## Prompts Configuration

The `prompts.json` file contains comprehensive prompts for all 4 seasons:

### Spring Scenes
- Cherry blossom trees, rolling green hills, calm lakes
- Meadows of tulips/daffodils, spring forests, gentle rain
- Flowing streams, lavender fields, coastal scenes

### Summer Scenes
- Ocean waves, golden wheat fields, dramatic cloudscapes
- Lush forest canopy, mountain lakes, sunflower fields
- Summer meadows, coral reef abstracts, desert landscapes

### Fall Scenes
- Maple trees in autumn colors, misty forests
- Mountain landscapes, lakes with reflections
- Country roads, pumpkin fields, vineyards

### Winter Scenes
- Snow-covered peaks, frozen lakes, winter forests
- Northern lights/aurora, snowfields, starry night skies
- Icy rivers, frost patterns, glacial landscapes

Each scene has multiple variations, times of day, and weather conditions to ensure unique images.

---

## Technical Details

### Image Specifications
- **Resolution:** 3840×2160 (4K UHD)
- **Aspect ratio:** 16:9
- **Format:** PNG
- **Style:** Photorealistic, cinematic, serene
- **Content:** Nature landscapes, no people/text/logos

### Generation Settings
- **Model:** Stable Diffusion XL 1.0
- **Base resolution:** 1536×896 (upscaled to 4K)
- **CFG Scale:** 7.5
- **Steps:** 40
- **Sampler:** K_DPM_2_ANCESTRAL
- **Concurrent requests:** 5 (adjustable)

### Features
- **Parallel processing:** Up to 5 concurrent API requests
- **Resume support:** Automatically skips completed images
- **Progress tracking:** `progress.json` saves state
- **Metadata:** JSON file with prompt for each image

---

## Cost Estimate

| Item | Cost |
|------|------|
| SDXL generation (~$0.01/image) | ~$77 |
| Upscaling (included in script) | ~$0-77 |
| **Total estimate** | **$77-150** |

---

## Troubleshooting

### API Key Error
```
ERROR: STABILITY_API_KEY environment variable not set!
```
**Solution:** Make sure `.env` file exists with your key:
```bash
echo 'STABILITY_API_KEY=sk-your-key' > .env
```

### Rate Limited
```
Rate limited, waiting...
```
**Solution:** Normal behavior - script will retry automatically.

### Resume After Interruption
Progress is auto-saved. Just run again:
```bash
./run_all.sh
```

### Check What's Generated
```bash
./status.sh
```

---

## Alternative: Replicate API

If you prefer not to use Stability AI, the script can be modified to use **Replicate** instead:
- Similar pricing (~$0.01/image)
- Simpler signup process
- URL: https://replicate.com/stability-ai/sdxl

---

## Commands Quick Reference

```bash
# Navigate to generator folder
cd /Users/larryseyer/JTFNews/media/generator

# Add API key
echo 'STABILITY_API_KEY=sk-xxx' > .env

# Test (1 image per season)
./run_all.sh --test

# Generate all (parallel - faster)
./run_all.sh --parallel

# Generate all (sequential)
./run_all.sh

# Generate single season
./run_spring.sh
./run_summer.sh
./run_fall.sh
./run_winter.sh

# Check progress
./status.sh

# Watch logs
tail -f logs/*.log

# Stop generation
pkill -f 'python generate.py'
```

---

## Files Reference

| File | Purpose |
|------|---------|
| `generate.py` | Main Python script with async parallel generation |
| `prompts.json` | All scene/variation/time/weather combinations |
| `requirements.txt` | Python dependencies |
| `.env` | Your API key (you need to create this) |
| `.env.example` | Template for .env file |
| `setup.sh` | One-time setup (already run) |
| `run_all.sh` | Generate all seasons |
| `run_[season].sh` | Generate specific season |
| `status.sh` | Show progress bars |
| `progress.json` | Resume state (auto-created) |
| `logs/` | Generation logs (auto-created) |

---

## Summary

1. **Setup is complete** - venv created, dependencies installed
2. **You need to get a Stability AI API key** from https://platform.stability.ai
3. **Add ~$80-100 credits** to your account
4. **Save your key** to `.env` file
5. **Run `./run_all.sh --test`** to verify
6. **Run `./run_all.sh --parallel`** to generate all 7,680 images

Generation will take approximately 2-4 hours in parallel mode and produces 4K photorealistic nature images for all four seasons.

---

*Document created: February 11, 2026*
