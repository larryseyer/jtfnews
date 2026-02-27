# Just the Facts News – Project Summary
**Date:** February 10, 2026
**Idea owner:** Larry Seyer (@larryseyer)

## Core Concept
24/7 live stream delivering **only verifiable facts**
- No opinions, no adjectives, no interpretation
- Calm synthetic female northern-English voice
- Slow serene background images (unrelated to stories)
- Brand: Just the Facts News (JTF News)

## Key Rules
- News = verifiable event in last 24 h affecting ≥500 people, costing ≥$1M USD, changing law or border
- Minimum 2 unrelated sources (different owners/investors)
- Source ratings shown (accuracy, bias, speed, consensus) + top 3 owners
- Stories said once per 24-hour loop (midnight GMT reset)
- Corrections loud and immediate
- Silence when no qualifying news

## Delivery
- YouTube live stream (minimal: title “JTF News – Live”, no chat, no interaction)
- X posts: one tweet per story, no replies
- Planned: Alexa/Google Home flash briefing
- Archive: daily .txt files zipped → GitHub (year folders)

## Tech (minimal/local-first)
- OBS Studio + browser source showing local HTML/JS/CSS page
- Python script in terminal (scraping → rewriting → TTS → file update)
- SQLite or plain text + daily zip for archive
- Custom TTS voice (northern English female, calm)

## Philosophy & Constraints
- No ads, no tracking, no paywall
- Donations or tiny subscription only
- CC-BY-SA license
- No enforcement – just public list of misusers
- Non-profit structure planned
- Silence is the brand

Tagline:
*If we stay boring enough, we might just change the world.*
