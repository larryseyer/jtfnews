# Spread the News
## A Philosophy-Aligned Discovery Strategy for JTF News

*"We don't chase. We list. Let the world notice."*

---

## Budget Reality

**Current funding:** Self-funded with limited resources. No sponsors yet.

This means we prioritize:
- **Free tools first** - SEO, RSS submissions, GitHub discoverability
- **Manual over automated** - Twitter posts by hand, not API ($100/month is prohibitive)
- **One-time efforts** - Single announcements that don't require ongoing costs
- **Passive presence** - Assets that work without maintenance

The philosophy already aligns with this constraint: we don't chase, we don't engage, we don't maintain active campaigns. A bootstrap budget fits perfectly.

---

## The Paradox

The whitepaper declares:
- "No fanfare. No launch party. Just on."
- "We tweet once. We never reply."
- "If someone shouts back, we stay quiet. We do not argue with the wind."

Yet the reality is clear: **Nobody benefits if nobody knows about it.**

This document resolves that tension. The whitepaper doesn't reject *visibility*—it rejects *attention-seeking tactics*. There is a profound difference between shouting at someone and having a well-lit storefront.

---

## The Core Insight

**The constraint IS the differentiator.**

A news service that refuses to engage, refuses to argue, and refuses to promote itself is *remarkable* in a world of attention warfare. In an economy built on engagement farming, JTF News is a deliberate anomaly.

That remarkability is the marketing.

---

## What's Permitted vs. Prohibited

| Prohibited | Permitted |
|------------|-----------|
| Hype, urgency, "BREAKING" | Calm presence |
| Engagement bait | Passive availability |
| Tracking, ads | Open educational content |
| Replies, arguments | Single statements |
| Selling | Sharing |
| Chasing | Being findable |

---

## The Methodology as Message

The whitepaper contains inherently shareable philosophy:

> "If we stay boring enough, we might just change the world."

> "Think of us as a very slow, very honest librarian. We read everything, say nothing unless two other librarians agree, and never raise our voice."

> "We do not argue with the wind."

> "Twitter is not for conversation. It is for a single sentence."

> "Silence when nothing happens."

> "We die if we fail."

These read like manifestos. **People share manifestos.**

The methodology belongs to no one. It serves everyone. That openness is itself a distribution mechanism—every community that adopts the methodology points back to the original.

---

## Target Communities

These groups would naturally care about fact-only news. We don't pursue them. We exist where they already look.

### 1. Media Critics and Journalism Reformers
- Columbia Journalism Review readers
- Nieman Lab audience
- Press criticism newsletters (Press Watch, Study Hall)
- r/journalism, r/media_criticism

### 2. News Anxiety / Doomscrolling Recovery
- Mental health communities discussing news fatigue
- Calm/mindfulness app communities
- "Slow news" movement adherents
- People actively seeking non-dramatic news

### 3. Fact-Check Enthusiasts
- Wikipedia editors (verification-obsessed by nature)
- Snopes, PolitiFact, Full Fact followers
- Open-source intelligence (OSINT) communities
- r/neutralpolitics

### 4. Open Source and Tech Ethics
- Hacker News (this is exactly their aesthetic)
- GitHub Explore and Trending
- AI ethics communities (Claude-powered verification is interesting)
- Privacy-focused communities (no tracking is a feature)

### 5. Cord-Cutters and Alternative Media Seekers
- People tired of cable news drama
- RSS and independent media enthusiasts
- Those seeking news without commentary

---

## Phase 1: Be Findable (Passive Discovery)

*"Let the world notice"*

### 1.1 Search Engine Optimization

People searching for alternatives should find us. This is not chasing—it's being organized.

**Target Keywords:**
- "unbiased news"
- "facts only news"
- "news without opinion"
- "verified news live"
- "calm news stream"
- "news without commentary"
- "no opinion news source"

**Technical Implementation:**
- [ ] Add meta descriptions to all GitHub Pages
- [ ] Add OpenGraph tags for social sharing
- [ ] Add structured data markup (Schema.org NewsMediaOrganization)
- [ ] Create focused landing pages for key concepts

**Files to Update:**
- `gh-pages-dist/index.html`
- `gh-pages-dist/how-it-works.html`
- `gh-pages-dist/whitepaper.html`
- `gh-pages-dist/screensaver-setup.html`

### 1.2 RSS Directory Submissions

RSS is experiencing a renaissance among people tired of algorithmic feeds. These are exactly our audience.

**Submit to:**
- [ ] Feedly (add to their directory)
- [ ] NewsBlur
- [ ] Inoreader
- [ ] The Old Reader
- [ ] News aggregator directories

**Verify:**
- [ ] Feed validates at https://validator.w3.org/feed/
- [ ] Feed parses correctly in major readers

### 1.3 Voice Assistant Integration

From the whitepaper: *"Alexa. Google Home. Say the name. Hear the fact."*

**Implementation:**
- [x] Publish Alexa Flash Briefing skill *(application submitted February 2026)*
- [ ] Create Google Assistant Action
- [ ] Ensure `alexa.json` is properly formatted

This is passive discovery—someone asks for news and gets JTF. The calm tone stands in stark contrast to dramatic news briefings.

### 1.4 GitHub Discoverability

The open source community finds projects through GitHub's discovery mechanisms.

**Optimize:**
- [ ] Add GitHub Topics: `news`, `fact-checking`, `journalism`, `ai`, `automation`, `open-source`
- [ ] Ensure README has clear badges
- [ ] Enable GitHub Discussions (let community come to us)
- [ ] Add to GitHub Explore relevant categories

---

## Phase 2: Be Shareable (Assets for Others)

*"Use it. Share it. Credit us."*

### 2.1 Embeddable Fact Widget

Let websites embed a JTF ticker. We don't push—others pull.

```html
<iframe
  src="https://larryseyer.github.io/jtfnews/widget.html"
  width="400" height="80"
  frameborder="0">
</iframe>
```

**Implementation:**
- [ ] Create `gh-pages-dist/widget.html` - minimal, embeddable
- [ ] Auto-updating latest fact with attribution
- [ ] Customizable via URL parameters (dark mode, size)
- [ ] Include "via JTF News" attribution

### 2.2 Whitepaper as Standalone Document

The philosophy document is compelling enough to share independently.

**Create:**
- [ ] PDF version with clean typography
- [ ] One-page summary for quick sharing
- [ ] Quotable pull-quotes formatted for social sharing

### 2.3 Screen Saver Gallery Submissions

The screen saver is self-promoting. People running it in offices, lobbies, and homes create ambient awareness.

**Submit to:**
- [ ] WebViewScreenSaver galleries (macOS community)
- [ ] Wallpaper Engine workshop (Steam - huge audience)
- [ ] Linux screen saver repositories
- [ ] r/Rainmeter and customization communities

### 2.4 Digital Signage Mode

Many spaces have screens showing ambient content. A dedicated mode optimized for this use case could spread JTF into physical spaces without any outreach.

**Target environments:**
- Doctor's office waiting rooms (calm, non-anxiety-inducing)
- Library reading rooms
- Corporate lobbies
- University common areas
- Coffee shops

**Implementation:**
- [ ] Create `gh-pages-dist/signage.html` - full-screen, no controls
- [ ] Optimized for landscape displays
- [ ] Auto-start, no interaction required
- [ ] Include setup documentation

---

## Phase 3: One-Time Announcements

*"No fanfare. No launch party. Just on."*

The whitepaper permits single statements. We announce once, then go silent.

### 3.1 Hacker News

A single "Show HN" post. The HN community appreciates:
- Technical elegance
- Open source projects
- Anti-hype ethos
- Interesting constraints

**Post once:**
```
Show HN: JTF News – 24/7 automated news that only reports verified facts
```

Then never post again. Let the community discuss (or not).

### 3.2 Product Hunt

A single listing. Not a "launch campaign"—just presence.

**List once:**
- Title: JTF News
- Tagline: "Facts only. No opinions."
- Description: Brief, calm, factual

Then never engage with comments.

### 3.3 Reddit

Single posts to relevant communities:

- [ ] r/InternetIsBeautiful - "A 24/7 calm news stream"
- [ ] r/opensource - "Open source fact-only news"
- [ ] r/minimalism - "News stripped to just facts"
- [ ] r/Journalism - "An experiment in algorithmic verification"

Post once per subreddit. Never reply to comments.

### 3.4 Twitter/X Account Setup

**Account Creation:**
- Create @JTFNewsLive (or similar available handle)
- Bio: "Facts only. No opinions. We tweet once. We never reply."
- Link to YouTube live stream
- No profile engagement—ever

**Manual Posting (Budget Reality):**
Twitter API costs $100/month—prohibitive for a zero-budget project. We post manually.

This actually *reinforces* the philosophy:
- Posting is intentional, not automated
- We can't accidentally over-post
- Each tweet is a deliberate act of stating a fact

**When to Post:**
- Major verified stories (not every story)
- Once per day maximum
- When something genuinely matters

**Tweet Format:**
```
Pennsylvania Avenue school, shooting reported. Police attending.

Sources: Reuters, AP
```

Keep it simple. No hashtags unless they add discoverability value.

**Philosophy Enforcement:**
- Never reply
- Never like
- Never retweet
- Never quote tweet
- Never follow anyone
- Never DM

The account that never responds will generate curiosity. "Why won't they reply?" becomes part of the mythology.

**Future:** If sponsorship covers API costs ($100/month), automation via `main.py` is already scaffolded.

---

## Phase 4: Physical/Ambient Presence

*"We don't chase. We list."*

### 4.1 QR Code Materials

Minimal, aesthetic, non-intrusive.

**Design:**
- Nature photograph background (matching screen saver aesthetic)
- QR code to screensaver URL
- Text: "Just The Facts" (no call to action)
- No logo spam, no "follow us"

**Placement:**
- Leave in coffee shops (don't ask permission to advertise—just leave)
- Library bulletin boards
- University common areas
- Co-working spaces

This is not promotion. It's an access point for the curious.

### 4.2 Business Cards

For when someone asks "What is that?" about your screen saver.

**Front:**
```
JTF News
Facts only. No opinions.
```

**Back:**
```
jtfnews.com/screensaver
```

Nothing else. No social handles. No "follow us." Just the URL.

---

## Phase 5: Let Others Promote

*"CC-BY-SA. Use it. Share it. Credit us."*

### 5.1 Earned Media

JTF News is inherently interesting to journalists covering:
- AI in journalism
- Media bias and trust crisis
- Non-profit media models
- News fatigue and mental health
- The future of news

**We do not pitch.** We exist. Those who cover these beats will find us.

### 5.2 Academic Interest

The methodology could become a teaching case study:
- Journalism schools: "Algorithmic verification in practice"
- Computer science: "AI-assisted fact extraction"
- Media studies: "Post-editorial news production"
- Business: "Sustainable non-profit media models"

**We do not reach out to academics.** We document thoroughly and let them find us.

### 5.3 Community Adoption

From the whitepaper:
> "Communities deserve fact-based reporting: Local news, free from partisan spin. Sports scores, free from hot takes. School boards, free from drama."

Each community that forks the methodology becomes a discovery vector back to the original.

**We do not franchise.** We share. If a community needs facts, the methodology is theirs.

---

## What We Measure

Traditional engagement metrics are irrelevant. Philosophy-aligned metrics:

| Metric | Meaning |
|--------|---------|
| YouTube concurrent viewers | People watching |
| RSS subscribers | Dedicated followers |
| Screen saver installs | Ambient presence |
| GitHub stars | Developer interest |
| Inbound links | Organic discovery |
| Fork count | Methodology adoption |

**What we do NOT measure:**
- Twitter engagement (we don't engage)
- Click-through rates (we don't advertise)
- "Viral" shares (we don't chase)
- Comments (we don't read them)

---

## Implementation Checklist

*Prioritized for zero budget—free strategies first.*

### Immediate (This Week)
- [ ] Add SEO meta tags to all GitHub Pages
- [ ] Add OpenGraph tags for social sharing
- [ ] Submit RSS to Feedly and NewsBlur
- [ ] Create Twitter/X account @JTFNewsLive (manual posting)
- [x] Submit Alexa Flash Briefing skill *(in progress)*

### Short-Term (Next 2 Weeks)
- [ ] Single Hacker News "Show HN" post
- [ ] Single Product Hunt listing
- [ ] Add GitHub Topics for discoverability
- [ ] Validate RSS feed at W3C validator

### Medium-Term (This Month)
- [ ] Create embeddable widget (`gh-pages-dist/widget.html`)
- [ ] Submit screen saver to Wallpaper Engine (free)
- [ ] Reddit announcements (one per subreddit, then silence)
- [ ] PDF version of whitepaper

### When Budget Allows
- [ ] Create digital signage mode
- [ ] Google Assistant Action
- [ ] Twitter API automation ($100/month)

### Ongoing (Forever)
- [ ] Let the system run
- [ ] Let the world notice
- [ ] Stay silent
- [ ] Do not argue with the wind

---

## The Philosophy in Practice

This document itself follows the methodology:
- It states what will be done
- It does not persuade
- It does not hype
- It does not ask for engagement

We will be findable. We will be shareable. We will be interesting.

And then we will be quiet.

*"If we stay boring enough, we might just change the world."*

---

*Last updated: February 2026*
