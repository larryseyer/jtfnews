# JTF News - Complete Technical Specification
## Version 1.0 | February 2026

---

## Table of Contents
1. [Mission Statement](#1-mission-statement)
2. [Core Principles](#2-core-principles)
3. [Architecture Overview](#3-architecture-overview)
4. [Folder Structure](#4-folder-structure)
5. [News Sources](#5-news-sources)
6. [Claude AI Integration](#6-claude-ai-integration)
7. [Verification Rules](#7-verification-rules)
8. [Breaking News Protocol](#8-breaking-news-protocol)
9. [The 24-Hour Loop](#9-the-24-hour-loop)
10. [Lower Third Design](#10-lower-third-design)
11. [Text-to-Speech](#11-text-to-speech)
12. [Twitter/X Behavior](#12-twitterx-behavior)
13. [YouTube Stream Settings](#13-youtube-stream-settings)
14. [Watchdog Alert System](#14-watchdog-alert-system)
15. [GitHub Archive Structure](#15-github-archive-structure)
16. [Launch Protocol](#16-launch-protocol)
17. [File Specifications](#17-file-specifications)
18. [Constraints and Ethics](#18-constraints-and-ethics)
19. [Verification Checklist](#19-verification-checklist)
20. [Future Directions](#20-future-directions)

---

## 1. Mission Statement

**Tagline (for homepage/stream description):**
> "Think of us as a very slow, very honest librarian. We read everything, say nothing unless two other librarians agree, and never raise our voice."

**One-line description:**
> "Facts only. No opinions."

**What JTF News is:**
- An automated news stream that reports only verified facts
- Claude AI strips all editorialization, bias, and opinion from headlines
- Requires 2+ unrelated sources before speaking
- Streams 24/7 via OBS to YouTube with calm HD visuals and natural TTS voice
- Tweets each story once (no engagement)
- Archives daily to GitHub at midnight GMT

**What JTF News is NOT:**
- Not a news aggregator
- Not commentary
- Not analysis
- Not entertainment
- Not a conversation

---

## 2. Core Principles

### 2.1 Simplicity = Stability
**Always look for the simplest solution to any problem—it will ALWAYS be the most stable.**

This code needs to run FOREVER. Every line we don't write is a line that can't break.

### 2.2 OBS Does the Heavy Lifting
Let OBS handle what OBS does best. We write minimal code.

**OBS handles natively (no custom code):**
- Background image/video rotation → Image Slideshow source
- Video backgrounds → Media Source or VLC Source
- Audio playback → Media Source for TTS files
- Layer compositing → Scene with background + overlay layers
- Streaming to YouTube → Built-in RTMP

**We only write:**
- One Python script (~400 lines)
- One HTML overlay (~20 lines)
- One CSS file (~30 lines)
- One JS file (~50 lines)

**Total: ~500 lines of code. 8 files.**

### 2.3 Silence is Default
- We do not speak unless we have verified facts
- We do not fill silence with filler
- We do not speculate
- If there is nothing to say, we say nothing

### 2.4 No Drama
- No emotional language
- No urgency indicators
- No "BREAKING" labels
- No music stings
- No dramatic pauses
- Just facts, calmly stated

---

## 3. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         OBS STUDIO                               │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Scene: JTF News Live                                     │    │
│  │  ├─ Layer 1: Image Slideshow (media/ folder)            │    │
│  │  │   └─ Random, 50s interval, crossfade, HD              │    │
│  │  ├─ Layer 2: Browser Source (lower-third.html)          │    │
│  │  │   └─ 1920x1080, transparent background               │    │
│  │  └─ Layer 3: Media Source (audio/current.wav)           │    │
│  │      └─ Plays TTS, restarts on file change              │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                   │
│                              ▼                                   │
│                    YouTube RTMP Stream                           │
│                   "JTF News – Live"                              │
└─────────────────────────────────────────────────────────────────┘
                               ▲
                               │ reads
┌─────────────────────────────────────────────────────────────────┐
│                        main.py                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ Scrape   │→ │ Claude   │→ │ Verify   │→ │ Output   │        │
│  │ Headlines│  │ Process  │  │ 2 Sources│  │ Files    │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
│                                              │                   │
│                              ┌───────────────┼───────────────┐  │
│                              ▼               ▼               ▼  │
│                        data/current.txt  audio/current.wav  Tweet│
│                                                                  │
│  ┌──────────┐  ┌──────────┐                                     │
│  │ Watchdog │→ │ SMS Alert│ (Twilio)                            │
│  └──────────┘  └──────────┘                                     │
│                                                                  │
│  ┌──────────┐                                                   │
│  │ Midnight │→ Archive to GitHub (year/jtf-YYYY-MM-DD.txt.zip)  │
│  │ Archive  │                                                   │
│  └──────────┘                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Folder Structure

```
/Users/larryseyer/JTFNews/
├── main.py                 # THE ONLY SCRIPT - runs continuously
├── config.json             # News sources, thresholds, settings
├── .env                    # API keys (GITIGNORED)
├── .gitignore              # Ignores .env, data/, audio/
├── requirements.txt        # Python dependencies (7 packages)
├── SPECIFICATION.md        # This document
├── README.md               # Brief setup instructions
├── web/
│   ├── lower-third.html    # OBS Browser Source overlay
│   ├── lower-third.css     # Styling for lower third
│   └── lower-third.js      # Display logic, polls current.txt
├── data/                   # Runtime data (GITIGNORED)
│   ├── current.txt         # Current story text (one sentence)
│   ├── source.txt          # Source attribution ("Reuters – 9.8")
│   ├── queue.json          # Stories waiting for second source
│   ├── daily_log.txt       # Today's published stories
│   └── shown_hashes.txt    # Prevents repeats within 24h
├── audio/                  # Runtime audio (GITIGNORED)
│   └── current.wav         # TTS audio file
└── media/                  # HD backgrounds (user-provided)
    └── (HD images and videos - OBS Image Slideshow uses this)
```

**Files we create: 8**
**Lines of code: ~500**

---

## 5. News Sources

### 5.1 The 30 Sources

Each source has:
- `name`: Display name
- `url`: Homepage URL
- `rss`: RSS feed URL (if available)
- `scrape_selector`: CSS selector for headlines
- `owner`: Corporate owner/trust
- `country`: Country of origin
- `type`: "public" | "private" | "trust" | "cooperative"
- `default_rating`: Default trust rating (adjustable)

```json
[
  {
    "id": "reuters",
    "name": "Reuters",
    "url": "https://www.reuters.com",
    "rss": "https://www.reuters.com/rssFeed/worldNews",
    "scrape_selector": "h3[data-testid='Heading']",
    "owner": "Thomson Reuters Corporation",
    "country": "UK/Canada",
    "type": "private",
    "default_rating": 9.8
  },
  {
    "id": "ap",
    "name": "Associated Press",
    "url": "https://apnews.com",
    "rss": "https://apnews.com/rss",
    "scrape_selector": "h2.PagePromo-title",
    "owner": "AP Cooperative (member newspapers)",
    "country": "USA",
    "type": "cooperative",
    "default_rating": 9.6
  },
  {
    "id": "bbc",
    "name": "BBC News",
    "url": "https://www.bbc.com/news",
    "rss": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "scrape_selector": "h3[data-testid='card-headline']",
    "owner": "British Broadcasting Corporation",
    "country": "UK",
    "type": "public",
    "default_rating": 9.4
  },
  {
    "id": "npr",
    "name": "NPR",
    "url": "https://www.npr.org/sections/news/",
    "rss": "https://feeds.npr.org/1001/rss.xml",
    "scrape_selector": "h2.title",
    "owner": "National Public Radio (nonprofit)",
    "country": "USA",
    "type": "public",
    "default_rating": 9.2
  },
  {
    "id": "guardian",
    "name": "The Guardian",
    "url": "https://www.theguardian.com/world",
    "rss": "https://www.theguardian.com/world/rss",
    "scrape_selector": "a[data-link-name='article']",
    "owner": "Scott Trust Limited",
    "country": "UK",
    "type": "trust",
    "default_rating": 8.8
  },
  {
    "id": "aljazeera",
    "name": "Al Jazeera English",
    "url": "https://www.aljazeera.com/news/",
    "rss": "https://www.aljazeera.com/xml/rss/all.xml",
    "scrape_selector": "h3.gc__title",
    "owner": "Al Jazeera Media Network (Qatar)",
    "country": "Qatar",
    "type": "state",
    "default_rating": 8.5
  },
  {
    "id": "france24",
    "name": "France 24",
    "url": "https://www.france24.com/en/",
    "rss": "https://www.france24.com/en/rss",
    "scrape_selector": "h2.article__title",
    "owner": "France Médias Monde (French government)",
    "country": "France",
    "type": "public",
    "default_rating": 8.6
  },
  {
    "id": "dw",
    "name": "Deutsche Welle",
    "url": "https://www.dw.com/en/top-stories/s-9097",
    "rss": "https://rss.dw.com/rdf/rss-en-all",
    "scrape_selector": "h2",
    "owner": "German Federal Government",
    "country": "Germany",
    "type": "public",
    "default_rating": 8.7
  },
  {
    "id": "cbc",
    "name": "CBC News",
    "url": "https://www.cbc.ca/news/world",
    "rss": "https://www.cbc.ca/cmlink/rss-world",
    "scrape_selector": "h3.headline",
    "owner": "Canadian Broadcasting Corporation",
    "country": "Canada",
    "type": "public",
    "default_rating": 9.0
  },
  {
    "id": "abc_au",
    "name": "ABC News Australia",
    "url": "https://www.abc.net.au/news/",
    "rss": "https://www.abc.net.au/news/feed/51120/rss.xml",
    "scrape_selector": "h3.CardHeading",
    "owner": "Australian Broadcasting Corporation",
    "country": "Australia",
    "type": "public",
    "default_rating": 9.0
  },
  {
    "id": "independent",
    "name": "The Independent",
    "url": "https://www.independent.co.uk/news/world",
    "rss": "https://www.independent.co.uk/news/world/rss",
    "scrape_selector": "h2.title",
    "owner": "Lebedev family",
    "country": "UK",
    "type": "private",
    "default_rating": 7.8
  },
  {
    "id": "sky",
    "name": "Sky News",
    "url": "https://news.sky.com/world",
    "rss": "https://feeds.skynews.com/feeds/rss/world.xml",
    "scrape_selector": "h3.sdc-site-tile__headline",
    "owner": "Comcast (Sky Group)",
    "country": "UK",
    "type": "private",
    "default_rating": 8.2
  },
  {
    "id": "pbs",
    "name": "PBS NewsHour",
    "url": "https://www.pbs.org/newshour/world",
    "rss": "https://www.pbs.org/newshour/feeds/rss/world",
    "scrape_selector": "h4.title",
    "owner": "Public Broadcasting Service (nonprofit)",
    "country": "USA",
    "type": "public",
    "default_rating": 9.1
  },
  {
    "id": "euronews",
    "name": "Euronews",
    "url": "https://www.euronews.com/news",
    "rss": "https://www.euronews.com/rss",
    "scrape_selector": "h3.title",
    "owner": "Alpac Capital (Portugal)",
    "country": "EU",
    "type": "private",
    "default_rating": 8.0
  },
  {
    "id": "toi",
    "name": "Times of India",
    "url": "https://timesofindia.indiatimes.com/world",
    "rss": "https://timesofindia.indiatimes.com/rssfeeds/296589292.cms",
    "scrape_selector": "span.w_tle",
    "owner": "Bennett Coleman & Co. Ltd.",
    "country": "India",
    "type": "private",
    "default_rating": 7.5
  },
  {
    "id": "scmp",
    "name": "South China Morning Post",
    "url": "https://www.scmp.com/news/world",
    "rss": "https://www.scmp.com/rss/91/feed",
    "scrape_selector": "h2.headline",
    "owner": "Alibaba Group",
    "country": "Hong Kong",
    "type": "private",
    "default_rating": 7.8
  },
  {
    "id": "globe",
    "name": "The Globe and Mail",
    "url": "https://www.theglobeandmail.com/world/",
    "rss": "https://www.theglobeandmail.com/arc/outboundfeeds/rss/category/world/",
    "scrape_selector": "h3.c-card__title",
    "owner": "Woodbridge Company (Thomson family)",
    "country": "Canada",
    "type": "private",
    "default_rating": 8.4
  },
  {
    "id": "irish",
    "name": "Irish Times",
    "url": "https://www.irishtimes.com/world/",
    "rss": "https://www.irishtimes.com/cmlink/news-1.1319192",
    "scrape_selector": "h2.headline",
    "owner": "Irish Times Trust",
    "country": "Ireland",
    "type": "trust",
    "default_rating": 8.5
  },
  {
    "id": "straits",
    "name": "The Straits Times",
    "url": "https://www.straitstimes.com/world",
    "rss": "https://www.straitstimes.com/news/world/rss.xml",
    "scrape_selector": "h5.card-title",
    "owner": "Singapore Press Holdings",
    "country": "Singapore",
    "type": "private",
    "default_rating": 7.6
  },
  {
    "id": "hindustan",
    "name": "Hindustan Times",
    "url": "https://www.hindustantimes.com/world-news",
    "rss": "https://www.hindustantimes.com/feeds/rss/world-news/rssfeed.xml",
    "scrape_selector": "h3.hdg3",
    "owner": "HT Media Ltd. (Shobhana Bhartia)",
    "country": "India",
    "type": "private",
    "default_rating": 7.4
  }
]
```

### 5.2 Ownership Verification Rule

Two sources must have **different owners** to verify a story.

**Same owner = same source:**
- Reuters and Reuters = 1 source
- Two Alibaba-owned outlets = 1 source
- BBC and BBC World Service = 1 source

**Different owners = valid verification:**
- Reuters (Thomson Reuters) + AP (cooperative) = 2 sources ✓
- BBC (public UK) + CBC (public Canada) = 2 sources ✓
- Guardian (Scott Trust) + Independent (Lebedev) = 2 sources ✓

### 5.3 Source Ownership Disclosure

For each story, source ownership is disclosed to show who funds the information.

#### 5.3.1 Data Structure

Each source includes ownership fields matching config.json:

```json
{
  "id": "reuters",
  "name": "Reuters",
  "control_type": "corporate",
  "owner": "Thomson Reuters Corporation",
  "owner_display": "Thomson Reuters (public)",
  "institutional_holders": [
    {"name": "Woodbridge Company", "percent": 69.0},
    {"name": "Vanguard", "percent": 3.1},
    {"name": "BlackRock", "percent": 2.8}
  ]
}
```

For public broadcasters or nonprofits (no institutional shareholders):

```json
{
  "id": "bbc",
  "name": "BBC News",
  "control_type": "public_broadcaster",
  "owner": "British Broadcasting Corporation",
  "owner_display": "UK Public (100%)",
  "institutional_holders": []
}
```

#### 5.3.2 Ownership Types

| Type | Example | Ownership Display |
|------|---------|-------------------|
| `private` | Reuters | Parent company + institutional shareholders if public |
| `public` | BBC, NPR | Government/public entity at 100% |
| `cooperative` | AP | "Member newspapers (cooperative) 100%" |
| `trust` | Guardian | Trust name at 100% |
| `state` | Al Jazeera | State/government entity at 100% |

#### 5.3.3 Display Formats

**Lower-third source bar (compact):**
```
Reuters 9.8|9.5 · AP 9.6|9.2
```
Format: `Name Accuracy|Bias` — no ownership on stream (keeps it calm)

**Website (full disclosure):**
```
Reuters
├─ Accuracy: 9.8
├─ Bias: 9.5
├─ Speed: 9.8
├─ Consensus: 9.8
└─ Ownership:
   • Woodbridge Company (69.0%)
   • Vanguard (3.1%)
   • BlackRock (2.8%)
```

**RSS feed (machine-readable):**
```xml
<source name="Reuters" accuracy="9.8" bias="9.5" speed="9.8" consensus="9.8">
  <owner name="Woodbridge Company" percent="69.0"/>
  <owner name="Vanguard" percent="3.1"/>
  <owner name="BlackRock" percent="2.8"/>
</source>
```

### 5.4 Source Scores

Each source has four live scores, all on a 0-10 scale where **higher is better**. Listed in order of importance:

| Priority | Score | Meaning | Calculation |
|----------|-------|---------|-------------|
| 1 | **Accuracy** | Verification success rate | `(verified_stories / total_stories) × 10` |
| 2 | **Bias** | Editorial neutrality | `10 - (avg_text_removed_percentage × 10)` |
| 3 | **Speed** | Time to first report | `10 - (avg_minutes_behind_first / 60)` capped at 0 |
| 4 | **Consensus** | Agreement with other sources | `(matching_facts / total_facts) × 10` |

#### 5.4.1 Accuracy Score (Priority 1)

Measures how often a source's stories get verified by a second unrelated source.

- **Verification Success:** Story verified by second source → +1 success for both sources
- **Verification Failure:** Story expires from queue without verification → +1 failure

See Section 7.5 for full rating methodology and audit trail.

#### 5.4.2 Bias Score (Priority 2)

Measures how much editorialization Claude strips from a source's headlines. Higher = more neutral (better).

**Calculation:**
```python
bias_score = 10 - (average_percentage_of_text_removed * 10)
```

**Examples:**
| Avg Text Removed | Bias Score | Interpretation |
|------------------|------------|----------------|
| 5% | 9.5 | Excellent - minimal editorialization |
| 25% | 7.5 | Moderate - some loaded language |
| 50% | 5.0 | Poor - heavily editorialized |

**Tracking:**
- For each headline processed, log: `original_length`, `fact_length`, `removed_count`
- File: `data/bias_tracking.json`
- Updated in real-time as headlines are processed

#### 5.4.3 Speed Score (Priority 3)

Measures how quickly a source reports news compared to the first source to report.

**Calculation:**
```python
speed_score = max(0, 10 - (avg_minutes_behind_first_source / 60))
```

**Examples:**
| Avg Minutes Behind | Speed Score | Interpretation |
|--------------------|-------------|----------------|
| 0 (first) | 10.0 | Often breaks news first |
| 30 | 9.5 | Very fast |
| 120 | 8.0 | Moderate |
| 360+ | 4.0 | Slow but thorough |

**Note:** Speed is less important than accuracy. A slow but accurate source is preferable to a fast but unreliable one.

#### 5.4.4 Consensus Score (Priority 4)

Measures how often a source's reported facts align with what other sources report.

**Calculation:**
```python
consensus_score = (facts_matching_other_sources / total_facts_reported) × 10
```

A high consensus score means the source rarely reports things that other sources contradict or fail to corroborate.

#### 5.4.5 Score Display

**Lower-third (compact):** `Reuters 9.8|9.5` (Accuracy|Bias only — top 2 priorities)

**Website (full):**
```
Reuters
├─ Accuracy: 9.8
├─ Bias: 9.5
├─ Speed: 9.8
├─ Consensus: 9.8
└─ Ownership: Thomson Reuters (69%), Vanguard (3.1%), BlackRock (2.8%)
```

**RSS feed:** All 4 scores as XML attributes

**Score explanation** is provided on the website and in the YouTube stream description (not on-stream, to maintain calm aesthetic).

---

## 6. Claude AI Integration

### 6.1 Purpose
Claude AI is the **critical component** that strips all editorialization, bias, and opinion from headlines. Without this, JTF News has no value.

### 6.2 What Claude Does

For each headline, Claude:
1. Detects subtle editorial slant that humans might miss
2. Removes loaded language ("brutal attack" → "attack")
3. Strips implicit opinion ("failed policy" → "policy")
4. Identifies and removes unverifiable claims
5. Extracts only: **what, where, when, how many**
6. Returns a confidence score (0-100%)

### 6.3 API Configuration

**Model:** `claude-haiku-4-5-20251001` (optimized for cost; fact extraction doesn't require Sonnet)
**Fallback:** If API fails, story queues for next cycle. **Never publish unprocessed text.**

### 6.4 The Prompt

```python
CLAUDE_SYSTEM_PROMPT = """You are a fact extraction system for JTF News. Your ONLY job is to strip ALL editorialization, bias, and opinion from news headlines and return pure facts.

RULES:
1. Extract ONLY verifiable facts: what, where, when, how many
2. Remove ALL loaded language:
   - "brutal" → remove
   - "tragic" → remove
   - "shocking" → remove
   - "controversial" → remove
   - "failed" → remove unless objectively measurable
   - "active shooter" → "shooting reported"
   - "terrified" → remove
   - "slammed" → "criticized"
   - "historic" → remove unless objectively true
   - "orders" → "ruled" (for judicial actions - "orders" implies commanding authority; "ruled" is neutral legal terminology)
3. Remove ALL speculation and attribution of motive
4. Remove ALL adjectives that convey judgment
5. Keep numbers, locations, names, and actions
6. Use present tense for ongoing events
7. Maximum ONE sentence
8. If the headline contains NO verifiable facts, return "SKIP"
9. OFFICIAL TITLES REQUIRED - Titles are facts. Omitting them is editorial.
   - Never bare last names. Always include official titles for government officials.
   - HEADS OF STATE/GOVERNMENT: "President Trump", "President Biden", "Prime Minister Starmer" - NEVER just "Trump" or "Biden" alone
   - MEMBERS OF CONGRESS: "Senator Cruz", "Representative Crockett" - NEVER just last name alone
   - CABINET/EXECUTIVES: "Secretary Rubio", "Director Smith" - include their role
   - Format: "[Official Title] [Last Name]" for well-known figures, "[Official Title] [Full Name]" for lesser-known
   - WRONG: "Trump stated...", "Biden announced...", "Cruz said..."
   - CORRECT: "President Trump stated...", "President Biden announced...", "Senator Cruz said..."
   - Media-invented nicknames are editorialization, not titles. "Border czar" is journalistic shorthand that carries implicit judgment - use official title instead
   - If you don't know the official title, describe the role: "the official responsible for border policy"
   - NEVER use first name alone unless disambiguating two people with same last name
   - Former officials: "former President Obama", "former Secretary Clinton" (lowercase "former")
10. JUDGES: Always include full name AND court jurisdiction - both are facts.
     - Format: "Judge [Full Name] of the [Court Name]"
     - Example: "Judge Aileen Cannon of the U.S. District Court for the Southern District of Florida ruled..."
     - Example: "Chief Justice John Roberts of the U.S. Supreme Court ruled..."
     - The judge's NAME is a fact. The court is a fact. Omitting either is editorial.
     - If headline has judge's name → ALWAYS include it with proper title and court
     - ONLY use "A federal judge" if the name is truly unavailable after lookup
     - Never just "Judge [LastName]" without court identification

NEWSWORTHINESS THRESHOLD:
A story is only newsworthy if it meets AT LEAST ONE of these criteria:
- Involves death or violent crime (shootings, murders, attacks, etc.)
- Affects 500 or more people directly
- Costs or invests at least $1 million USD (or equivalent)
- Changes a law or regulation
- Redraws a political border
- Major scientific or technological achievement (space launch, medical breakthrough, new discovery)
- Humanitarian milestone (aid delivered, rescue success, disaster relief)
- Official statements or actions by heads of state/government (Presidents, Prime Ministers, etc.)
- Major economic indicators (GDP, unemployment rates, inflation data, housing market reports)
- International agreements, treaties, or diplomatic actions between nations
- Major natural disaster, pandemic, or public health emergency
If the story does NOT meet any threshold, return newsworthy: false.

OUTPUT FORMAT:
Return a JSON object with:
- "fact": The clean, factual sentence (or "SKIP")
- "confidence": Your confidence percentage (0-100) that this is purely factual
- "removed": Array of words/phrases you removed and why

EXAMPLES:

Input: "Tragic school shooting leaves community in shock as gunman opens fire"
Output: {"fact": "Shooting reported at school.", "confidence": 95, "removed": ["tragic", "leaves community in shock", "gunman"]}

Input: "Failed economic policy slammed by experts as inflation skyrockets"
Output: {"fact": "SKIP", "confidence": 100, "removed": ["entire headline - no verifiable facts without source data"]}

Input: "Earthquake measuring 6.2 strikes Chile, thousands evacuated"
Output: {"fact": "Earthquake measuring 6.2 struck Chile. Evacuations reported.", "confidence": 98, "removed": ["thousands - unverified count"]}

Input: "Historic peace deal signed between nations after brutal decade-long conflict"
Output: {"fact": "Peace agreement signed between [nations].", "confidence": 92, "removed": ["historic", "brutal", "decade-long"]}

Input: "Biden slams Republican lawmakers over controversial spending bill"
Output: {"fact": "President Biden criticized Republican lawmakers regarding spending bill.", "confidence": 90, "removed": ["slams", "controversial"], "notes": ["Added required title 'President' - titles are facts, omitting them is editorial"]}

Input: "Judge orders halt to immigration policy"
Output: {"fact": "Judge [Full Name] of the [Court Name] ruled to halt immigration policy.", "confidence": 85, "removed": ["orders"], "notes": ["Replaced 'orders' with 'ruled'; requires full judge name and court jurisdiction before publishing"]}

Input: "Federal judge blocks new environmental rule"
Output: {"fact": "Judge [Full Name] of the U.S. District Court for [District] ruled to block environmental regulation.", "confidence": 85, "removed": ["blocks"], "notes": ["Replaced 'blocks' with 'ruled to block'; requires full judge name and court before publishing"]}
"""
```

### 6.5 Confidence Threshold

- **≥85%**: Publish immediately
- **80-89%**: Queue for human review (but for MVP, just queue for next cycle)
- **<80%**: Discard and log
- **Any story that publishes with <85% triggers SMS alert**

### 6.6 Error Handling

```python
def process_with_claude(headline, source_id):
    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",  # Cost-optimized
            max_tokens=500,
            system=CLAUDE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"Process this headline: {headline}"}]
        )
        result = json.loads(response.content[0].text)

        if result["fact"] == "SKIP":
            log(f"SKIPPED: {headline} - no verifiable facts")
            return None

        if result["confidence"] < 80:
            log(f"LOW CONFIDENCE ({result['confidence']}%): {headline}")
            return None

        return {
            "fact": result["fact"],
            "confidence": result["confidence"],
            "source_id": source_id,
            "original": headline,
            "removed": result["removed"]
        }

    except Exception as e:
        log(f"CLAUDE API ERROR: {e}")
        return None  # Never publish unprocessed
```

### 6.7 Safe JSON Parsing

Claude may occasionally return malformed JSON. The `safe_parse_claude_json()` helper handles this gracefully:

1. **Try standard JSON parsing** (extract `{...}` from response)
2. **Try markdown code block extraction** (```json...```)
3. **Regex field extraction** (fallback for malformed responses)
4. **Return safe default** (e.g., `{"contradiction": false}`)

This ensures parsing failures never crash the system or block stories.

---

## 7. Verification Rules

### 7.1 Two Source Requirement

A story is ONLY published when:
1. **Two or more sources** report the same core fact
2. The sources have **different owners**
3. Claude has processed BOTH headlines
4. BOTH have confidence ≥85%

### 7.2 Similarity Matching

Stories are grouped by semantic similarity:
- Extract key entities: locations, names, numbers, actions
- Two stories match if they share 2+ key entities
- Use fuzzy matching for names (e.g., "President Biden" = "Biden" = "US President")

```python
def stories_match(story1, story2):
    """Returns True if two stories are about the same event."""
    entities1 = extract_entities(story1["fact"])
    entities2 = extract_entities(story2["fact"])

    # Must share at least 2 key entities
    shared = entities1.intersection(entities2)
    return len(shared) >= 2
```

### 7.3 The Twenty-Four Hour Rule

- When first source reports, story goes to `queue.json` with timestamp
- If no second source within **24 hours**, story is **dropped**
- No ghost stories. No "developing" placeholder.
- Either verified or deleted.

```python
def check_queue():
    """Remove stories older than 24 hours without verification."""
    now = time.time()
    three_hours = 3 * 60 * 60

    queue = load_queue()
    for story_hash, story in list(queue.items()):
        if now - story["first_seen"] > three_hours:
            log(f"EXPIRED (no 2nd source): {story['fact']}")
            del queue[story_hash]

    save_queue(queue)
```

### 7.4 Reliability-Based Conflict Resolution

When two sources verify the same event, they may report **different details** (e.g., different casualty counts, different dollar amounts). The system uses **reliability scores** to determine which version to publish.

#### Reliability Score Formula

```
reliability = source_rating × (confidence / 100)
```

- **source_rating**: The learned accuracy rating (0-10 scale, from 7.5)
- **confidence**: Claude's extraction confidence for this specific fact (0-100%)

#### Example

| Source | Rating | Confidence | Reliability |
|--------|--------|------------|-------------|
| Reuters | 9.8 | 95% | 9.31 |
| Times of India | 7.4 | 90% | 6.66 |

**Result:** Reuters' version is published (9.31 > 6.66)

#### Implementation

```python
def get_reliability_score(source_id: str, confidence: int) -> float:
    """Calculate reliability score for conflict resolution."""
    rating = get_learned_rating(source_id)
    return rating * (confidence / 100)

# During verification:
new_reliability = get_reliability_score(headline["source_id"], confidence)
queue_reliability = get_reliability_score(match["source_id"], match["confidence"])

if queue_reliability > new_reliability:
    best_fact = match["fact"]  # Use queued (higher-rated) source's version
else:
    best_fact = fact  # Use new source's version (tiebreaker: newer wins)
```

#### Key Points

- **Both sources still credited** — attribution shows both sources regardless of which fact version is used
- **Tiebreaker** — If reliability scores are equal, the newer source's version wins
- **Logging** — When a queued source beats a newer source, it's logged:
  `Preferring queued source (Reuters: 9.31) over new (TOI: 6.66)`

### 7.5 Source Rating Methodology

Source accuracy ratings are **evidence-based**, calculated from actual verification performance.

#### Formula

```
Rating = (verification_successes / (verification_successes + failures)) × 10
```

- **Verification Success:** Story from source A was verified by unrelated source B. BOTH sources receive +1 success.
- **Verification Failure:** Story expired from queue after 24 hours without second-source verification. Source receives +1 failure.

#### Display Format

| Data Points | Format | Example | Meaning |
|-------------|--------|---------|---------|
| 0 (no data) | `rating*` | `9.6*` | Editorial baseline, no observed data |
| 1-9 (cold start) | `rating* (n/m)` | `8.5* (3/10)` | Blended baseline + observed, insufficient data |
| 10+ (mature) | `rating (n/m)` | `9.4 (47/50)` | Pure evidence-based rating |

The asterisk (*) indicates "insufficient data, using editorial baseline".

#### Audit Trail

All rating events are logged to `data/ratings_audit.jsonl` (one JSON object per line):

```jsonl
{"timestamp":"2026-02-11T20:17:48Z","source_id":"ap","event":"success","fact_hash":"a1b2c3"}
{"timestamp":"2026-02-11T21:05:00Z","source_id":"guardian","event":"failure","fact_hash":"d4e5f6"}
```

This creates a legally defensible record. If challenged about a rating:
1. Show the audit trail with all verification events
2. Show the formula: `successes / total × 10`
3. Show the transparency indicator (asterisk for insufficient data)

#### Cold Start Behavior

- Day 1: All ratings display asterisk (no observed data)
- Week 1: High-volume sources (AP, BBC) accumulate data
- Month 1: Most sources reach 10+ data points, removing asterisk

#### Runtime Files

| File | Purpose |
|------|---------|
| `data/learned_ratings.json` | Current success/failure counts per source |
| `data/ratings_audit.jsonl` | Append-only audit trail of all rating events |

---

## 8. Breaking News Protocol

### 8.1 Speed vs. Accuracy

JTF News is **not first**. JTF News is **correct**.

When breaking news happens:
1. First source arrives → Queue (do not speak)
2. Wait for second source (could be 5 minutes, could be 24 hours)
3. Second source arrives → Verify owners are different
4. Publish merged fact

**Example timeline:**

```
08:00:00 - Reuters: "Shooting at Pennsylvania Avenue school, casualties unknown"
           → Queued. Silent.

08:05:00 - AP: "Active shooter at Pennsylvania Avenue school, police on scene"
           → Second source! Different owner! Verify...

08:05:05 - JTF publishes:
           "Pennsylvania Avenue school, shooting reported. Police attending."
           Sources: Reuters – 9.8, AP – 9.6
```

### 8.2 Prohibited Words in Breaking News

Never use:
- "active" (implies ongoing when we don't know)
- "tragic" (editorial)
- "terrified" (editorial)
- "brutal" (editorial)
- "horrific" (editorial)
- "breaking" (we don't use this label)
- "developing" (we don't use this label)
- "just in" (we don't use this label)

### 8.3 Updating Facts

If a third source adds new verified information:
- Add the new fact as a separate sentence
- Do not replace the original
- Both get said in the next loop cycle

```
First version:  "Pennsylvania Avenue school, shooting reported. Police attending."
After update:   "Pennsylvania Avenue school, shooting reported. Police attending. Three injured."
```

---

## 9. The 24-Hour Loop

### 9.1 Loop Structure

- **Starts:** Midnight GMT
- **Contains:** All verified stories from current day
- **Plays:** Each story once, in order of first publication
- **Repeats:** After last story, returns to first
- **Ends:** Midnight GMT (archive and reset)

### 9.2 Loop Timing

- Each story: ~10 seconds (read time) + 2 second pause
- 10 stories = ~2 minute loop
- 50 stories = ~10 minute loop
- Loop plays continuously until midnight

### 9.3 No Filler

- If no stories: silence (background visuals only, no audio)
- No "we'll be right back"
- No "stay tuned"
- No "still developing"
- Silence IS the content when there's nothing to say

### 9.4 Story Persistence

Same story can appear on multiple days:
- Day 1: "Earthquake struck Chile. 50 dead."
- Day 2: "Earthquake struck Chile. 127 dead." (if count updated)
- Day 3: (dropped if no new information)

This is not repetition. It's history.

### 9.5 Midnight Reset

At 00:00:00 GMT:
1. Archive current day's log to GitHub
2. Clear `daily_log.txt`
3. Clear `shown_hashes.txt`
4. Clear `current.txt` and `source.txt`
5. New day begins with silence

---

## 10. Lower Third Design

### 10.1 Visual Layout (HD: 1920x1080)

```
┌────────────────────────────────────────────────────────────────────┐
│                                                                    │
│                                                                    │
│                      (HD background visual)                        │
│                                                                    │
│                                                                    │
│                                                                    │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ Reuters – 9.8 · AP – 9.6                                     │ │ ← Source bar
│  ├──────────────────────────────────────────────────────────────┤ │
│  │                                                              │ │
│  │  Pennsylvania Avenue school, shooting reported.              │ │ ← Main text
│  │  Police attending. Three injured.                            │ │
│  │                                                              │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
     ↑                                                           ↑
   5% margin                                                  5% margin
```

### 10.2 Specifications

**Overall Container (Dark Glassmorphism):**
- Position: 8% from bottom of screen, 5% from left
- Width: 90% max
- Background: rgba(15, 23, 42, 0.75) - dark slate with blur
- Backdrop filter: blur(40px) saturate(180%)
- Border: 1px solid rgba(255, 255, 255, 0.15)
- Border radius: 16px
- Box shadow: layered depth effect

**Brand Tab:**
- Position: Sticks up from top-left of container
- Background: Gold gradient (rgba(212, 175, 55, 0.95) to rgba(170, 135, 35, 0.9))
- Font: Inter, 22px, 600 weight, dark text (#1a1a1a)
- Letter spacing: 4px
- Content: "JTF NEWS"

**Source Bar:**
- Background: Blue gradient (rgba(30, 64, 175, 0.7) to rgba(23, 37, 84, 0.8))
- Font: Inter, 28px, 600 weight, white, uppercase
- Letter spacing: 3px
- Padding: 18px 36px

**Main Text Area:**
- Font: Inter, 58px, 400 weight, white
- Line height: 1.45
- Padding: 36px 44px

**Animations:**
- Slide-in: 0.8 second ease-out with translateX
- Hold: Matches audio playback duration
- Slide-out: 0.8 second ease-out
- Gap between stories: 45 seconds

### 10.3 Responsive Text Duration

```javascript
function calculateDisplayTime(text) {
    // Average reading speed: 150 words per minute
    // Minimum display: 5 seconds
    // Add 0.5 seconds per 10 characters
    const baseTime = 5000; // 5 seconds
    const extraTime = Math.floor(text.length / 10) * 500;
    return Math.min(baseTime + extraTime, 15000); // Max 15 seconds
}
```

### 10.4 Story Freshness Handling

Stories are prioritized by how recently they were verified. This ensures viewers see the most timely news first without adding urgency indicators.

**Freshness Tiers:**

| Tier | Age | Weight | Behavior |
|------|-----|--------|----------|
| Fresh | < 6 hours | 3x | Plays most often, appears first |
| Medium | 6-12 hours | 2x | Moderate play frequency |
| Stale | 12-24 hours | 1x | Plays less often, appears later |

**Display Order Priority:**
- Stories are sorted by verification time (freshest first)
- Within each tier, stories are lightly shuffled for variety
- Ensures breaking news is heard before older stories

**Frequency Weighting:**
- Fresh stories have 3x probability of being selected
- Medium stories have 2x probability
- Stale stories have 1x probability
- Combined with 30-minute minimum replay interval

**Maximum Silence Duration:**
- MAX_SILENCE_DURATION: 15 minutes
- If no story has played for 15 minutes, the MIN_REPLAY_INTERVAL is bypassed
- This prevents extended dead air while honoring the "silence is default" philosophy
- A viewer will hear at least 4 stories per hour, even with a small verified story pool
- Philosophy preserved: We still prefer silence over filler; we just cap it at 15 minutes

**Timestamp Display:**
- Source bar shows time since verification
- Format: `Reuters – 9.8 · 2 hours ago`
- Provides context without drama or urgency

### 10.5 Viewer Support Messaging (PBS-Style)

JTF News displays periodic viewer support messages using the same lower-third infrastructure as news stories. These are silent, visual-only interstitials that alternate between two messages.

**Messages (alternating):**

| Message | Source Bar | Purpose |
|---------|------------|---------|
| "JTF News is supported by viewers like you." | Support · github.com/sponsors/larryseyer | Financial support |
| "Run JTF News as your screen saver." | Free · jtfnews.com/screensaver | Viewer engagement |

**Frequency:**
- Appears every 10 stories (~10 minutes at typical story rate)
- Messages alternate: sponsor → screensaver → sponsor → ...
- Same fade animation as news stories
- 5 second hold time (no audio)

**Configuration (config.json):**
```json
"sponsor": {
  "enabled": true,
  "frequency": 10,
  "tts_enabled": false,
  "messages": [
    {
      "message": "JTF News is supported by viewers like you.",
      "source_text": "Support · github.com/sponsors/larryseyer"
    },
    {
      "message": "Run JTF News as your screen saver.",
      "source_text": "Free · jtfnews.com/screensaver"
    }
  ]
}
```

**Design Constraints (Whitepaper Compliance):**
- No TTS (silent display only)
- No Alexa/voice assistant messaging (too intrusive when spoken)
- No animated graphics (violates calm aesthetic)
- No donation amounts or goals (creates urgency)
- No "please donate" language (begging)
- PBS-style acknowledgment, not advertisement

**Where Support Messaging Appears:**

| Surface | Implementation |
|---------|---------------|
| Lower-third overlay | Periodic interstitial every N stories |
| Screensaver | Same logic (inline JS) |
| RSS feed | Static channel description |
| Website | Support section on index.html |

---

## 11. Text-to-Speech

### 11.1 Voice Requirements

From the specification:
> "Calm female voice, northern English. Custom. Quiet."

**This is NON-NEGOTIABLE.** The voice quality defines the project aesthetic.

### 11.2 Primary: ElevenLabs API

**Why ElevenLabs:**
- Most realistic AI voices available
- Custom voice creation/cloning
- Fine control: pitch, speed, stability, clarity
- Simple Python SDK
- ~$5/month hobby tier

**Voice Settings:**
- Style: Calm, measured, neutral
- Accent: Northern English (or closest available)
- Speed: 0.9x (slightly slower than normal)
- Stability: 0.7 (consistent but not robotic)
- Clarity: 0.8 (clear enunciation)

**Implementation:**
```python
from elevenlabs import generate, set_api_key, Voice, VoiceSettings

def generate_tts(text):
    set_api_key(os.getenv("ELEVENLABS_API_KEY"))

    audio = generate(
        text=text,
        voice=Voice(
            voice_id="custom-jtf-voice",  # Created in ElevenLabs dashboard
            settings=VoiceSettings(
                stability=0.7,
                similarity_boost=0.8,
                style=0.3,
                use_speaker_boost=True
            )
        ),
        model="eleven_multilingual_v2"
    )

    with open("audio/current.wav", "wb") as f:
        f.write(audio)

    return True
```

### 11.3 Fallback: OpenAI TTS

If ElevenLabs unavailable:
- Model: "tts-1-hd"
- Voice: "nova" (calm female)
- Speed: 0.9

```python
from openai import OpenAI

def generate_tts_fallback(text):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    response = client.audio.speech.create(
        model="tts-1-hd",
        voice="nova",
        input=text,
        speed=0.9
    )

    response.stream_to_file("audio/current.wav")
    return True
```

### 11.4 Audio File Handling

- Format: WAV (uncompressed, OBS-compatible)
- Sample rate: 44100 Hz
- Channels: Mono
- OBS Media Source monitors `audio/current.wav`
- When file changes, OBS plays new audio

---

## 12. Twitter/X Behavior

### 12.1 Philosophy

> "Twitter is not for conversation. It is for a single sentence. We tweet the fact. We do not reply. We do not retweet. We do not like. It is a billboard. Not a bar. If someone shouts back, we stay quiet. We do not argue with the wind."

### 12.2 What We Do

- Tweet each verified story **once**
- Include source attribution
- Include hashtag #JTFNews

**Tweet format:**
```
Pennsylvania Avenue school, shooting reported. Police attending.

Sources: Reuters, AP

#JTFNews
```

### 12.3 What We Never Do

- ❌ Reply to any tweet
- ❌ Retweet anything
- ❌ Like any tweet
- ❌ Quote tweet
- ❌ Follow anyone
- ❌ DM anyone
- ❌ Engage with mentions
- ❌ Post threads
- ❌ Post images/video
- ❌ Use emoji

### 12.4 Implementation

```python
import tweepy

def tweet_story(story):
    """Tweet a verified story. Once. No engagement."""

    client = tweepy.Client(
        consumer_key=os.getenv("TWITTER_API_KEY"),
        consumer_secret=os.getenv("TWITTER_API_SECRET"),
        access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
        access_token_secret=os.getenv("TWITTER_ACCESS_SECRET")
    )

    sources = ", ".join([s.split(" – ")[0] for s in story["sources"]])

    tweet_text = f"""{story["fact"]}

Sources: {sources}

#JTFNews"""

    try:
        client.create_tweet(text=tweet_text)
        log(f"TWEETED: {story['fact'][:50]}...")
        return True
    except Exception as e:
        log(f"TWEET ERROR: {e}")
        return False
```

### 12.5 Duplicate Prevention

- Hash each story's fact text
- Store hashes in `shown_hashes.txt`
- Never tweet same fact twice in 24 hours
- Reset at midnight GMT

---

## 13. YouTube Stream Settings

### 13.1 Stream Configuration

**Title:** `JTF News – Live`

**Description:**
```
Facts only. No opinions.

Think of us as a very slow, very honest librarian.
We read everything, say nothing unless two other librarians agree,
and never raise our voice.

24/7 automated news. Verified facts only.

─────────────────────────────
SOURCE SCORES (Higher = Better)

On-stream: Accuracy | Bias (top 2 priorities)
• Accuracy: How often stories get verified by a second unrelated source
• Bias: How neutral the language is (10 = no editorialization removed)

Example: "Reuters 9.8|9.5" = 9.8 accuracy, 9.5 bias

Full scores (all 4) and ownership disclosure: jtfnews.com/sources
─────────────────────────────
```

**Category:** News & Politics

**Visibility:** Public

**Live Chat:** Disabled (or hidden)

**Comments:** Disabled

### 13.2 What We Never Do on YouTube

- ❌ Read chat
- ❌ Respond to chat
- ❌ Pin comments
- ❌ Add timestamps
- ❌ Add cards/end screens
- ❌ Use community posts
- ❌ Heart comments
- ❌ Add polls

> "It's a window, not a stage."

### 13.3 OBS Stream Settings

- Service: YouTube - RTMPS
- Server: Primary YouTube ingest server
- Stream Key: (from YouTube Studio)
- Output Resolution: 1920x1080 (HD)
- FPS: 30
- Encoder: x264 or NVENC
- Bitrate: 6000-8000 Kbps (for HD)
- Keyframe Interval: 2 seconds

---

## 14. Watchdog Alert System

### 14.1 Philosophy

> "A simple watchdog script. If the AI outputs anything with a confidence score below eighty-five percent, or if two consecutive sentences contradict each other, it pings your phone. One line: 'Alert: possible hallucination.' You get in the car, you log in, you hit stop. No committee. No press release. Just you."

### 14.2 Alert Triggers

**Critical (SMS immediately):**
1. Story published with confidence < 85%
2. Contradiction detected between two published sentences
3. Single-source story bypassed verification
4. Stream offline > 5 minutes
5. API costs exceed 80% of daily budget ($5)
6. Queue backup > 200 items or oldest item > 20 hours
7. 3 consecutive API failures (same service)

**Warning (log only):**
- API rate limit approaching
- Source website unreachable
- No new stories for 2 hours

### 14.2.1 Alert Throttling

To prevent SMS spam, alerts are throttled by type:

| Alert Type | Cooldown |
|------------|----------|
| `api_failure` | 1 hour |
| `credits_low` | 24 hours |
| `queue_backup` | 6 hours |
| `offline` | Until resolved |
| `contradiction` | None |

Implementation: `_alert_cooldowns` dict tracks last sent time per type.

### 14.3 SMS Implementation (Twilio)

```python
from twilio.rest import Client

def send_alert(message):
    """Send SMS alert to human operator."""

    client = Client(
        os.getenv("TWILIO_ACCOUNT_SID"),
        os.getenv("TWILIO_AUTH_TOKEN")
    )

    client.messages.create(
        body=f"JTF: {message}",
        from_=os.getenv("TWILIO_PHONE_NUMBER"),
        to=os.getenv("ALERT_PHONE_NUMBER")
    )

    log(f"ALERT SENT: {message}")
```

### 14.4 Alert Messages

Keep them short. One line. Actionable.

- `JTF: Confidence 84%` - Published story below threshold
- `JTF: Contradiction detected` - Logic failure
- `JTF: Single source published` - Verification bypass
- `JTF: Offline 5+ min` - Stream down
- `JTF: API error` - Claude/TTS/Twitter API failure

### 14.5 Human Response

When you receive an alert:
1. Log in to system
2. Check `data/daily_log.txt` for recent output
3. Kill stream if necessary (OBS stop)
4. Investigate
5. Fix or wait
6. Resume when confident

No escalation. No committee. One person. One button.

---

## 15. GitHub Archive Structure

### 15.1 Repository Structure

```
jtf-news-archive/
├── README.md
├── 2026/
│   ├── jtf-2026-02-10.txt.zip
│   ├── jtf-2026-02-11.txt.zip
│   └── ...
├── 2027/
│   └── ...
└── ...
```

### 15.2 README.md Content

```markdown
# JTF News Archive

Archives by year. One zip per day. Unzip, read, delete.

No edits. No comments. No mercy.

## Format

Each zip contains a single text file with all facts published that day.

Format per line:
```
[ISO timestamp] | [fact] | [sources]
```

## License

CC-BY-SA 4.0

## More Info

https://jtfnews.com (if exists)
```

### 15.3 Daily Archive File Format

Filename: `jtf-YYYY-MM-DD.txt`

Content:
```
2026-02-10T08:05:00Z | Pennsylvania Avenue school, shooting reported. Police attending. | Reuters – 9.8, AP – 9.6
2026-02-10T09:30:00Z | Earthquake measuring 6.2 struck Chile. Evacuations reported. | BBC – 9.4, France24 – 8.6
2026-02-10T14:15:00Z | Trade agreement signed between UK and Australia. | Guardian – 8.8, ABC AU – 9.0
```

### 15.4 Archive Implementation

```python
import zipfile
import subprocess
from datetime import datetime, timezone

def archive_daily():
    """Archive today's log to GitHub at midnight GMT."""

    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    year = now.strftime("%Y")

    log_file = "data/daily_log.txt"
    zip_name = f"jtf-{date_str}.txt.zip"
    zip_path = f"archive/{year}/{zip_name}"

    # Ensure year directory exists
    os.makedirs(f"archive/{year}", exist_ok=True)

    # Create zip
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write(log_file, f"jtf-{date_str}.txt")

    # Git commit and push
    subprocess.run(["git", "-C", "archive", "add", "."])
    subprocess.run(["git", "-C", "archive", "commit", "-m", f"Archive {date_str}"])
    subprocess.run(["git", "-C", "archive", "push"])

    log(f"ARCHIVED: {zip_name}")
```

### 15.5 Public Website (GitHub Pages)

The `gh-pages` branch serves the public-facing website at https://larryseyer.github.io/jtfnews/

**Files in `gh-pages-dist/`:**

| File | Purpose |
|------|---------|
| `index.html` | Landing page with live operational costs |
| `how-it-works.html` | Interactive guide with live story demo |
| `whitepaper.html` | Renders WhitePaper.md dynamically (single source of truth) |
| `screensaver.html` | Standalone screen saver version |
| `screensaver-setup.html` | Screen saver installation guide |
| `monitor.html` | Full operations dashboard |
| `feed.xml` | RSS feed of verified stories |
| `stories.json` | Current day's verified stories (synced from data/) |
| `monitor.json` | Live operational metrics (synced from data/) |

**Key Principle:** The whitepaper page fetches `WhitePaper.md` from the main branch at runtime, ensuring the public page always reflects the canonical source.

**Sync Mechanism:** `main.py` pushes `monitor.json` and `stories.json` to gh-pages after each cycle for live dashboard updates.

---

## 16. Launch Protocol

### 16.1 Philosophy

> "We begin when the code is ready. We begin when two sources report something. We begin with silence. And when the first true sentence arrives, we speak it. No fanfare. No launch party. Just on."

### 16.2 Pre-Launch Checklist

- [ ] All API keys configured and tested
- [ ] All 20 news sources verified reachable
- [ ] Claude API returning valid responses
- [ ] ElevenLabs voice created and tested
- [ ] Twitter account created (@JTFNews or similar)
- [ ] YouTube channel created
- [ ] OBS configured with all sources
- [ ] Test stream completed (unlisted)
- [ ] Alert system tested (send test SMS)
- [ ] GitHub archive repo created
- [ ] Background media folder populated with HD images

### 16.3 Launch Sequence

1. Start OBS
2. Verify YouTube stream key
3. Start `main.py`
4. Wait for first verified story
5. Click "Start Streaming" in OBS

That's it. No announcement. No countdown.

### 16.4 First Day

The first day will likely be quiet:
- System needs to build up queued stories
- Two sources need to match
- This might take minutes or hours

**This is correct behavior.** Silence is the product until we have verified facts.

---

## 17. File Specifications

### 17.1 config.json

```json
{
  "channel": {
    "id": "global",
    "name": "JTF News",
    "tagline": "Facts only. No opinions."
  },
  "sources": [
    // See Section 5 for full list
  ],
  "thresholds": {
    "min_confidence": 90,
    "min_sources": 2,
    "queue_timeout_hours": 24,
    "duplicate_window_hours": 24
  },
  "timing": {
    "scrape_interval_minutes": 30,  // Cost optimized (was 5)
    "archive_hour_utc": 0
  },
  "display": {
    "fade_in_ms": 1000,
    "hold_base_ms": 5000,
    "fade_out_ms": 1000,
    "gap_between_stories_ms": 2000
  }
}
```

### 17.2 .env

```bash
# Claude API (REQUIRED)
ANTHROPIC_API_KEY=sk-ant-api03-...

# ElevenLabs TTS (REQUIRED)
ELEVENLABS_API_KEY=...
ELEVENLABS_VOICE_ID=...

# OpenAI TTS (FALLBACK)
OPENAI_API_KEY=sk-...

# Twitter/X (REQUIRED)
TWITTER_API_KEY=...
TWITTER_API_SECRET=...
TWITTER_ACCESS_TOKEN=...
TWITTER_ACCESS_SECRET=...

# Twilio SMS Alerts (REQUIRED)
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+1...
ALERT_PHONE_NUMBER=+1...

# GitHub Archive (REQUIRED)
GITHUB_TOKEN=ghp_...
GITHUB_ARCHIVE_REPO=username/jtf-news-archive
```

### 17.3 .gitignore

```
# Environment
.env

# Runtime data
data/
audio/

# Python
__pycache__/
*.pyc
venv/

# OS
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/
```

### 17.4 requirements.txt

```
anthropic>=0.18.0
elevenlabs>=0.2.0
openai>=1.0.0
beautifulsoup4>=4.12.0
requests>=2.31.0
tweepy>=4.14.0
python-dotenv>=1.0.0
twilio>=8.0.0
```

### 17.5 main.py Structure

```python
#!/usr/bin/env python3
"""
JTF News - Just The Facts
Automated news system that reports only verified facts.

This is THE ONLY SCRIPT. It does everything:
- Scrapes headlines from 30 sources
- Processes with Claude AI to strip editorialization
- Verifies 2+ unrelated sources
- Writes output files for OBS
- Generates TTS audio
- Tweets each story once
- Archives daily to GitHub
- Sends SMS alerts on failures
"""

import os
import json
import time
import hashlib
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('jtf.log'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

def load_config():
    """Load configuration from config.json."""
    with open('config.json', 'r') as f:
        return json.load(f)

CONFIG = load_config()

# =============================================================================
# SCRAPING
# =============================================================================

def scrape_all_sources():
    """Scrape headlines from all configured sources."""
    pass  # Implementation

def scrape_source(source):
    """Scrape headlines from a single source."""
    pass  # Implementation

# =============================================================================
# CLAUDE PROCESSING
# =============================================================================

def process_with_claude(headline, source_id):
    """Process headline through Claude to strip editorialization."""
    pass  # Implementation

# =============================================================================
# VERIFICATION
# =============================================================================

def verify_two_sources(stories):
    """Group stories by similarity, require 2+ different owners."""
    pass  # Implementation

def stories_match(story1, story2):
    """Check if two stories are about the same event."""
    pass  # Implementation

def check_queue_expiry():
    """Remove stories older than 24 hours without verification."""
    pass  # Implementation

# =============================================================================
# OUTPUT
# =============================================================================

def write_current_story(story):
    """Write current story to data files for OBS."""
    pass  # Implementation

def update_daily_log(story):
    """Append story to daily log."""
    pass  # Implementation

# =============================================================================
# TEXT-TO-SPEECH
# =============================================================================

def generate_tts(text):
    """Generate TTS audio using ElevenLabs."""
    pass  # Implementation

def generate_tts_fallback(text):
    """Fallback TTS using OpenAI."""
    pass  # Implementation

# =============================================================================
# TWITTER
# =============================================================================

def tweet_story(story):
    """Tweet verified story. Once. No engagement."""
    pass  # Implementation

def is_duplicate_tweet(story):
    """Check if story was already tweeted today."""
    pass  # Implementation

# =============================================================================
# ARCHIVING
# =============================================================================

def archive_daily():
    """Archive today's log to GitHub at midnight GMT."""
    pass  # Implementation

def reset_daily_files():
    """Clear daily files for new day."""
    pass  # Implementation

# =============================================================================
# WATCHDOG
# =============================================================================

def send_alert(message):
    """Send SMS alert to human operator."""
    pass  # Implementation

def check_for_contradictions(story):
    """Check if new story contradicts recent output."""
    pass  # Implementation

# =============================================================================
# MAIN LOOP
# =============================================================================

def main():
    """Main loop - runs continuously."""
    log.info("JTF News starting...")

    while True:
        try:
            # Check if midnight - archive and reset
            if is_midnight_utc():
                archive_daily()
                reset_daily_files()

            # Scrape all sources
            headlines = scrape_all_sources()

            # Process each through Claude
            processed = []
            for headline, source_id in headlines:
                result = process_with_claude(headline, source_id)
                if result:
                    processed.append(result)

            # Check queue for expired stories
            check_queue_expiry()

            # Verify and publish
            verified = verify_two_sources(processed)
            for story in verified:
                # Check for contradictions
                if check_for_contradictions(story):
                    send_alert("Contradiction detected")
                    continue

                # Check confidence
                if story["confidence"] < 90:
                    send_alert(f"Confidence {story['confidence']}%")
                    continue

                # Publish
                write_current_story(story)
                generate_tts(story["fact"])
                update_daily_log(story)

                if not is_duplicate_tweet(story):
                    tweet_story(story)

            # Wait for next cycle
            time.sleep(CONFIG["timing"]["scrape_interval_minutes"] * 60)

        except Exception as e:
            log.error(f"Main loop error: {e}")
            send_alert("API error")
            time.sleep(60)  # Wait before retry

if __name__ == "__main__":
    main()
```

### 17.6 web/lower-third.html

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=1920, height=1080">
    <title>JTF News Lower Third</title>
    <link rel="stylesheet" href="lower-third.css">
</head>
<body>
    <div id="lower-third" class="hidden">
        <div id="source-bar"></div>
        <div id="fact-text"></div>
    </div>
    <script src="lower-third.js"></script>
</body>
</html>
```

### 17.7 web/lower-third.css

```css
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    width: 1920px;
    height: 1080px;
    background: transparent;
    overflow: hidden;
    font-family: Arial, sans-serif;
}

#lower-third {
    position: absolute;
    bottom: 5%;
    left: 5%;
    width: 90%;
    transition: opacity 1s ease-in-out;
}

#lower-third.hidden {
    opacity: 0;
}

#lower-third.visible {
    opacity: 1;
}

#source-bar {
    background: rgba(128, 128, 128, 0.8);
    padding: 10px 20px;
    font-size: 24px;
    color: white;
    text-shadow: 1px 1px 2px black;
}

#fact-text {
    background: rgba(0, 0, 0, 0.7);
    padding: 30px;
    font-size: 64px;
    color: white;
    line-height: 1.4;
    text-shadow: 2px 2px 4px black;
}
```

### 17.8 web/lower-third.js

```javascript
/**
 * JTF News Lower Third Display
 * Polls data files and displays facts with fade animation.
 */

const POLL_INTERVAL = 2000; // Check for new content every 2 seconds
const BASE_HOLD_TIME = 5000; // Base display time
const FADE_TIME = 1000; // Fade animation duration

let currentFact = '';
let isDisplaying = false;

async function fetchText(url) {
    try {
        const response = await fetch(url + '?t=' + Date.now()); // Cache bust
        if (response.ok) {
            return (await response.text()).trim();
        }
    } catch (e) {
        console.error('Fetch error:', e);
    }
    return '';
}

function calculateHoldTime(text) {
    // Longer text = longer display
    // ~150 words per minute reading speed
    const baseTime = BASE_HOLD_TIME;
    const extraTime = Math.floor(text.length / 10) * 500;
    return Math.min(baseTime + extraTime, 15000);
}

async function displayStory(fact, source) {
    if (isDisplaying) return;
    isDisplaying = true;

    const lowerThird = document.getElementById('lower-third');
    const sourceBar = document.getElementById('source-bar');
    const factText = document.getElementById('fact-text');

    // Set content
    sourceBar.textContent = source;
    factText.textContent = fact;

    // Fade in
    lowerThird.classList.remove('hidden');
    lowerThird.classList.add('visible');

    // Hold
    const holdTime = calculateHoldTime(fact);
    await new Promise(resolve => setTimeout(resolve, holdTime));

    // Fade out
    lowerThird.classList.remove('visible');
    lowerThird.classList.add('hidden');

    // Wait for fade
    await new Promise(resolve => setTimeout(resolve, FADE_TIME));

    isDisplaying = false;
}

async function poll() {
    const fact = await fetchText('../data/current.txt');
    const source = await fetchText('../data/source.txt');

    if (fact && fact !== currentFact) {
        currentFact = fact;
        await displayStory(fact, source);
    }
}

// Start polling
setInterval(poll, POLL_INTERVAL);
poll(); // Initial check
```

### 17.9 README.md

```markdown
# JTF News

**Just The Facts.**

> Think of us as a very slow, very honest librarian.
> We read everything, say nothing unless two other librarians agree,
> and never raise our voice.

## What This Is

An automated news stream that reports only verified facts:
- Scrapes 20 news sources
- Uses Claude AI to strip ALL editorialization
- Requires 2+ unrelated sources for verification
- Streams 24/7 to YouTube with calm visuals and TTS
- Tweets each story once (no engagement)
- Archives daily to GitHub

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and fill in API keys:
   - Anthropic (Claude)
   - ElevenLabs (TTS)
   - Twitter/X
   - Twilio (SMS alerts)
   - GitHub

3. Configure OBS:
   - Add Image Slideshow source → `media/` folder
   - Add Browser Source → `web/lower-third.html` (1920x1080)
   - Add Media Source → `audio/current.wav`
   - Configure YouTube stream

4. Add HD backgrounds to `media/` folder

5. Run:
   ```bash
   python main.py
   ```

6. Start OBS stream

## Files

- `main.py` - The only script. Does everything.
- `config.json` - News sources and settings
- `web/` - OBS browser overlay
- `data/` - Runtime data (gitignored)
- `audio/` - TTS output (gitignored)
- `media/` - HD backgrounds (user-provided)

## License

Code: MIT
Output: CC-BY-SA 4.0

## More

See `SPECIFICATION.md` for complete technical documentation.
```

---

## 18. Constraints and Ethics

### 18.1 Hard Rules (Never Break)

1. **Never publish without 2+ sources from different owners**
2. **Never publish with confidence < 85%**
3. **Never use emotional or loaded language**
4. **Never engage on Twitter (no replies, likes, retweets)**
5. **Never respond to YouTube comments/chat**
6. **Never publish unprocessed (non-Claude-filtered) text**
7. **Always respect robots.txt**
8. **Delete raw scraped data after 7 days**
9. **Archive daily to public GitHub**

### 18.2 Content Standards

**We report:**
- Deaths if verified count available
- Locations if specific
- Actions if verifiable
- Numbers if sourced
- People with proper titles (President, Senator, Governor, etc.) - never bare last names

**We never report:**
- Motives unless stated by officials
- Speculation about outcomes
- Editorial characterizations
- Unverified claims
- Single-source stories

### 18.3 Licensing

- **Code:** MIT License
- **Output (published facts):** CC-BY-SA 4.0

Anyone can use, share, adapt our output with attribution.

### 18.4 Transparency

- All code is open source
- All archives are public
- All sources are disclosed
- All ownership data is visible

### 18.5 Corrections & Retractions

When a fact passes the two-source test but is later proven false:

1. **Correction Timing**: A correction is issued within the next update cycle
2. **No Silent Deletion**: The original item is marked as corrected in the archive, never silently deleted
3. **Full Retractions**: If the error is fundamental, a full retraction is issued with explanation
4. **Equal Prominence**: Corrections are given the same prominence as the original item
5. **Public Log**: A running corrections log is maintained publicly on GitHub

We do not bury mistakes. We name them.

**Implementation:**
- Corrections file: `data/corrections.json` (local) and `gh-pages-dist/corrections.json` (public)
- Archive entries marked with `[CORRECTED]` prefix when applicable
- Correction tweets reference the original story

---

## 19. Verification Checklist

After implementation, verify each item:

### 19.1 Core Functionality

- [ ] `python main.py` starts without errors
- [ ] Scrapes at least 25/30 sources successfully
- [ ] Claude API processes headlines correctly
- [ ] Stories with <85% confidence are rejected
- [ ] Single-source stories are queued, not published
- [ ] Two-source stories are published
- [ ] Different-owner verification works
- [ ] 24-hour queue expiry works

### 19.2 Output Files

- [ ] `data/current.txt` updates with new stories
- [ ] `data/source.txt` shows correct attribution
- [ ] `data/daily_log.txt` accumulates stories
- [ ] `data/shown_hashes.txt` prevents duplicates
- [ ] `audio/current.wav` generates correctly

### 19.3 OBS Integration

- [ ] Browser source shows lower third
- [ ] Fade in/out animations work
- [ ] Text is readable over backgrounds
- [ ] Audio plays when story changes
- [ ] Image slideshow rotates backgrounds
- [ ] Stream to YouTube works

### 19.4 External Services

- [ ] Twitter posts stories correctly
- [ ] Twitter never replies/likes/retweets
- [ ] SMS alerts arrive on failures
- [ ] GitHub archive commits daily

### 19.5 Edge Cases

- [ ] No stories = silence (no errors)
- [ ] API failure = alert sent, no crash
- [ ] Invalid headline = skipped cleanly
- [ ] Duplicate story = not re-tweeted
- [ ] Midnight = archive + reset works

---

## 20. Future Directions

### 20.1 The Channel Concept

JTF News Global is the first implementation of the JTF methodology. The architecture supports future community-specific channels without code changes.

A **channel** is:
- A distinct set of news sources
- A relevance threshold appropriate to its community
- Its own branding (JTF Local, JTF Sports, etc.)
- Its own YouTube stream and Twitter account
- The same verification methodology

### 20.2 What Remains Universal

All channels share:
- Two-source verification from different owners
- Claude AI editorialization stripping
- Confidence threshold (≥85%)
- No engagement policy
- Calm presentation aesthetic
- Public archiving
- 501(c) non-profit operation

### 20.3 What Varies by Channel

| Element | Configured Per Channel |
|---------|----------------------|
| `sources[]` | Different news outlets per domain |
| `thresholds.relevance` | Community-appropriate definition |
| `branding.name` | "JTF Sports", "JTF [City]", etc. |
| `branding.tagline` | Domain-specific version of mission |
| `social.twitter_handle` | @JTFSports, @JTFLocal, etc. |
| `social.youtube_channel` | Separate stream per channel |
| `media/` folder | Domain-appropriate imagery |

### 20.4 Architecture Readiness

The current implementation already supports this through `config.json`:

```json
{
  "channel": {
    "id": "global",
    "name": "JTF News",
    "tagline": "Facts only. No opinions.",
    "description": "Global news verification"
  },
  "sources": [...],
  "thresholds": {...}
}
```

Future channels would be separate `config.json` files or a multi-channel configuration structure. No core code changes required.

### 20.5 Community Ownership

Channels are public services, not products:
- No licensing fees
- No franchise model
- Methodology is freely shared
- Communities may fork and adapt
- Attribution appreciated, not required
- CC-BY-SA applies to methodology documentation

### 20.6 Not Planned for MVP

The following are documented for future consideration only:
- Multi-channel orchestration
- Shared source pools across channels
- Cross-channel deduplication
- Unified archive structure
- Channel discovery/directory

The MVP focuses solely on JTF News Global. This section exists to ensure architectural decisions do not preclude expansion.

---

## End of Specification

**Total files to create:** 8
**Total lines of code:** ~500
**Total dependencies:** 8

This specification is complete. Any AI or developer following this document should be able to build JTF News with zero ambiguity.

*Last updated: February 2026*
