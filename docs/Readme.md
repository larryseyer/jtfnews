# Just the Facts News

24/7 live stream: only verifiable facts, no opinions, no adjectives, no interpretation.

## Philosophy
If we stay boring enough, we might just change the world.

## How it works
- Scrapes public headlines from ~20 long-established English news sites
- Requires minimum 2 unrelated sources (different owners/investors)
- AI rewrites to strip all non-factual language
- Generates calm northern-English female TTS voice
- Serves minimal HTML page for OBS browser source (serene rotating backgrounds)
- Streams to YouTube via OBS (title: "JTF News – Live")
- Tweets each story once on X, no replies
- Daily text log zipped and pushed to GitHub archive repo at midnight GMT
- Silence when no qualifying news

## Constraints obeyed
- No APIs, no paywalls, respect robots.txt
- No ads, no tracking, no long-term raw data storage
- No human contact info
- CC-BY-SA license on output
- Non-profit spirit

## Setup (local only)
1. Install dependencies: `pip install -r requirements.txt`
2. Configure config.json (sources, ratings, owners, YouTube RTMP, X API keys)
3. Run: `python main.py`
4. In OBS: add browser source → http://localhost:8000/news.html
5. Add audio input for TTS output file

## Files
- main.py          → main loop (30-min cycle)
- news.html        → displayed page
- news.css         → styling
- news.js          → reads local JSON
- config.json      → sources & settings
- requirements.txt → dependencies

No server. No database. Plain text + daily archive push.

Run it. Stay quiet.
