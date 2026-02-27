# Claude Code Prompt: Build Just the Facts News (JTF News) System

You are an expert Python developer building a complete, minimal, local-first implementation of "Just the Facts News" exactly as described in the white paper and project requirements below. Do not abbreviate, do not simplify, do not add features not listed, do not remove any constraint. Follow every rule to the letter.

## White Paper – Full Text (must be obeyed exactly)

Just the Facts News: Algorithmic Reporting for a Narrative-Free World

If we stay boring enough, we might just change the world.

0. What is News?
A verifiable event, within the last twenty-four hours, that affects five hundred people, costs one million US dollars, changes a law, or redraws a border. Nothing less. Nothing more.

1. Core Principle
We do not editorialise. We state what happened, where, when, and—when known—how many. Nothing more.

2. Data Sourcing
Public headlines and metadata from open websites. No login walls. No paid content. No APIs. No copyrighted imagery.

3. Data Processing
AI rewrites. Strips adjectives. Keeps facts. If it can’t be proven, it vanishes.

4. Source Rating
Live scores: accuracy, bias, speed, consensus. Numbers only. No labels.

5. Verification
Two unrelated sources minimum. Unrelated means different owners, different investors.

6. Voice & Visuals
Calm female voice, northern English. Slow, neutral background images—clouds, fields, water. Never the event. Never the news.

7. Updates
Every thirty minutes. Breaking news within five, but no urgency.

8. Transparency
Pseudocode on GitHub. Anyone can read. No one can change.

9. Disclaimers
This is not journalism. It is data.

10. Ownership Disclosure
Top three owners listed. Percentages. No spin.

11. Funding & Community
No ads. No tracking. Donations. Five-pound subscription for early code.

12. Governance
Non-profit. No dividends. We own nothing.

13. Legal & Integrity
Not liable for misuse. Corrections announced loud. Silence when nothing happens. English only. We die if we fail.

14. Visuals
Images rotate every forty-five seconds. Never match the story. They breathe.

15. The Voice
Custom. Female. Northern. Quiet. Trained on plain speech. Speaks. Stops.

16. Sound Design
Voice only. No music. No breath. When it stops, quiet.

17. Ethics
We do not store raw data longer than seven days. Daily summaries are archived on GitHub. Nothing hidden. Nothing sold. Just the record. No paywalls. No bots. Respect robots.txt. No logs.

18. Licensing
CC-BY-SA. Use it. Share it. Credit us. Don’t sell it.

19. Enforcement
We don’t chase. We list. Let the world notice.

20. Launch
When the code runs. When two sources speak. We start. No fanfare.

21. Why
Facts are dying. Silence is louder.

22. Voice Assistants
Alexa. Google Home. Say the name. Hear the fact.

23. Social Media
We tweet once. We never reply.

24. YouTube
Title: JTF News – Live. Description: Facts only. No chat. No hearts.

25. The Loop
Twenty-four hours. Midnight GMT. Each story once. Then back.

## Additional Project Requirements (must also be followed exactly)

- Delivery method: OBS Studio streaming to YouTube
- OBS shows a local browser source pointing to localhost HTML page (news.html)
- HTML page uses HTML + CSS + JavaScript only (no server, no framework)
- JavaScript reads a local JSON file that is updated every cycle
- Lower third: one white Arial sentence, appears 5 seconds, fades
- Thin grey bar above lower third showing: "Source – score" (example: Reuters – 9.8)
- Background images: full-screen, slow fade every 50 seconds, cycle of serene public-domain images (clouds, waves, fields, stars), never related to story
- Audio: separate TTS-generated WAV/MP3 file fed into OBS via virtual audio cable or direct file source
- Core script: Python running in terminal, local-only
- Scrapes ~20 pre-defined English news sites (BBC, Reuters, AP, etc.) that update daily and are ≥5 years old
- Rewrites using AI (you can simulate or placeholder with rule-based stripping for now)
- Stores minimal daily text log (one line per story)
- At midnight GMT: zip daily log → commit & push to GitHub repo in year folder (2026/, 2027/, etc.)
- One root README.md only
- No database – use plain text files + daily zip
- No repeats within 24h loop; loop replays day’s facts until midnight reset
- Breaking news: wait for second unrelated source; never single-source
- Corrections: if needed, insert at top of next cycle with full volume
- Silence: if no qualifying news, stream shows background + voice says nothing
- X (Twitter): one tweet per new story, exact sentence, no reply, no like, no retweet
- No email, no phone, no human contact address
- Archive pushed to GitHub daily, public, year folders
- Respect robots.txt in scraper
- No long-term raw storage; only daily summary text survives

## Task

1. Create complete folder structure
2. Write main.py – the eternal loop script (30-min cycle)
3. Write news.html, news.css, news.js for the browser source
4. Include placeholder TTS call (use piper-tts or pyttsx3 if available; comment how to swap for custom northern voice later)
5. Include placeholder for AI rewrite function (rule-based adjective strip + fact extraction)
6. Include YouTube RTMP key placeholder & X API tweet function placeholder
7. Write README.md for GitHub repo
8. Write initial config.json with example sources (20 sites) and placeholder owner/rating data
9. Add watchdog: if confidence <85% or contradiction, print alert (future text message placeholder)
10. Ensure silence when no stories qualify

Generate every file in full. Show diffs or write complete files. Ask only if something is truly ambiguous. Otherwise build it exactly as specified.
