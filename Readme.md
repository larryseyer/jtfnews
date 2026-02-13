# Just the Facts News

24/7 live stream: only verifiable facts, no opinions, no adjectives, no interpretation.

**[Watch Live](https://www.youtube.com/@JTFNewsLive)** · **[How It Works](https://larryseyer.github.io/jtfnews/how-it-works.html)** · **[Whitepaper](https://larryseyer.github.io/jtfnews/whitepaper.html)** · **[RSS Feed](https://larryseyer.github.io/jtfnews/feed.xml)**

## Philosophy
If we stay boring enough, we might just change the world.

JTF News is a methodology, not just a channel. Two sources. Different owners. Strip the adjectives. State the facts. Stop. This approach can serve any community—local news, sports, school boards—wherever facts matter. See [WhitePaper.md](docs/WhitePaper.md) and [SPECIFICATION.md](docs/SPECIFICATION.md#20-future-directions) for the expansion framework.

## How it works
- Scrapes public headlines from 30+ long-established English news sites
- Requires minimum 2 unrelated sources (different owners/investors)
- AI rewrites to strip all non-factual language
- Generates calm northern-English female TTS voice
- Serves minimal HTML overlay for OBS browser source (serene rotating backgrounds)
- Streams to YouTube via OBS (title: "JTF News – Live")
- Daily text log zipped and pushed to GitHub archive repo at midnight GMT
- Silence when no qualifying news

## Source Ratings

Source accuracy ratings are **evidence-based**, calculated from verification performance:

```
Rating = (verification_successes / total) × 10
```

| Display | Meaning |
|---------|---------|
| `9.6*` | Editorial baseline (no observed data yet) |
| `8.5* (3/10)` | Cold start (blended baseline + observed) |
| `9.4 (47/50)` | Mature (pure evidence-based rating) |

Both sources involved in a successful verification receive +1 success. Stories that expire unverified record +1 failure. All events logged to `data/ratings_audit.jsonl` for legal defensibility.

## Public Pages

The [JTF News website](https://larryseyer.github.io/jtfnews/) includes:

- **[How It Works](https://larryseyer.github.io/jtfnews/how-it-works.html)** - Interactive guide with live story demo
- **[Whitepaper](https://larryseyer.github.io/jtfnews/whitepaper.html)** - Full editorial philosophy (renders from WhitePaper.md)
- **[Operations Dashboard](https://larryseyer.github.io/jtfnews/monitor.html)** - Live API costs and system status
- **[Screen Saver](https://larryseyer.github.io/jtfnews/screensaver.html)** - Run JTF News as your desktop screen saver

## Constraints obeyed
- No APIs, no paywalls, respect robots.txt
- No ads, no tracking, no long-term raw data storage
- No human contact info
- CC-BY-SA license on output
- Non-profit spirit

## Setup (local only)
1. Install dependencies: `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and add API keys (Anthropic, ElevenLabs, Twilio)
3. Configure `config.json` (sources, ratings, thresholds)
4. Run: `python main.py`
5. In OBS: add browser sources for `web/lower-third.html` and `web/background-slideshow.html`

## Support

JTF News is self-funded and open source. If you find value in unbiased, fact-only news:

[![Sponsor](https://img.shields.io/badge/Sponsor-GitHub-ea4aaa)](https://github.com/sponsors/larryseyer)

Live operational costs are displayed transparently on the [funding page](https://larryseyer.github.io/jtfnews/).

## Project Structure

```
main.py                 → Main loop (30-min cycle), fact extraction, verification
config.json             → Sources, ratings, thresholds, timing
web/
  lower-third.html/css/js   → OBS overlay for displaying facts
  background-slideshow.html → Rotating seasonal background images
  screensaver.html          → Standalone screen saver version
  monitor.html/css/js       → Operations dashboard
gh-pages-dist/          → Public website (GitHub Pages)
  index.html            → Landing page with live cost transparency
  how-it-works.html     → Interactive guide
  whitepaper.html       → Renders WhitePaper.md dynamically
  feed.xml              → RSS feed
  stories.json          → Current day's verified stories
docs/
  WhitePaper.md         → Editorial philosophy (single source of truth)
  SPECIFICATION.md      → Full technical specification
  ResilienceSystem.md   → 24/7 uptime resilience design
media/
  fall/spring/summer/winter/  → Seasonal background images
```

No server. No database. Plain text + daily archive push.

Run it. Stay quiet.
