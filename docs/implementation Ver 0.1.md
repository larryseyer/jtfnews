# JTF News Implementation Plan - Version 0.1

## Core Principle

**SIMPLICITY = STABILITY**

Always look for the simplest solution. This code needs to run forever.

---

## The One-Liner (for a ten-year-old)

*"Think of us as a very slow, very honest librarian. We read everything, say nothing unless two other librarians agree, and never raise our voice."*

---

## What We're Building

A 24/7 automated news stream that:
- Scrapes headlines from 20 public news sources
- Uses Claude AI to strip all editorialization, bias, and opinion
- Requires 2+ unrelated sources for verification
- Displays calm 4K visuals with natural AI voice
- Streams to YouTube via OBS Studio

---

## Architecture

**Let OBS do what OBS does best. We write minimal code.**

| Component | Handled By |
|-----------|------------|
| Background rotation | OBS Image Slideshow |
| Video backgrounds | OBS Media Source |
| Audio playback | OBS Media Source |
| Layer compositing | OBS Scene |
| Streaming to YouTube | OBS RTMP |
| News scraping | Python (main.py) |
| AI text processing | Claude API |
| Voice generation | ElevenLabs API |
| Lower third display | HTML/CSS/JS |

---

## Data Storage Standards

### Naming Conventions

**All dates use ISO 8601 format: `YYYY-MM-DD`**

| File Type | Naming Pattern | Example |
|-----------|----------------|---------|
| Daily log | `YYYY-MM-DD.txt` | `2026-02-10.txt` |
| Daily archive | `YYYY-MM-DD.txt.gz` | `2026-02-10.txt.gz` |
| Hash file | `shown_YYYY-MM-DD.txt` | `shown_2026-02-10.txt` |

### Directory Structure

```
JTFNews/
├── data/                       # Runtime data (gitignored except current day)
│   ├── current.txt             # Current story (overwritten each cycle)
│   ├── source.txt              # Current source attribution
│   ├── 2026-02-10.txt          # Today's log (plain text)
│   └── shown_2026-02-10.txt    # Today's shown story hashes
│
└── archive/                    # Permanent archive (pushed to GitHub)
    └── 2026/                   # Year folder
        ├── 2026-01-15.txt.gz   # Gzipped daily logs
        ├── 2026-01-16.txt.gz
        └── ...
```

### File Formats

**Daily Log Format (`YYYY-MM-DD.txt`):**
```
# JTF News Daily Log
# Date: 2026-02-10
# Generated: UTC

2026-02-10T14:30:00Z|Reuters,BBC|9.8,9.5|Earthquake measuring 6.2 struck Chile, affecting approximately 12,000 people.
2026-02-10T15:00:00Z|AP,Guardian|9.7,9.2|United Nations approved resolution on climate funding with 143 votes in favor.
```

**Format:** `ISO_TIMESTAMP|SOURCES|SCORES|CLEAN_SENTENCE`

- Pipe-delimited (simple, grep-able)
- UTF-8 encoding
- One story per line
- Header comments for human readability

**Hash File Format (`shown_YYYY-MM-DD.txt`):**
```
a1b2c3d4e5f6
b2c3d4e5f6a7
c3d4e5f6a7b8
```
- MD5 hash of each story's clean text (first 12 chars)
- One hash per line
- Used to prevent 24-hour repeats

### News Source Configuration (`config.json`)

```json
{
  "sources": [
    {
      "id": "reuters",
      "name": "Reuters",
      "url": "https://www.reuters.com",
      "tier": 1,
      "parent_company": null,
      "control_type": "family_trust",
      "owners": [
        {"name": "Thomson family trust", "percent": 100, "type": "controlling"}
      ],
      "institutional_holders": [],
      "owner_display": "Thomson family trust (100%)",
      "established": 1851,
      "ratings": {
        "accuracy": 9.8,
        "bias": 0.1,
        "speed": 9.5,
        "consensus": 9.5
      }
    },
    {
      "id": "ap",
      "name": "Associated Press",
      "url": "https://apnews.com",
      "tier": 1,
      "parent_company": null,
      "control_type": "cooperative",
      "owners": [],
      "institutional_holders": [],
      "owner_display": "Cooperative (no owners)",
      "established": 1846,
      "ratings": {
        "accuracy": 9.7,
        "bias": 0.1,
        "speed": 9.5,
        "consensus": 9.5
      }
    },
    {
      "id": "cnn",
      "name": "CNN",
      "url": "https://www.cnn.com",
      "tier": 3,
      "parent_company": "Warner Bros. Discovery",
      "control_type": "corporate",
      "owners": [
        {"name": "Warner Bros. Discovery", "percent": 100, "type": "parent"}
      ],
      "institutional_holders": [
        {"name": "Vanguard", "percent": 9.2},
        {"name": "BlackRock", "percent": 7.1},
        {"name": "State Street", "percent": 4.3}
      ],
      "owner_display": "WBD: Vanguard 9%, BlackRock 7%, State Street 4%",
      "established": 1980,
      "ratings": {
        "accuracy": 8.2,
        "bias": 2.5,
        "speed": 9.0,
        "consensus": 7.5
      }
    }
  ],
  "unrelated_rules": {
    "max_shared_institutional_percent": 5,
    "max_shared_top_holders": 2
  },
  "thresholds": {
    "people_affected": 500,
    "cost_usd": 1000000,
    "confidence_minimum": 0.90
  },
  "cycle_minutes": 30
}
```

**Key fields:**
- `tier` - 1 (independent), 2 (public broadcaster), 3 (conglomerate)
- `control_type` - "family_trust", "cooperative", "public", "corporate"
- `institutional_holders` - BlackRock, Vanguard, etc. with percentages
- `unrelated_rules` - defines when two sources count as "unrelated"
- `owner_display` - formatted string for lower third (grey text)
- `ratings.bias` - 0 = center, negative = left, positive = right

### Archive Process (Midnight GMT)

```
1. Close today's log file
2. Gzip: 2026-02-10.txt → 2026-02-10.txt.gz
3. Move to: archive/2026/2026-02-10.txt.gz
4. Git commit: "Archive 2026-02-10"
5. Git push to GitHub
6. Delete: data/2026-02-10.txt (original)
7. Delete: data/shown_2026-02-10.txt
8. Create new day's files
```

### Retention Policy

| Data Type | Retention | Location |
|-----------|-----------|----------|
| Current story | Overwritten each cycle | `data/current.txt` |
| Daily log (uncompressed) | 24 hours | `data/` |
| Daily log (gzipped) | Forever | `archive/YYYY/` |
| Shown hashes | 24 hours | `data/` |
| Raw scraped HTML | Never stored | - |
| TTS audio | Overwritten each story | `audio/current.wav` |

**From white paper:** "We do not store raw data longer than seven days."

Raw scraped data is processed immediately and discarded. Only the clean, verified sentences are archived.

### Encoding Standards

- **All text files:** UTF-8, no BOM
- **Line endings:** LF (Unix-style)
- **Timestamps:** ISO 8601 with timezone (`2026-02-10T14:30:00Z`)
- **JSON:** Minified for storage, pretty-printed for config

---

## Files to Create (9 total)

```
JTFNews/
├── main.py                 # The only Python script (~400 lines)
├── config.json             # News sources with ownership & ratings
├── docs/
│   └── source-ownership.md # PUBLIC: All source ownership (transparency)
├── .env                    # API keys (gitignored)
├── requirements.txt        # 6 Python packages
├── README.md               # Setup instructions
├── .gitignore              # Ignore .env, data/, audio/
├── web/
│   ├── lower-third.html    # OBS browser source (~20 lines)
│   ├── lower-third.css     # Styling (~40 lines)
│   └── lower-third.js      # Display logic (~50 lines)
├── data/                   # Runtime data (created automatically)
│   ├── current.txt         # Current story (overwritten each cycle)
│   ├── source.txt          # "Reuters – 9.8 │ Owner (100%)"
│   ├── alexa-feed.json     # Alexa Flash Briefing feed (auto-generated)
│   ├── corrections.txt     # Pending corrections queue
│   ├── YYYY-MM-DD.txt      # Today's log (ISO 8601 dated)
│   └── shown_YYYY-MM-DD.txt # Today's shown hashes
├── archive/                # Permanent archive (pushed to GitHub)
│   └── YYYY/               # Year folders
│       └── YYYY-MM-DD.txt.gz  # Gzipped daily logs
├── audio/
│   └── current.wav         # TTS audio (ElevenLabs)
└── media/
    └── (4K images + videos for OBS)
```

**Total: ~500 lines of code**

---

## main.py - What It Does

Runs every 30 minutes in an infinite loop:

```
1. Check data/corrections.txt FIRST (corrections are priority)
2. Scrape headlines from 20 sources (respect robots.txt)
3. Send each headline to Claude AI for fact extraction
4. Verify: require 2+ sources with different owner groups
5. Filter: 500+ people affected, $1M+ cost, law change, or border change
6. Check for duplicates (no repeats within 24h)
7. Generate TTS audio via ElevenLabs
8. Write to data/current.txt and data/source.txt
9. Update data/alexa-feed.json (for Alexa Flash Briefing)
10. Tweet once per story (no engagement)
11. At midnight GMT: zip daily log, push to GitHub
12. Sleep 30 minutes, repeat
```

---

## Lower Third Display

**Industry-standard format with ownership disclosure:**

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│                   (4K serene background)                    │
│                                                             │
│  ───────────────────────────────────────────────────────── │
│  Reuters – 9.8 │ Thomson Reuters (100%)     (grey bar)      │
│  ─────────────────────────────────────────────────────────  │
│  Earthquake measuring 6.2 struck Chile,     (white text)    │
│  affecting approximately 12,000 people.                     │
└─────────────────────────────────────────────────────────────┘
```

**Source bar format:** `SOURCE – SCORE │ TOP 3 OWNERS (percentages)`

Examples:
- `Reuters – 9.8 │ Thomson Reuters (100%)`
- `Guardian – 9.2 │ Scott Trust (100%)`
- `Sky News – 8.5 │ Comcast (100%) via Sky Group`

**Specifications:**
- Font: Arial, white, 64px (4K readable)
- Position: Title-safe area (5% from edges)
- Source bar: Full width, grey (#808080), includes owner disclosure
- Text shadow: 2px black drop shadow
- Animation: 1s fade in → 5s hold → 1s fade out

**From ChatSummary:** "Source ratings shown (accuracy, bias, speed, consensus) + top 3 owners"

---

## Human in the Loop (Kill Switch)

**One person. One button. No questions asked.**

The only override we allow. Everything else is code.

### The Rule
A human (Larry) can kill the stream instantly if the AI starts hallucinating.
- Not for opinion
- Not for flair
- Just to stop bad data from broadcasting

### Watchdog Alerts (SMS)

**Triggers:**
1. Confidence score below 90%
2. Two consecutive sentences contradict each other
3. Source verification fails unexpectedly
4. Any system error

**Alert format:**
```
JTF ALERT: Possible hallucination detected.
Confidence: 72%
Story: "..."
Action required.
```

**Implementation:**
```python
# In main.py
import os
from twilio.rest import Client  # or similar SMS service

def send_alert(message):
    client = Client(os.getenv("TWILIO_SID"), os.getenv("TWILIO_TOKEN"))
    client.messages.create(
        body=f"JTF ALERT: {message}",
        from_=os.getenv("TWILIO_FROM"),
        to=os.getenv("ALERT_PHONE")
    )

def watchdog_check(story, confidence):
    if confidence < 0.90:
        send_alert(f"Low confidence ({confidence:.0%}): {story[:50]}...")
        return False  # Don't publish
    return True
```

### Kill Switch

**Remote stop options:**
1. SSH into server, run: `touch /tmp/jtf-stop` (main.py checks this file)
2. GitHub webhook that triggers stop
3. Simple web endpoint (password protected)

```python
# In main.py main loop
if os.path.exists("/tmp/jtf-stop"):
    print("KILL SWITCH ACTIVATED - Stopping broadcast")
    # Clear current.txt, stop TTS, notify
    sys.exit(0)
```

**No committee. No press release. Just you.**

---

## Corrections (Loud and Immediate)

**From ChatSummary:** "Corrections loud and immediate"

When a previously broadcast fact is found to be incorrect:

1. **Detection:** Manual flag or source retraction detected
2. **Priority:** Correction becomes FIRST story in next cycle
3. **Format:**
   ```
   CORRECTION: [Original statement] has been updated.
   [New accurate statement]
   ```
4. **Voice:** Same calm voice, but correction is announced first
5. **Log:** Marked in daily log with `[CORRECTION]` prefix
6. **Tweet:** Original tweet deleted, correction tweeted

**Implementation:**
- `data/corrections.txt` - pending corrections queue
- main.py checks this file FIRST each cycle
- Corrections bypass normal verification (already verified as wrong)

---

## Silence is the Brand

**From ChatSummary:** "Silence when no qualifying news"

When no stories meet thresholds:
- Background continues rotating (OBS Image Slideshow)
- Lower third shows nothing (empty/hidden)
- No audio plays
- Stream continues silently
- This is intentional - silence IS the message

**"If we stay boring enough, we might just change the world."**

---

## Voice (ElevenLabs)

**Requirement:** "Calm female voice, northern English. Custom. Quiet."

**Natural-sounding AI voice is ESSENTIAL for project success.**

- Service: ElevenLabs API (most realistic available)
- Voice: Custom "calm northern English female" (created in dashboard)
- Output: audio/current.wav
- Cost: ~$5/month hobby tier

---

## OBS Studio Setup

**Scene: JTF News Live**

```
Layer 1: Image Slideshow
├── Source: media/ folder
├── Mode: Random, no repeats
├── Interval: 45 seconds
└── Transition: Crossfade

Layer 2: Browser Source
├── URL: file:///path/to/web/lower-third.html
├── Size: 3840x2160 (4K)
└── Background: Transparent

Layer 3: Media Source
├── File: audio/current.wav
├── Restart: When source becomes active
└── Visibility: Hidden (audio only)
```

**YouTube Stream Settings (from ChatSummary):**
- Title: `JTF News – Live`
- Description: `Facts only.`
- **Chat: DISABLED** (no interaction)
- Comments: Disabled
- Likes/Dislikes: Hidden if possible
- Category: News & Politics
- Visibility: Public
- DVR: Enabled (allows rewind)
- Latency: Normal (not ultra-low)

---

## Dependencies

```
anthropic          # Claude API (text processing)
elevenlabs         # TTS API (natural voice)
beautifulsoup4     # HTML parsing
requests           # HTTP requests
tweepy             # X/Twitter API
twilio             # SMS alerts (watchdog)
python-dotenv      # .env loading
```

---

## API Keys Required (.env file)

```
ANTHROPIC_API_KEY=sk-ant-...
ELEVENLABS_API_KEY=...
TWITTER_API_KEY=...
TWITTER_API_SECRET=...
TWITTER_ACCESS_TOKEN=...
TWITTER_ACCESS_SECRET=...

# Watchdog SMS Alerts (Twilio)
TWILIO_SID=...
TWILIO_TOKEN=...
TWILIO_FROM=+1234567890
ALERT_PHONE=+1234567890      # Larry's phone
```

---

## News Sources & Ownership

### The "Unrelated Sources" Rule

**Sources are UNRELATED only if:**
1. They don't share the same parent company
2. No single investor (BlackRock, Vanguard, etc.) holds >5% in both
3. Same top 3 institutional holders don't appear in both

**Examples:**
- CNN + ABC = RELATED (both major conglomerates with overlapping institutional investors)
- CNN + Reuters = UNRELATED (Reuters is Thomson family trust, different structure)
- AP + BBC = UNRELATED (cooperative + public broadcaster, no corporate overlap)

### Ownership Categories

**TIER 1: Independent/Center (Preferred - no corporate drama)**
| Source | Control | Why Independent |
|--------|---------|-----------------|
| Reuters | Thomson family trust | Tightly controlled, minimal institutional sway |
| AP | Not-for-profit cooperative | No owners at all |
| BBC | UK public broadcaster | Public-funded, editorially independent |
| NPR | US public radio | Non-profit, listener-supported |
| PBS | US public broadcasting | Non-profit |

**TIER 2: Public Broadcasters (Government-funded but editorially independent)**
| Source | Country | Funding |
|--------|---------|---------|
| CBC | Canada | Canadian public |
| ABC Australia | Australia | Australian public |
| DW | Germany | German public |
| France 24 | France | France Médias Monde |

**TIER 3: Major Conglomerates (Institutional investor overlap - use carefully)**
| Source | Parent | Top Institutional Holders |
|--------|--------|---------------------------|
| ABC News (US) | Disney | Vanguard ~8%, BlackRock ~7% |
| NBC/MSNBC | Comcast | Vanguard ~8%, BlackRock ~7% |
| CNN | Warner Bros. Discovery | Vanguard, BlackRock (similar) |
| CBS | Paramount | Vanguard, BlackRock (similar) |
| Fox News | Fox Corporation | Murdoch family control |

**TIER 3 Rule:** Two sources from Tier 3 can only count as "unrelated" if they have different parent companies AND don't share the same top 3 institutional holders above 5%.

### Ownership Display Format

**Shown in grey, next to reliability score:**
```
Reuters – 9.8 │ Thomson family trust (100%)
AP – 9.7 │ Cooperative (no owners)
CNN – 8.2 │ Warner Bros. Discovery: Vanguard 9%, BlackRock 7%, State Street 4%
```

No drama. No judgement. Just the numbers. People can decide for themselves.

### Bias Ratings (from Ad Fontes Media Bias Chart, Jan 2026)

| Category | Sources |
|----------|---------|
| Center/Minimal Bias | Reuters, AP, BBC, CBS News |
| Skews Left | CNN (TV), MSNBC, ABC, NBC |
| Skews Right | Fox News (TV) |

**Our approach:** Pull primarily from center sources. Tag all with ownership + bias scores. The contrast speaks for itself.

### Public Ownership List

We maintain a **public, transparent list** of all source ownership on GitHub.
- Updated whenever ownership changes
- Anyone can verify
- No accusations of playing favourites

File: `docs/source-ownership.md` (public, in repo)

---

## Constraints (from White Paper)

- [ ] No APIs for news (scraping only)
- [ ] Respect robots.txt always
- [ ] 2+ unrelated sources required
- [ ] No repeats within 24 hours
- [ ] Silence when no qualifying news
- [ ] Delete raw data after 7 days
- [ ] Daily archive push at midnight GMT
- [ ] One tweet per story, no engagement
- [ ] CC-BY-SA license on output

---

## Verification Steps

After implementation:

1. `python main.py` - verify scraping and processing works
2. Check `data/current.txt` contains clean factual sentence
3. Check `audio/current.wav` plays natural voice
4. Open `web/lower-third.html` in browser - verify fade animation
5. Add Browser Source in OBS - verify transparent overlay
6. Add Image Slideshow for `media/` folder - verify rotation
7. Test full stream with all layers

---

## Background Media

Add to `media/` folder:
- 4K resolution (3840x2160) required
- Images: JPG, PNG, WebP
- Videos: MP4, WebM (will play muted)
- Content: Clouds, waves, fields, stars, mountains, fog
- Never related to news events
- Any filename - no naming convention

OBS Image Slideshow handles all rotation automatically.

---

## Implementation Order

1. Create folder structure
2. Write config.json with 20 sources
3. Create .env template
4. Write requirements.txt
5. Write main.py (the single script)
6. Write web/lower-third.html
7. Write web/lower-third.css
8. Write web/lower-third.js
9. Update README.md
10. Configure OBS Studio
11. Test end-to-end

---

## What Happens at Runtime

```
[Every 30 minutes]
main.py wakes up
    ↓
Scrapes 20 news sites (respects robots.txt)
    ↓
Sends headlines to Claude AI
    ↓
Claude returns: "Earthquake measuring 6.2 struck Chile,
                affecting approximately 12,000 people."
    ↓
Verifies: Reuters + BBC both reported (different owner groups) ✓
    ↓
Checks hash against shown_2026-02-10.txt (no duplicates) ✓
    ↓
Writes to data/current.txt
Writes "Reuters – 9.8" to data/source.txt
Appends to data/2026-02-10.txt (daily log)
Appends hash to data/shown_2026-02-10.txt
    ↓
Calls ElevenLabs → audio/current.wav
    ↓
Tweets the sentence once (no engagement)
    ↓
lower-third.js detects file change
    ↓
Text fades in (1s) → displays (5s) → fades out (1s)
OBS plays audio/current.wav
    ↓
Silence until next story
    ↓
[At midnight GMT]
Gzip: data/2026-02-10.txt → archive/2026/2026-02-10.txt.gz
Git commit + push to GitHub
Delete: data/2026-02-10.txt, data/shown_2026-02-10.txt
Create new day's files
```

---

## Alexa Flash Briefing Skill

**"Alexa, give me my flash briefing"** → Alexa reads latest JTF News facts aloud.

### How It Works
Alexa's Flash Briefing is designed for short, news-style snippets. You feed it text via JSON/RSS, Alexa handles TTS. No programming, no backend headaches.

### Setup Steps (Alexa Developer Console)

1. Go to `developer.amazon.com/alexa/console/ask` (free Amazon account)
2. Click **"Create Skill"**
3. Name: `Just the Facts News`
4. Language: English
5. Model: **Flash Briefing** (built-in option)
6. Backend: **Provision your own**
7. Click **"+ Add new feed"**:
   - Preamble (70 chars max): `Here are the facts.`
   - Feed name: `JTF Daily`
   - Update frequency: Every 30 minutes (or daily)
   - Content type: **Text** (Alexa reads via TTS)
   - Genre: **News**
   - Feed URL: Points to our JSON file (see below)
8. Add 512x512 icon (calm, simple logo)
9. Save and test on Echo device
10. Publish when ready

### Feed Format (JSON)

main.py generates `data/alexa-feed.json`:

```json
{
  "uid": "jtf-2026-02-10-001",
  "updateDate": "2026-02-10T14:30:00.0Z",
  "titleText": "Just the Facts News",
  "mainText": "Earthquake measuring 6.2 struck Chile, affecting approximately 12,000 people. United Nations approved resolution on climate funding with 143 votes in favor.",
  "redirectionUrl": "https://youtube.com/live/jtfnews"
}
```

### Hosting the Feed

Options (simplest first):
1. **GitHub Raw URL** - Push JSON to repo, use raw.githubusercontent.com URL
2. **S3 Bucket** - Free tier, public read access
3. **GitHub Pages** - Free static hosting

main.py updates this file every cycle alongside other outputs.

### Files to Add

```
data/
├── alexa-feed.json    # Current stories for Alexa (auto-generated)
└── ...
```

### In main.py

```python
def update_alexa_feed(stories):
    feed = {
        "uid": f"jtf-{date.today()}-{cycle_num:03d}",
        "updateDate": datetime.utcnow().isoformat() + "Z",
        "titleText": "Just the Facts News",
        "mainText": " ".join([s['text'] for s in stories[-5:]]),  # Last 5 stories
        "redirectionUrl": "https://youtube.com/live/jtfnews"
    }
    with open("data/alexa-feed.json", "w") as f:
        json.dump(feed, f)
```

---

## Google Home (Future)

Actions on Google integration - similar concept, different format. Not in v0.1.

---

## RSS Feed (Future)

Standard news feed format for feed readers. Simple XML generation from same data.

---

## X (Twitter) Behavior

**Every 30 minutes. One tweet. Plain English.**

Format:
```
Earthquake measuring 6.2 struck Chile, affecting approximately 12,000 people.
```

**Rules:**
- One tweet per verified story
- The headline in plain English
- **No emoji**
- **No hashtags**
- **No commentary**
- Just the sentence
- Optional: link to YouTube live stream
- **No replies ever**
- **No likes**
- **No retweets**
- **No quote tweets**

If correction needed: delete original, post correction.

*"Let the curiosity pull them in."*

---

**Ready to implement when approved.**
