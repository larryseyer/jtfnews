# JTF News Background Image Generator

Generates 7,680 photorealistic 4K background images (1,920 per season) for JTF News using Stability AI's SDXL model.

## Quick Start

```bash
# 1. Run setup
./setup.sh

# 2. Add your API key
echo 'STABILITY_API_KEY=sk-your-key-here' > .env

# 3. Test with 1 image per season
./run_all.sh --test

# 4. Generate all images
./run_all.sh --parallel
```

## Requirements

- Python 3.9+
- Stability AI API key ([get one here](https://platform.stability.ai/account/keys))
- ~$80-150 budget for API calls

## Scripts

| Script | Description |
|--------|-------------|
| `setup.sh` | One-time setup (venv, dependencies) |
| `run_all.sh` | Generate all seasons (sequential) |
| `run_all.sh --parallel` | Generate all seasons (parallel, faster) |
| `run_all.sh --test` | Test mode (1 image per season) |
| `run_spring.sh` | Generate spring images only |
| `run_summer.sh` | Generate summer images only |
| `run_fall.sh` | Generate fall images only |
| `run_winter.sh` | Generate winter images only |
| `status.sh` | Check generation progress |

## Output Structure

```
media/
├── spring/          # 1,920 spring images
│   ├── spring_00000_abc123.png
│   ├── spring_00000_abc123.json  (metadata)
│   └── ...
├── summer/          # 1,920 summer images
├── fall/            # 1,920 fall images
├── winter/          # 1,920 winter images
└── generator/       # This folder
    ├── logs/        # Generation logs
    └── progress.json # Resume progress
```

## Features

- **Parallel processing**: Up to 5 concurrent API requests
- **Resume support**: Automatically skips completed images
- **Progress tracking**: Run `./status.sh` to check progress
- **4K output**: Images upscaled to 3840x2160
- **Metadata**: JSON file with prompt for each image

## Customization

Edit `prompts.json` to customize:
- Scene types (clouds, waves, fields, mountains, etc.)
- Times of day
- Weather conditions
- Color palettes
- Quality modifiers

Edit `generate.py` to change:
- Image dimensions
- CFG scale / steps
- Concurrent request limit
- API endpoints

## Monitoring

```bash
# Check progress
./status.sh

# Watch logs in real-time
tail -f logs/spring_*.log

# Check running processes
ps aux | grep generate.py

# Stop all generators
pkill -f 'python generate.py'
```

## Cost Estimate

- Stability AI: ~$0.01-0.02 per image
- 7,680 images × $0.01 = **~$77-150**
- Generation time: 4-8 hours (parallel mode)

## Troubleshooting

**API Key Error**
```
ERROR: STABILITY_API_KEY environment variable not set!
```
→ Copy `.env.example` to `.env` and add your key

**Rate Limited**
```
Rate limited, waiting...
```
→ Normal behavior, script will retry automatically

**Resume After Interruption**
```bash
# Progress is auto-saved, just run again:
./run_all.sh
```

## Image Specs

- Resolution: 3840×2160 (4K UHD)
- Aspect ratio: 16:9
- Format: PNG
- Style: Photorealistic, cinematic, serene
- Content: Nature landscapes, no people/text/logos
