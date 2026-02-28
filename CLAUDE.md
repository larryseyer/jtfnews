# CLAUDE.md - JTF News

## Project Overview
JTF News (Just the Facts News) - Automated 24/7 news stream that reports only verified facts. No opinions, no adjectives, no interpretation.

---

# THE JTF METHODOLOGY

## Philosophy

**Two sources. Different owners. Strip the adjectives. State the facts. Stop.**

This is not journalism. It is data. The methodology belongs to no one. It serves everyone.

**Facts without opinion. Wherever they are needed.**

We do not interpret events.
We do not speculate.
We do not persuade.

We record.

---

## Core Principle

We do not editorialise. We state what happened, where, when, and—when known—how many. Nothing more.

Each item states:
- What occurred
- Where it occurred
- When it occurred
- Who was formally involved
- Quantifiable outcomes when available

---

## What Qualifies as News

A verifiable event, within the last 24 hours, that meets at least one criteria:
- Affects 500+ people
- Costs/invests $1M+ USD
- Changes a law or regulation
- Redraws a border
- Involves death or violent crime
- Major scientific/technological achievement
- Humanitarian milestone
- Official statement by head of state/government
- Major economic indicator (GDP, unemployment, inflation)
- International agreement or diplomatic action
- Major natural disaster, pandemic, or public health emergency

Nothing less. Nothing more.

These thresholds define the global stream. Other communities define relevance for themselves.

---

## Verification Standard

Two unrelated sources minimum. Unrelated means different owners, different investors. Where cross-ownership makes full independence difficult to confirm, no common majority shareholder is the minimum threshold.

Where ownership independence cannot be reasonably confirmed, publication is deferred.

---

## Content Rules

### Data Processing
AI rewrites. Strips adjectives. Keeps facts. If it can't be proven, it vanishes.

The system:
- Removes descriptive and evaluative language
- Removes speculation and predictions
- Standardizes titles and naming conventions
- Extracts quantifiable facts
- Excludes unsupported claims

**The system does not add facts not present in source material.**

### Official Titles
People are addressed by their official titles and names. President [surname]. Senator [surname]. Representative [surname]. Judge [surname] of the [district or circuit]. Never bare last names. Titles are facts. Omitting them is editorial. For judges, the court is also a fact.

**Media-invented nicknames are editorialization, not titles.** A journalistic shorthand like "border czar" is not an official government position—it carries implicit judgment. We use official titles only. The title a person holds is a fact. The nickname a reporter invents is opinion.

### Data Sourcing
Public headlines and metadata from open websites. No login walls. No paid content. No APIs. No copyrighted imagery.

---

## AI Transparency & Bias Mitigation

The AI rewriting step is not neutral by default. Language models carry inherited biases from training data. We mitigate this through:

- Public pseudocode and processing logic on GitHub
- Periodic human audits of output against source material
- Community reporting of detected bias or distortion
- Logging of all editorial decisions the algorithm makes (what was stripped, what was kept)

**No algorithm is perfect. Ours is visible.**

---

## Source Ownership Disclosure

For each story, the top three owners of each cited source are listed. Percentages. No spin. This lets the audience see who funds the information they are receiving.

Live source scores: accuracy, bias, speed, consensus. Numbers only. No labels.

### Ownership Data Maintenance
Ownership structures change. Acquisitions happen. Shareholders shift. We review and verify all source ownership data quarterly. Updates are logged publicly on GitHub.

**Stale data is dishonest data. We do not let it drift.**

---

## Voice & Visuals

Calm female voice, northern English. Slow, neutral background images—clouds, fields, water. **Never the event. Never the news.**

Images rotate every 50 seconds. Never match the story. **They breathe.**

Voice only. No music. No breath. When it stops, quiet.

---

## Updates & Corrections

### Update Cadence
Every 30 minutes. Breaking news within 5, but no urgency.

### Corrections & Retractions
When a fact passes the two-source test but is later proven false:

- A correction is issued within the next update cycle
- The original item is marked as corrected in the archive, **never silently deleted**
- If the error is fundamental, a full retraction is issued with explanation
- Corrections are given the same prominence as the original item
- A running corrections log is maintained publicly on GitHub

**We do not bury mistakes. We name them.**

---

## Social Media Policy

We post once per platform. We do not reply. No engagement. No likes. **Corrections are the sole exception**—corrections are posted with the same reach as the original.

---

## Ethics & Data Retention

We do not store raw data longer than 7 days.
Daily summaries are archived on GitHub.
**Nothing hidden. Nothing sold. Just the record.**

No paywalls. No bots. Respect robots.txt. No logs.

---

## Transparency & Governance

- Independent nonprofit oversight
- **No dividends. We own nothing.**
- Public documentation of methodology
- **Pseudocode on GitHub. Anyone can read. No one can change.**
- Version-controlled changes
- Public corrections log
- No advertising or sale of user data

---

## Limits of the Model

JTF News does not provide:
- Opinion
- Analysis
- Forecasts
- Policy advocacy

Disagreements between sources are reported as disagreements of record. The system mitigates bias through **transparency and defined rules, not claims of perfect neutrality.**

---

## Mission

**To provide a structured factual reference layer beneath public discourse.**

When narrative is removed, the record remains.

Because the world needs a place where facts stand alone.

---

## The Loop

24 hours. Midnight GMT. Each story once. Then back.

---

## Community Channels

The global stream is our first application, not our only one.

Communities deserve fact-based reporting:
- Local news, free from partisan spin
- Sports scores, free from hot takes
- School boards, free from drama

Each channel serves a community. Each follows the methodology. Each stands alone.

**If a community needs facts, the methodology is theirs.**

---

## Universal Principles

Across all channels, always:
- Two or more unrelated sources minimum
- AI strips all editorialization
- No engagement. No replies. No likes.
- Calm voice. Neutral visuals.
- No ads. No tracking. No profit.
- Public archives. Open methodology.

**We serve. We do not sell.**

---

# IMPLEMENTATION

## Current State
**Live and running** - Implementation complete with main.py (~2000 lines). SPECIFICATION.md is the design reference.

## Key Architecture Principles (from spec)
- **Simplicity = Stability** - Always choose the simplest solution; code must run forever
- **OBS Does Heavy Lifting** - Let OBS handle media/streaming; we write minimal code (~500 lines total)
- **Silence is Default** - Don't speak unless facts are verified by 2+ unrelated sources
- **No Drama** - No emotional language, no "BREAKING" labels, just calm facts

## Key Files
- `docs/SPECIFICATION.md` - Complete technical spec (read this first for implementation)
- `docs/WhitePaper Ver 1.3 CURRENT.md` - Project philosophy and methodology whitepaper
- `docs/ResilienceSystem.md` - 24/7 uptime resilience design (retry logic, alerts, degradation)
- `docs/implementation Ver 0.1.md` - Implementation notes
- `docs/mediasetup.md` - Media/OBS setup instructions

## Commands

### Running the Service
- `./start.sh` - Start the JTF News service (normal operation)
- `./start.sh --rebuild` - Recover stories.json from daily log (use if stories were accidentally cleared)
- `./start.sh --fresh` - Clear stories and start fresh (requires confirmation; use only when file format changes)
- `./digest.sh` - Manually run the daily digest (record, upload to YouTube)

**When to use each start.sh flag:**
| Situation | Command |
|-----------|---------|
| Normal startup | `./start.sh` |
| Accidentally ran --fresh | `./start.sh --rebuild` |
| Quarterly ownership audit | `python main.py --audit` |
| Apply pending audit (non-interactive) | `python main.py --apply-audit` |
| Regenerate audio for a date | `python main.py --regenerate-audio YYYY-MM-DD` |

### Quarterly Ownership Audit
On startup, main.py checks if the current quarter's ownership audit has been completed. If not:
1. Blocks startup
2. Uses Claude to research current ownership for all 17 sources
3. Presents any changes found
4. Requires confirmation before applying changes
5. Logs the audit to `data/ownership_audit.json`

The audit happens automatically on normal startup if needed, or can be run manually with `--audit`.

### IMPORTANT: Always Use bu.sh for Commits
Do NOT use raw `git commit` commands. Always use `./bu.sh "message"` which:
1. Stages all changes
2. Commits with your message
3. Pushes to origin (main branch)
4. Creates a timestamped backup zip in Downloads

## Single-Machine Architecture

**Everything runs on one machine.** Development, OBS streaming, and production all happen at `/Users/larryseyer/JTFNews`. There is no separate deploy machine.

| Path | Purpose |
|------|---------|
| `/Users/larryseyer/JTFNews` | Everything: development, OBS streaming, production |

## Git Workflow
- Single branch: `main`
- Website served from `/docs` folder on main branch
- Public site: https://jtfnews.org/
- GitHub org: JTFNews/jtfnews

### Automatic GitHub Updates
Runtime files (feed.xml, stories.json, monitor.json, etc.) are pushed automatically by main.py via GitHub API. No manual git operations needed for website updates.

### Syncing Overlay Files (web/ → docs/)
When modifying overlay files that exist in BOTH locations, you MUST update BOTH:

| web/ (OBS local) | docs/ (public site) |
|------------------|---------------------|
| `web/screensaver.html` | `docs/screensaver.html` |
| `web/monitor.html` | `docs/monitor.html` |
| `web/lower-third.html` | (not on public site) |

**Path differences to fix when syncing:**
- `../media` → `./images`
- `../data/stories.json` → `./stories.json`
- `../data/monitor.json` → `./monitor.json`

**Files that exist ONLY in docs/:** index.html, how-it-works.html, whitepaper.html, screensaver-setup.html, feed.xml

## Folder Structure
- `main.py` - Main application (~6500 lines with resilience system, daily digest, YouTube upload)
- `web/` - OBS browser source overlays (lower-third.html, background-slideshow.html, screensaver.html, monitor.html)
- `docs/` - Public website (GitHub Pages) - index.html, how-it-works, whitepaper, feed.xml, stories.json
- `documentation/` - Project documentation (SPECIFICATION.md, WhitePaper Ver 1.3 CURRENT.md, plans/)
- `media/` - Background images organized by season (fall/, spring/, summer/, winter/)
- `data/` - Runtime data (stories.json, queue.json, api_usage, monitor.json) - NOT committed

## Tech Stack
- Python main script with resilience system (retry logic, alert throttling, graceful degradation)
- HTML/CSS/JS overlays for OBS browser source
- Claude AI (Haiku) for fact extraction/rewriting
- ElevenLabs TTS for audio generation (hash-based audio naming for sync integrity)
- ffmpeg/ffprobe for video silence trimming and validation
- YouTube Data API for daily digest uploads
- Twilio for SMS alerts
- OBS for streaming to YouTube (OBS WebSocket v4 for recording control)
- GitHub Pages for public website (how-it-works, whitepaper, operations dashboard)

## Constraints
- No APIs, no paywalls, respect robots.txt
- No ads, no tracking, no long-term raw data storage
- CC-BY-SA license on output
- **YouTube: Creative Commons license** (not Standard YouTube) - aligns with "methodology belongs to no one" philosophy
- Non-profit spirit
