# JTF News — The Complete Build Prompt
## The Only Document You Need

---

> **For the ten-year-old:**
> "Think of us as a very slow, very honest librarian. We read everything, say nothing unless two other librarians agree, and never raise our voice."

> **For everyone else:**
> "Facts only. No opinions."

---

## PART 1: THE MISSION

### What is News?

A verifiable event, within the last twenty-four hours, that affects five hundred people or more, costs at least one million US dollars, changes a law, or redraws a border. Nothing less. Nothing more.

### What We Do

We do not editorialise. We state what happened, where, when, and—when known—how many. Nothing more.

### What We Build

A 24/7 automated news stream that:
- Scrapes headlines from 20 public news sources
- Uses Claude AI to strip ALL editorialization, bias, and opinion
- Requires 2+ unrelated sources (different owners) for verification
- Streams via OBS to YouTube with calm 4K visuals and natural TTS voice
- Tweets each story once to X (no engagement)
- Archives daily logs to GitHub at midnight GMT
- Alerts a human via SMS if anything goes wrong

### The Core Principle

**SIMPLICITY = STABILITY**

Always look for the simplest solution to any problem—it will ALWAYS be the most stable. This code needs to run FOREVER. Every line we don't write is a line that can't break.

---

## PART 2: WHAT WE NEVER DO

Read this section carefully. These are hard rules that cannot be broken.

### Never (Content)
- Publish without 2+ sources from different owners
- Publish with confidence < 85%
- Use emotional or loaded language ("tragic", "brutal", "horrific", "shocking")
- Use urgency words ("BREAKING", "developing", "just in", "active")
- Speculate on motives
- Report single-source stories
- Publish unprocessed (non-Claude-filtered) text

### Never (Twitter/X)
- Reply to any tweet
- Retweet anything
- Like any tweet
- Quote tweet
- Follow anyone
- DM anyone
- Post threads
- Use emoji

### Never (YouTube)
- Read chat
- Respond to chat
- Pin comments
- Add timestamps
- Heart comments
- Use community posts

### Never (Technical)
- Use APIs for news (scraping only)
- Violate robots.txt
- Store raw data longer than 7 days
- Create a database (plain text files only)

---

## PART 3: ARCHITECTURE

### Let OBS Do the Heavy Lifting

**OBS handles natively (no custom code):**
- Background image/video rotation → Image Slideshow source
- Video backgrounds → Media Source
- Audio playback → Media Source for TTS files
- Layer compositing → Scene with layers
- Streaming to YouTube → Built-in RTMP

**We only write:**
- One Python script (~400 lines)
- One HTML overlay (~20 lines)
- One CSS file (~30 lines)
- One JS file (~50 lines)

**Total: ~500 lines of code. 8 files.**

### System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         OBS STUDIO                               │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Scene: JTF News Live                                     │    │
│  │  ├─ Layer 1: Image Slideshow (media/ folder)            │    │
│  │  │   └─ Random, 50s interval, crossfade, 4K             │    │
│  │  ├─ Layer 2: Browser Source (lower-third.html)          │    │
│  │  │   └─ 3840x2160, transparent background               │    │
│  │  └─ Layer 3: Media Source (audio/current.wav)           │    │
│  │      └─ Plays TTS, restarts on file change              │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                   │
│                              ▼                                   │
│                    YouTube RTMP Stream                           │
│                   "JTF News – Live"                              │
└─────────────────────────────────────────────────────────────────┘
                               ▲
                               │ writes to
┌─────────────────────────────────────────────────────────────────┐
│                        main.py                                   │
│                                                                  │
│  Scrape → Claude AI → Verify 2 Sources → Output Files           │
│                                              │                   │
│                              ┌───────────────┼───────────────┐  │
│                              ▼               ▼               ▼  │
│                      data/current.txt  audio/current.wav   Tweet │
│                                                                  │
│  Watchdog ──→ SMS Alert (Twilio) if confidence <85% or error   │
│                                                                  │
│  Midnight ──→ Archive to GitHub (year/jtf-YYYY-MM-DD.txt.zip)  │
└─────────────────────────────────────────────────────────────────┘
```

---

## PART 4: FOLDER STRUCTURE

```
/Users/larryseyer/JTFNews/
├── main.py                 # THE ONLY SCRIPT - runs continuously
├── config.json             # News sources, thresholds, settings
├── .env                    # API keys (GITIGNORED)
├── .gitignore              # Ignores .env, data/, audio/
├── requirements.txt        # Python dependencies (8 packages)
├── SPECIFICATION.md        # Complete technical specification
├── PromptStart.md          # This document
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
└── media/                  # 4K backgrounds (user-provided)
    └── (serene images: clouds, waves, fields, stars)
```

---

## PART 5: THE 20 NEWS SOURCES

Each must have different ownership for verification purposes.

| ID | Name | Owner | Rating |
|----|------|-------|--------|
| reuters | Reuters | Thomson Reuters Corporation | 9.8 |
| ap | Associated Press | AP Cooperative | 9.6 |
| bbc | BBC News | British Broadcasting Corporation | 9.4 |
| npr | NPR | National Public Radio (nonprofit) | 9.2 |
| guardian | The Guardian | Scott Trust Limited | 8.8 |
| aljazeera | Al Jazeera English | Al Jazeera Media Network (Qatar) | 8.5 |
| france24 | France 24 | France Médias Monde | 8.6 |
| dw | Deutsche Welle | German Federal Government | 8.7 |
| cbc | CBC News | Canadian Broadcasting Corporation | 9.0 |
| abc_au | ABC News Australia | Australian Broadcasting Corporation | 9.0 |
| independent | The Independent | Lebedev family | 7.8 |
| sky | Sky News | Comcast (Sky Group) | 8.2 |
| pbs | PBS NewsHour | Public Broadcasting Service | 9.1 |
| euronews | Euronews | Alpac Capital (Portugal) | 8.0 |
| toi | Times of India | Bennett Coleman & Co. Ltd. | 7.5 |
| scmp | South China Morning Post | Alibaba Group | 7.8 |
| globe | The Globe and Mail | Woodbridge Company | 8.4 |
| irish | Irish Times | Irish Times Trust | 8.5 |
| straits | The Straits Times | Singapore Press Holdings | 7.6 |
| hindustan | Hindustan Times | HT Media Ltd. | 7.4 |

**Ownership Verification Rule:**
Two sources must have DIFFERENT owners to count as verification.
- Reuters + AP = valid (different owners) ✓
- BBC + BBC World = invalid (same owner) ✗

---

## PART 6: CLAUDE AI INTEGRATION

### The Prompt

```
You are a fact extraction system for JTF News. Your ONLY job is to strip ALL editorialization, bias, and opinion from news headlines and return pure facts.

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
3. Remove ALL speculation and attribution of motive
4. Remove ALL adjectives that convey judgment
5. Keep numbers, locations, names, and actions
6. Use present tense for ongoing events
7. Maximum ONE sentence
8. If the headline contains NO verifiable facts, return "SKIP"

OUTPUT FORMAT:
Return a JSON object with:
- "fact": The clean, factual sentence (or "SKIP")
- "confidence": Your confidence percentage (0-100) that this is purely factual
- "removed": Array of words/phrases you removed and why
```

### Confidence Thresholds
- ≥85%: Publish immediately
- 75-84%: Queue for next cycle
- <75%: Discard and log
- Any <85% that publishes: triggers SMS alert

### Model
Use `claude-sonnet-4-20250514` for cost/quality balance.
If API fails, queue story for next cycle. NEVER publish unprocessed text.

---

## PART 7: VERIFICATION RULES

### Two Source Requirement

A story is ONLY published when:
1. Two or more sources report the same core fact
2. The sources have different owners
3. Claude has processed BOTH headlines
4. BOTH have confidence ≥85%

### The Six-Hour Rule

- First source reports → Story goes to `queue.json` with timestamp
- No second source within 6 hours → Story is DROPPED
- No ghost stories. No "developing" placeholder.
- Either verified or deleted.

### Similarity Matching

Stories match if they share 2+ key entities (locations, names, numbers, actions).
Use fuzzy matching for names ("President Biden" = "Biden" = "US President").

---

## PART 8: BREAKING NEWS PROTOCOL

JTF News is NOT first. JTF News is CORRECT.

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

**Prohibited words in breaking news:**
- "active" (implies ongoing when we don't know)
- "tragic", "terrified", "brutal", "horrific" (editorial)
- "breaking", "developing", "just in" (we don't use these labels)

---

## PART 9: THE 24-HOUR LOOP

### Structure
- **Starts:** Midnight GMT
- **Contains:** All verified stories from current day
- **Plays:** Each story once, in order of first publication
- **Repeats:** After last story, returns to first
- **Ends:** Midnight GMT (archive and reset)

### Timing
- Each story: ~10 seconds (read time) + 2 second pause
- 10 stories = ~2 minute loop
- 50 stories = ~10 minute loop

### No Filler
If no stories: silence. Background visuals continue. Voice says nothing.
This is correct behavior. Silence IS the product when there's nothing verified to say.

### Midnight Reset
At 00:00:00 GMT:
1. Archive current day's log to GitHub
2. Clear all daily files
3. New day begins with silence

---

## PART 10: LOWER THIRD DESIGN

### Visual Layout (4K: 3840x2160)

```
┌────────────────────────────────────────────────────────────────────┐
│                                                                    │
│                      (4K background visual)                        │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ Reuters – 9.8 · AP – 9.6                    (grey bar)       │ │
│  ├──────────────────────────────────────────────────────────────┤ │
│  │  Pennsylvania Avenue school, shooting reported.              │ │
│  │  Police attending.                          (white text)     │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
     ↑                                                           ↑
   5% margin                                                  5% margin
```

### Specifications

**Source Bar:**
- Background: rgba(128, 128, 128, 0.8)
- Font: Arial, 24px, white
- Position: 5% from bottom

**Main Text:**
- Background: rgba(0, 0, 0, 0.7)
- Font: Arial, 64px, white
- Text shadow: 2px 2px 4px black

**Animations:**
- Fade in: 1 second
- Hold: 5-15 seconds (based on text length)
- Fade out: 1 second
- Gap between stories: 2 seconds

---

## PART 11: TEXT-TO-SPEECH

### Voice Requirements

"Calm female voice, northern English. Custom. Quiet."

This is NON-NEGOTIABLE. The voice quality defines the project aesthetic.

### Primary: ElevenLabs API

```python
from elevenlabs import generate, Voice, VoiceSettings

audio = generate(
    text=text,
    voice=Voice(
        voice_id="custom-jtf-voice",
        settings=VoiceSettings(
            stability=0.7,
            similarity_boost=0.8,
            style=0.3
        )
    ),
    model="eleven_multilingual_v2"
)
```

### Fallback: OpenAI TTS
- Model: "tts-1-hd"
- Voice: "nova" (calm female)
- Speed: 0.9

---

## PART 12: TWITTER/X BEHAVIOR

### Philosophy

"Twitter is not for conversation. It is for a single sentence. We tweet the fact. We do not reply. We do not retweet. We do not like. It is a billboard. Not a bar. If someone shouts back, we stay quiet. We do not argue with the wind."

### Tweet Format

```
Pennsylvania Avenue school, shooting reported. Police attending.

Sources: Reuters, AP

#JTFNews
```

One tweet per verified story. No engagement. Ever.

---

## PART 13: YOUTUBE STREAM

### Settings

- **Title:** `JTF News – Live`
- **Description:** `Facts only. No opinions.`
- **Chat:** Disabled
- **Comments:** Disabled
- **Resolution:** 3840x2160 (4K)
- **Bitrate:** 20000-25000 Kbps

> "It's a window, not a stage."

---

## PART 14: WATCHDOG ALERT SYSTEM

### Philosophy

"A simple watchdog script. If the AI outputs anything with a confidence score below eighty-five percent, or if two consecutive sentences contradict each other, it pings your phone. One line: 'Alert: possible hallucination.' You get in the car, you log in, you hit stop. No committee. No press release. Just you."

### Alert Triggers (SMS immediately)

1. Story published with confidence < 85%
2. Contradiction detected between two published sentences
3. Single-source story bypassed verification
4. Stream offline > 5 minutes

### Alert Messages

Keep them short. One line.

- `JTF: Confidence 84%`
- `JTF: Contradiction detected`
- `JTF: Single source published`
- `JTF: Offline 5+ min`
- `JTF: API error`

### Human Response

See message → Log in → Check → Kill if needed → Done.
No escalation. No committee. One person. One button.

---

## PART 15: GITHUB ARCHIVE

### Structure

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

### Archive README

```
# JTF News Archive

Archives by year. One zip per day. Unzip, read, delete.

No edits. No comments. No mercy.
```

### Daily File Format

```
2026-02-10T08:05:00Z | Pennsylvania Avenue school, shooting reported. | Reuters – 9.8, AP – 9.6
2026-02-10T09:30:00Z | Earthquake measuring 6.2 struck Chile. | BBC – 9.4, France24 – 8.6
```

---

## PART 16: FILES TO CREATE

### 1. requirements.txt

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

### 2. .env

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

### 3. .gitignore

```
.env
data/
audio/
__pycache__/
*.pyc
venv/
.DS_Store
.vscode/
.idea/
```

### 4. config.json

Complete JSON with all 20 sources, each containing:
- id, name, url, rss, scrape_selector
- owner, country, type, default_rating

Plus thresholds:
```json
{
  "thresholds": {
    "min_confidence": 90,
    "min_sources": 2,
    "queue_timeout_hours": 6,
    "duplicate_window_hours": 24
  },
  "timing": {
    "scrape_interval_minutes": 5,
    "archive_hour_utc": 0
  }
}
```

### 5. main.py

Single Python script that:
- Scrapes headlines from 20 sources (respecting robots.txt)
- Sends each to Claude API for fact extraction
- Verifies 2+ sources with different owners
- Checks 6-hour queue expiry
- Writes to data/current.txt and data/source.txt
- Generates TTS via ElevenLabs → audio/current.wav
- Updates daily_log.txt
- Tweets once per story
- At midnight GMT: archives to GitHub, resets files
- Sends SMS alerts on errors via Twilio
- Runs in infinite loop

### 6. web/lower-third.html

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=3840, height=2160">
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

### 7. web/lower-third.css

```css
* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    width: 3840px;
    height: 2160px;
    background: transparent;
    font-family: Arial, sans-serif;
}

#lower-third {
    position: absolute;
    bottom: 5%;
    left: 5%;
    width: 90%;
    transition: opacity 1s ease-in-out;
}

#lower-third.hidden { opacity: 0; }
#lower-third.visible { opacity: 1; }

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

### 8. web/lower-third.js

```javascript
const POLL_INTERVAL = 2000;
let currentFact = '';
let isDisplaying = false;

async function fetchText(url) {
    try {
        const r = await fetch(url + '?t=' + Date.now());
        return r.ok ? (await r.text()).trim() : '';
    } catch { return ''; }
}

function holdTime(text) {
    return Math.min(5000 + Math.floor(text.length / 10) * 500, 15000);
}

async function displayStory(fact, source) {
    if (isDisplaying) return;
    isDisplaying = true;

    document.getElementById('source-bar').textContent = source;
    document.getElementById('fact-text').textContent = fact;

    const el = document.getElementById('lower-third');
    el.classList.remove('hidden');
    el.classList.add('visible');

    await new Promise(r => setTimeout(r, holdTime(fact)));

    el.classList.remove('visible');
    el.classList.add('hidden');

    await new Promise(r => setTimeout(r, 1000));
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

setInterval(poll, POLL_INTERVAL);
poll();
```

### 9. README.md

```markdown
# JTF News

**Just The Facts.**

> Think of us as a very slow, very honest librarian.
> We read everything, say nothing unless two other librarians agree,
> and never raise our voice.

## Setup

1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env`, fill in API keys
3. Configure OBS with sources from `web/` and `media/`
4. `python main.py`
5. Start OBS stream

## License

Code: MIT | Output: CC-BY-SA 4.0

See `SPECIFICATION.md` for complete technical documentation.
```

---

## PART 17: LAUNCH PROTOCOL

### Philosophy

"We begin when the code is ready. We begin when two sources report something. We begin with silence. And when the first true sentence arrives, we speak it. No fanfare. No launch party. Just on."

### Pre-Launch Checklist

- [ ] All API keys configured and tested
- [ ] All 20 news sources verified reachable
- [ ] Claude API returning valid responses
- [ ] ElevenLabs voice created and tested
- [ ] Twitter account created
- [ ] YouTube channel created
- [ ] OBS configured with all sources
- [ ] Test stream completed (unlisted)
- [ ] Alert system tested (send test SMS)
- [ ] GitHub archive repo created
- [ ] Background media folder populated with 4K images

### Launch Sequence

1. Start OBS
2. Verify YouTube stream key
3. Start `python main.py`
4. Wait for first verified story
5. Click "Start Streaming" in OBS

That's it. No announcement. No countdown.

---

## PART 18: VERIFICATION CHECKLIST

After implementation, verify EVERY item:

### Core Functionality
- [ ] `python main.py` starts without errors
- [ ] Scrapes at least 15/20 sources successfully
- [ ] Claude API processes headlines correctly
- [ ] Stories with <85% confidence are rejected
- [ ] Single-source stories are queued, not published
- [ ] Two-source stories are published
- [ ] Different-owner verification works
- [ ] 6-hour queue expiry works

### Output Files
- [ ] `data/current.txt` updates with new stories
- [ ] `data/source.txt` shows correct attribution
- [ ] `data/daily_log.txt` accumulates stories
- [ ] `data/shown_hashes.txt` prevents duplicates
- [ ] `audio/current.wav` generates correctly

### OBS Integration
- [ ] Browser source shows lower third
- [ ] Fade in/out animations work
- [ ] Text is readable over backgrounds
- [ ] Audio plays when story changes
- [ ] Image slideshow rotates backgrounds
- [ ] Stream to YouTube works

### External Services
- [ ] Twitter posts stories correctly
- [ ] Twitter never replies/likes/retweets
- [ ] SMS alerts arrive on failures
- [ ] GitHub archive commits daily

### Edge Cases
- [ ] No stories = silence (no errors)
- [ ] API failure = alert sent, no crash
- [ ] Invalid headline = skipped cleanly
- [ ] Duplicate story = not re-tweeted
- [ ] Midnight = archive + reset works

---

## PART 19: CONSTRAINTS SUMMARY

### Hard Rules (Never Break)

1. Never publish without 2+ sources from different owners
2. Never publish with confidence < 85%
3. Never use emotional or loaded language
4. Never engage on Twitter (no replies, likes, retweets)
5. Never respond to YouTube comments/chat
6. Never publish unprocessed text
7. Always respect robots.txt
8. Delete raw scraped data after 7 days
9. Archive daily to public GitHub
10. Human can kill stream with one button if AI hallucinates

### Licensing

- **Code:** MIT License
- **Output:** CC-BY-SA 4.0

---

## END OF PROMPT

**Total files to create:** 8
**Total lines of code:** ~500
**Total dependencies:** 8

This document is complete. Any AI following this prompt should be able to build JTF News with zero ambiguity and total confidence.

**Remember:**
- If we stay boring enough, we might just change the world.
- Facts are dying. Silence is louder.
- We do not argue with the wind.

---

*Version 1.0 | February 2026*
*"Just the facts. Nothing more."*
