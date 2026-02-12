# CLAUDE.md - JTF News

## Project Overview
JTF News (Just the Facts News) - Automated 24/7 news stream that reports only verified facts. No opinions, no adjectives, no interpretation.

## Current State
**Planning/specification phase** - No implementation code yet. SPECIFICATION.md is the primary reference (~53KB, comprehensive).

## Key Architecture Principles (from spec)
- **Simplicity = Stability** - Always choose the simplest solution; code must run forever
- **OBS Does Heavy Lifting** - Let OBS handle media/streaming; we write minimal code (~500 lines total)
- **Silence is Default** - Don't speak unless facts are verified by 2+ unrelated sources
- **No Drama** - No emotional language, no "BREAKING" labels, just calm facts

## Key Files
- `SPECIFICATION.md` - Complete technical spec (read this first for implementation)
- `PromptStart.md` - Initial prompt/context document
- `docs/implementation Ver 0.1.md` - Implementation notes
- `docs/mediasetup.md` - Media/OBS setup instructions

## Commands
- **`./bu.sh "commit message"`** - ALWAYS use this for commits. Does git commit+push AND creates timestamped backup zip to Dropbox (excludes media/)
- `./deploy.sh` - Rsync source files to deploy machine

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
| Intel/Mojave (deploy) | `/Volumes/larryseyer/JTFNews` | Production streaming |

### CRITICAL: Always Deploy After Making Changes
After ANY changes to the development folder, ALWAYS run `./deploy.sh` to sync to the production machine.

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
- Check if volume is mounted before deploying: `ls /Volumes/larryseyer/JTFNews`
- If deploy machine venv breaks after copy, run `./fix-after-copy.sh` on the Intel machine

## Folder Structure
- `media/` - Background images organized by season (fall/, spring/, summer/, winter/, generator/)
- `docs/` - Documentation and implementation notes

## Tech Stack (planned)
- Python (~400 lines main script)
- HTML/CSS/JS overlay for OBS browser source
- Claude AI for fact extraction/rewriting
- TTS for audio generation
- OBS for streaming to YouTube
- X/Twitter for posting stories

## Constraints
- No APIs, no paywalls, respect robots.txt
- No ads, no tracking, no long-term raw data storage
- CC-BY-SA license on output
- Non-profit spirit
