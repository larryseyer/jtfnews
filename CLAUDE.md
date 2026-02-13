# CLAUDE.md - JTF News

## Project Overview
JTF News (Just the Facts News) - Automated 24/7 news stream that reports only verified facts. No opinions, no adjectives, no interpretation.

## Current State
**Live and running** - Implementation complete with main.py (~1700 lines). SPECIFICATION.md is the design reference.

## Key Architecture Principles (from spec)
- **Simplicity = Stability** - Always choose the simplest solution; code must run forever
- **OBS Does Heavy Lifting** - Let OBS handle media/streaming; we write minimal code (~500 lines total)
- **Silence is Default** - Don't speak unless facts are verified by 2+ unrelated sources
- **No Drama** - No emotional language, no "BREAKING" labels, just calm facts

## Key Files
- `docs/SPECIFICATION.md` - Complete technical spec (read this first for implementation)
- `docs/WhitePaper.md` - Project philosophy and methodology whitepaper
- `docs/ResilienceSystem.md` - 24/7 uptime resilience design (retry logic, alerts, degradation)
- `docs/implementation Ver 0.1.md` - Implementation notes
- `docs/mediasetup.md` - Media/OBS setup instructions

## Commands

### Development Machine
- **`./bu.sh "commit message"`** - ALWAYS use this for commits. Does git commit+push AND creates timestamped backup zip to Dropbox (excludes media/)
- `./deploy.sh` - Rsync source files to deploy machine

### Deploy Machine (run these ON the deploy machine)
- `./start.sh` - Start the JTF News service
- `./start.sh --fresh` - Clear old stories and start fresh (use after code changes that affect story format)
- `./fix-after-copy.sh` - Reinstall venv dependencies (run if venv breaks after deploy)

### IMPORTANT: Always Use bu.sh for Commits
Do NOT use raw `git commit` commands. Always use `./bu.sh "message"` which:
1. Stages all changes
2. Commits with your message
3. Pushes to origin
4. Creates a timestamped backup zip in Dropbox

## IMPORTANT: Two-Machine Architecture (Apple Silicon → Intel)

**We develop on Apple Silicon but deploy on Intel/Mojave.** These architectures are incompatible for compiled files.

| Machine | Path | Purpose |
|---------|------|---------|
| Apple Silicon (dev) | `/Users/larryseyer/JTFNews` | Development |
| Intel/Mojave (deploy) | `/Volumes/MacLive/Users/larryseyer/JTFNews` | Production streaming |

### CRITICAL: Always Deploy After Making Changes
After ANY changes to the development folder, ALWAYS run `./deploy.sh` to sync to the production machine.

### ⚠️ NEVER EDIT FILES ON THE DEPLOY MACHINE ⚠️
**ALL code changes MUST happen on the DEV machine first, then deploy.**

- The deploy path (`/Volumes/MacLive/...`) is for PRODUCTION ONLY
- NEVER open or edit files at the deploy path directly
- If you accidentally edit on deploy, STOP and copy changes back to dev first
- The deploy.sh script will OVERWRITE deploy files with dev versions (no -u flag)
- Dev is ALWAYS the source of truth

**What gets deployed** (safe to copy):
- Python source files (.py)
- Config files (config.json, requirements.txt)
- Web assets (HTML, CSS, JS)
- Media files (images, videos)
- Shell scripts

**What NEVER gets deployed** (architecture-specific, will break on Intel):
- `venv/` - Python virtual environment (ARM64 binaries)
- `__pycache__/` - Compiled Python bytecode
- `*.pyc` files - Compiled Python
- `.git/` - Git internals
- `data/` and `audio/` - Runtime data (generated on each machine)

### Notes
- `gh-pages-dist/` is for GitHub Pages web assets only, NOT deployment
- Check if volume is mounted before deploying: `ls /Volumes/MacLive/Users/larryseyer/JTFNews`
- If deploy machine venv breaks after copy, run `./fix-after-copy.sh` on the Intel machine

## Folder Structure
- `main.py` - Main application (~2000 lines with resilience system)
- `web/` - OBS browser source overlays (lower-third.html, background-slideshow.html, screensaver.html, monitor.html)
- `gh-pages-dist/` - Public website (GitHub Pages) - how-it-works, whitepaper, feed.xml, stories.json
- `media/` - Background images organized by season (fall/, spring/, summer/, winter/)
- `docs/` - Documentation (SPECIFICATION.md, WhitePaper.md, ResilienceSystem.md)
- `data/` - Runtime data (stories.json, queue.json, api_usage, monitor.json) - NOT committed

## Tech Stack
- Python main script with resilience system (retry logic, alert throttling, graceful degradation)
- HTML/CSS/JS overlays for OBS browser source
- Claude AI (Haiku) for fact extraction/rewriting
- ElevenLabs TTS for audio generation
- Twilio for SMS alerts
- OBS for streaming to YouTube
- GitHub Pages for public website (how-it-works, whitepaper, operations dashboard)

## Constraints
- No APIs, no paywalls, respect robots.txt
- No ads, no tracking, no long-term raw data storage
- CC-BY-SA license on output
- Non-profit spirit
