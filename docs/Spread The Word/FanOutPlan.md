# JTF News — Fan-Out Distribution Plan

**"We tweet once. We never reply."** — JTF Whitepaper, Section 23

This document defines every free distribution channel for JTF News, the automation architecture to drive them, and step-by-step Claude Code implementation instructions.

---

## Architecture Overview

JTF News already produces two outputs every 30 minutes:

1. **Text** — The fact-checked, adjective-stripped news text
2. **Audio** — ElevenLabs-generated voice read (calm, female, northern English)

The fan-out strategy takes these two artifacts and pushes them to every channel simultaneously. One pipeline. One post per channel. No engagement. No replies. No analytics.

```
┌─────────────┐
│  JTF Engine  │
│  (text+audio)│
└──────┬───────┘
       │
       ▼
┌─────────────┐
│  fan-out.js  │  (or fan-out.py)
└──────┬───────┘
       │
       ├──▶ Bluesky     (text)
       ├──▶ Mastodon    (text)
       ├──▶ Telegram    (text)
       ├──▶ Threads     (text)
       ├──▶ Podcast RSS (audio)
       ├──▶ YouTube     (already live)
       └──▶ RSS Feed    (already live)
```

---

## Channel Details

### 1. Bluesky

**Why:** Open protocol, free API, no algorithm manipulation, audience that values signal over noise. This is the X replacement.

**Whitepaper alignment:** Post once, never reply. No engagement. CC-BY-SA compatible.

**API:** AT Protocol — `https://bsky.social/xrpc/`

**Account setup:**
- Create account at https://bsky.app
- Generate an App Password (Settings → App Passwords)
- Store handle and app password as environment variables

**Rate limits:** 1,667 creates per hour (more than enough for every-30-minute posts)

**Character limit:** 300 characters per post. For longer fact cycles, use a thread (multiple posts linked together) or post a summary with a link back to the JTF site.

**Implementation — Claude Code prompt:**

```
Create a Node.js module `channels/bluesky.js` that:
1. Authenticates with the Bluesky AT Protocol using env vars
   BLUESKY_HANDLE and BLUESKY_APP_PASSWORD
2. Exports an async function postToBluesky(text, link) that:
   - Creates a session via com.atproto.server.createSession
   - If text > 300 chars, truncates with "..." and appends the link
   - Posts via com.atproto.repo.createRecord with app.bsky.feed.post
   - Includes a link facet pointing to the full story on larryseyer.github.io/jtfnews
   - Returns the post URI on success
   - Logs errors but never throws (fan-out must not halt on one channel failure)
3. No external dependencies — use native fetch
```

**Environment variables:**
```bash
export BLUESKY_HANDLE="jtfnews.bsky.social"
export BLUESKY_APP_PASSWORD="xxxx-xxxx-xxxx-xxxx"
```

---

### 2. Mastodon

**Why:** Federated, no algorithm, posts propagate across the entire fediverse. Audience values transparency.

**Whitepaper alignment:** Post once, never reply. Open protocol matches open methodology.

**Instance options (free):**
- `mastodon.social` — largest general instance
- `newsie.social` — news-focused instance
- Self-hosted later if desired (requires VPS)

**API:** REST — `https://{instance}/api/v1/`

**Account setup:**
- Create account on chosen instance
- Go to Preferences → Development → New Application
- Scopes needed: `write:statuses` only
- Save the access token

**Character limit:** 500 characters (default, varies by instance)

**Implementation — Claude Code prompt:**

```
Create a Node.js module `channels/mastodon.js` that:
1. Uses env vars MASTODON_INSTANCE and MASTODON_ACCESS_TOKEN
2. Exports an async function postToMastodon(text, link) that:
   - Posts to /api/v1/statuses with status text
   - If text > 500 chars, truncates and appends link
   - Sets visibility to "public"
   - Returns the status ID on success
   - Logs errors but never throws
3. No external dependencies — use native fetch
```

**Environment variables:**
```bash
export MASTODON_INSTANCE="https://mastodon.social"
export MASTODON_ACCESS_TOKEN="your-access-token"
```

---

### 3. Telegram Broadcast Channel

**Why:** Pure push notification. No algorithm. No comments (configurable). Subscribers get the fact and nothing else. Possibly the single most aligned channel with the whitepaper.

**Whitepaper alignment:** Perfect. Broadcast-only. No engagement. No tracking.

**Setup:**
- Message @BotFather on Telegram to create a bot
- Create a Channel (e.g., @JTFNewsLive)
- Add the bot as an administrator of the channel with "Post Messages" permission
- Disable comments on the channel (Channel Settings → Discussion → None)

**API:** Bot API — `https://api.telegram.org/bot{token}/`

**Character limit:** 4,096 characters per message (plenty for any fact cycle)

**Implementation — Claude Code prompt:**

```
Create a Node.js module `channels/telegram.js` that:
1. Uses env vars TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID
2. Exports an async function postToTelegram(text, link) that:
   - Sends message via /sendMessage endpoint
   - Uses parse_mode "HTML" for minimal formatting (bold titles only)
   - Appends a "Read more" link at the bottom
   - Disables link preview (disable_web_page_preview: true)
   - Returns the message ID on success
   - Logs errors but never throws
3. No external dependencies — use native fetch
```

**Environment variables:**
```bash
export TELEGRAM_BOT_TOKEN="123456:ABC-DEF..."
export TELEGRAM_CHANNEL_ID="@JTFNewsLive"
```

---

### 4. Threads (Meta)

**Why:** Large and growing audience. Free API. No direct messaging means less engagement pressure.

**Whitepaper alignment:** Post once, never reply. Threads doesn't have DMs, which helps enforce the boundary.

**API:** Threads Publishing API (requires Meta developer account)

**Account setup:**
- Create a Threads account linked to an Instagram account
- Register at developers.facebook.com
- Create an app, add Threads API product
- Generate a long-lived access token

**Character limit:** 500 characters

**Implementation — Claude Code prompt:**

```
Create a Node.js module `channels/threads.js` that:
1. Uses env vars THREADS_USER_ID and THREADS_ACCESS_TOKEN
2. Exports an async function postToThreads(text, link) that:
   - Creates a media container via POST /v1.0/{user_id}/threads
     with media_type TEXT and truncated text + link
   - Publishes via POST /v1.0/{user_id}/threads_publish
   - Returns the post ID on success
   - Logs errors but never throws
3. No external dependencies — use native fetch
```

**Environment variables:**
```bash
export THREADS_USER_ID="your-threads-user-id"
export THREADS_ACCESS_TOKEN="your-long-lived-token"
```

**Note:** Threads API tokens need periodic refresh. Add a token refresh utility or use a long-lived token (60 days) and set a reminder to rotate.

---

### 5. Podcast RSS Feed

**Why:** The audio is already being generated. Packaging it as a podcast is essentially free and opens up Apple Podcasts, Spotify, Google Podcasts, Pocket Casts, and every other podcast app.

**Whitepaper alignment:** Perfect. Listen-only. No comments. No engagement. Calm voice, facts, silence.

**Hosting:** GitHub Pages (free) or Cloudflare R2 free tier (10 GB/month)

**Feed format:** Standard RSS 2.0 with iTunes namespace

**Distribution (all free to list):**
- Apple Podcasts — https://podcastsconnect.apple.com
- Spotify — https://podcasters.spotify.com
- Google Podcasts — auto-indexed from RSS
- Pocket Casts — submit RSS URL

**Implementation — Claude Code prompt:**

```
Create a Node.js script `channels/podcast-feed.js` that:
1. Reads a directory of audio files (MP3) with naming convention
   YYYY-MM-DD-HHMM.mp3
2. Generates a valid podcast RSS 2.0 XML feed with:
   - iTunes namespace tags (itunes:author, itunes:category News,
     itunes:explicit false, itunes:image)
   - Channel title: "JTF News — Just The Facts"
   - Channel description: "Verified facts from multiple independent
     sources. No opinions. No adjectives. No interpretation."
   - Channel link: https://larryseyer.github.io/jtfnews/
   - Each audio file becomes an <item> with:
     - <enclosure> pointing to the hosted audio URL
     - <pubDate> derived from filename
     - <itunes:duration> (read from file or estimated)
     - <title> formatted as "JTF News — YYYY-MM-DD HH:MM GMT"
     - <description> with the text version of that cycle's facts
3. Writes the feed to podcast.xml
4. Optionally accepts --daily flag to produce a single daily
   digest episode instead of per-cycle episodes
```

**Podcast metadata:**
```xml
<itunes:category text="News"/>
<itunes:category text="News">
  <itunes:category text="Daily News"/>
</itunes:category>
<itunes:explicit>false</itunes:explicit>
<itunes:author>JTF News</itunes:author>
<language>en</language>
```

---

### 6. Alexa Skill (from Whitepaper Section 22)

**Why:** The whitepaper already calls for this. "Say the name. Hear the fact."

**Cost:** Free to develop and publish.

**Implementation — Claude Code prompt:**

```
Create an Alexa Skill project in `channels/alexa/` that:
1. Uses the Alexa Skills Kit SDK for Node.js
2. Skill invocation: "Alexa, ask JTF News for the latest"
3. LaunchRequestHandler fetches the latest fact cycle text from
   the JTF News RSS feed (feed.xml)
4. Reads the facts aloud using SSML with:
   - Slow rate: <prosody rate="90%">
   - Brief pauses between items: <break time="1s"/>
5. Includes a SessionEndedRequestHandler
6. Includes skill.json manifest with:
   - Name: "JTF News"
   - Category: NEWS
   - Description matching the whitepaper tagline
7. Includes instructions for deploying via ASK CLI (free)
```

---

### 7. Google Home Action (from Whitepaper Section 22)

**Why:** Same rationale as Alexa. Different ecosystem, same reach.

**Cost:** Free to develop and publish.

**Note:** Google is transitioning from Actions on Google to newer conversational frameworks. Check current status before implementing. May want to prioritize Alexa first and revisit Google later.

**Implementation — Claude Code prompt:**

```
Research the current state of Google Assistant / Google Home
custom actions as of 2025-2026. If Actions on Google is still
supported, create a basic action that:
1. Invocation: "Hey Google, talk to JTF News"
2. Fetches latest facts from the RSS feed
3. Reads them aloud
If the platform has changed, document the current recommended
approach and create the equivalent.
```

---

### 8. Email Newsletter (via Buttondown — free tier)

**Why:** Algorithm-proof. Direct to inbox. No tracking pixels (matches "no tracking" principle). Buttondown's free tier allows up to 100 subscribers.

**Whitepaper alignment:** No ads, no tracking. Buttondown supports plain-text emails with zero tracking.

**Setup:**
- Create account at https://buttondown.com
- Buttondown can auto-import from RSS — point it at your feed.xml
- Or use their API for custom sends

**Implementation — Claude Code prompt:**

```
Create a Node.js module `channels/newsletter.js` that:
1. Uses env var BUTTONDOWN_API_KEY
2. Exports an async function sendNewsletter(subject, bodyText) that:
   - Posts to https://api.buttondown.com/v1/emails
   - Sends plain-text email (no HTML, no tracking pixels)
   - Subject format: "JTF News — YYYY-MM-DD HH:MM GMT"
   - Body is the plain fact cycle text
   - Returns the email ID on success
   - Logs errors but never throws
3. No external dependencies — use native fetch

Also document the alternative: Buttondown's built-in RSS-to-email
feature which requires zero code (just configure in their dashboard).
```

**Environment variables:**
```bash
export BUTTONDOWN_API_KEY="your-api-key"
```

---

## Fan-Out Orchestrator

This is the central script that ties everything together.

**Implementation — Claude Code prompt:**

```
Create `fan-out.js` — the main orchestrator that:

1. Accepts input:
   - --text <file>   Path to the current fact cycle text file
   - --audio <file>  Path to the current audio file (optional)
   - --link <url>    Link to the full story on the JTF site

2. Imports all channel modules from channels/

3. Runs ALL channel posts concurrently using Promise.allSettled()
   (never Promise.all — one failure must not block others)

4. Logs results in a structured format:
   {
     "timestamp": "ISO-8601",
     "channels": {
       "bluesky": { "status": "ok", "id": "..." },
       "mastodon": { "status": "ok", "id": "..." },
       "telegram": { "status": "ok", "id": "..." },
       "threads": { "status": "error", "error": "token expired" },
       "newsletter": { "status": "skipped", "reason": "daily only" }
     }
   }

5. Writes the log to fan-out-log.json (append, one line per run)

6. Exit code 0 even if some channels fail (log the failures)

7. Supports a --dry-run flag that validates credentials and
   prints what would be posted without actually posting

8. Supports a --channels flag to run only specific channels:
   --channels bluesky,telegram

9. Reads all credentials from environment variables (never
   hardcoded, never in config files committed to git)
```

---

## Environment Variables Summary

Create a `.env.example` file (committed to repo) and a `.env` file (gitignored):

```bash
# Bluesky
BLUESKY_HANDLE=jtfnews.bsky.social
BLUESKY_APP_PASSWORD=

# Mastodon
MASTODON_INSTANCE=https://mastodon.social
MASTODON_ACCESS_TOKEN=

# Telegram
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHANNEL_ID=@JTFNewsLive

# Threads
THREADS_USER_ID=
THREADS_ACCESS_TOKEN=

# Buttondown Newsletter
BUTTONDOWN_API_KEY=

# Podcast
PODCAST_AUDIO_BASE_URL=https://larryseyer.github.io/jtfnews/audio/
```

---

## Implementation Order (Recommended)

Priority is based on effort-to-reach ratio and whitepaper alignment:

| Priority | Channel | Effort | Reach | Notes |
|----------|---------|--------|-------|-------|
| 1 | Telegram | 1 hour | High | Purest whitepaper fit. No algorithm. |
| 2 | Bluesky | 1 hour | Growing | X replacement. Open protocol. |
| 3 | Mastodon | 1 hour | Medium | Fediverse reach. Same code pattern. |
| 4 | Podcast RSS | 2 hours | High | Audio already exists. Passive discovery. |
| 5 | Newsletter | 30 min | Medium | Buttondown RSS auto-import = zero code. |
| 6 | Threads | 2 hours | High | Largest audience. Token management overhead. |
| 7 | Alexa | 4 hours | Medium | Whitepaper promise. Skill review process. |
| 8 | Google Home | 4 hours | Medium | Platform in transition. Research first. |

---

## Integration with Existing JTF Pipeline

The fan-out script should be called at the end of each 30-minute cycle:

```bash
# Inside your existing cron or scheduler:
node fan-out.js \
  --text ./output/latest-cycle.txt \
  --audio ./output/latest-cycle.mp3 \
  --link "https://larryseyer.github.io/jtfnews/"
```

For the podcast feed, run the feed generator after each audio file is produced:

```bash
node channels/podcast-feed.js \
  --audio-dir ./output/audio/ \
  --output ./docs/podcast.xml
```

---

## What We Skip (and Why)

| Channel | Reason |
|---------|--------|
| X / Twitter | $100/month minimum for API access |
| Reddit | Requires engagement / comments — violates whitepaper |
| Facebook | Requires Page + algorithm controls content visibility |
| Discord | Community/engagement platform — wrong model |
| TikTok | Video-first, requires editing, algorithm-driven |
| Nostr | Philosophically aligned but audience too small for now |
| Apple News | Publisher approval process is slow; revisit later |
| LinkedIn | Professional network, engagement-driven, wrong audience |

---

## Monitoring & Transparency

Consistent with the whitepaper's operational cost dashboard, add fan-out status to the existing monitor:

```
Fan-Out Status (Last Cycle)
├── Bluesky:    ✓ posted 14:30 GMT
├── Mastodon:   ✓ posted 14:30 GMT
├── Telegram:   ✓ posted 14:30 GMT
├── Threads:    ✗ token expired
├── Podcast:    ✓ feed updated 14:31 GMT
└── Newsletter: ○ daily digest at 00:00 GMT
```

---

## Claude Code Master Prompt

Use this single prompt to scaffold the entire project:

```
Read FanPlan.md in this repo. It contains the complete fan-out
distribution plan for JTF News.

Create the following project structure:

  channels/
    bluesky.js
    mastodon.js
    telegram.js
    threads.js
    newsletter.js
    podcast-feed.js
    alexa/
      index.js
      skill.json
  fan-out.js
  .env.example

Each channel module exports a single async function that:
- Accepts (text, link) parameters
- Posts to its platform via native fetch (no external deps)
- Returns { status, id } on success
- Returns { status: "error", error: message } on failure
- Never throws

fan-out.js orchestrates all channels with Promise.allSettled()
and supports --text, --audio, --link, --dry-run, and --channels flags.

All credentials come from environment variables.
Follow the implementation details in FanPlan.md exactly.
```

---

## License

This plan follows the JTF News licensing: **CC-BY-SA**.

Use it. Share it. Credit us. Don't sell it.
