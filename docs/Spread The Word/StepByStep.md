# JTF News Launch — Step by Step

*"No fanfare. No launch party. Just on."*

This document provides the exact sequence for launching JTF News to the world. Each step is a one-time action. We post once. We never reply.

---

## Prerequisites

Before starting, ensure:
- [ ] YouTube livestream is running and stable
- [ ] GitHub Pages site is live (larryseyer.github.io/jtfnews)
- [ ] RSS feed is working (feed.xml)
- [ ] All documentation is current (whitepaper, how-it-works)

---

## Phase 1: Video Platforms

These are the primary streams. Set them up first.

### Step 1: YouTube (Primary)
**Status:** Should already be running

- [ ] Verify stream is live at youtube.com/@JTFNews (or your channel)
- [ ] Verify description contains all links (updated in SPECIFICATION.md Section 13.1)
- [ ] Verify comments are disabled
- [ ] Verify live chat is disabled or hidden
- [ ] Set license to Creative Commons

### Step 2: Rumble (Secondary)
**File:** `RumblePost.md`

- [ ] Create Rumble account
- [ ] Set up livestream pointing to same source as YouTube
- [ ] Copy description from `RumblePost.md`
- [ ] Disable comments if possible
- [ ] Go live

---

## Phase 2: Social Media Announcements

One post per platform. Never reply. These are announcements, not conversations.

### Step 3: X (Twitter)
**File:** `XPost.md`

- [ ] Create @JTFNews account (or use existing)
- [ ] Post the content from `XPost.md`
- [ ] Pin the tweet
- [ ] Do not engage with replies

### Step 4: Threads
**File:** `ThreadsPost.md`

- [ ] Create Threads account (requires Instagram)
- [ ] Post the content from `ThreadsPost.md`
- [ ] Do not engage with replies

### Step 5: LinkedIn
**File:** `LinkedInPost.md`

- [ ] Create LinkedIn page for JTF News
- [ ] Post the content from `LinkedInPost.md`
- [ ] Do not engage with comments

### Step 6: Facebook
**File:** `FacebookPost.md`

- [ ] Create Facebook page for JTF News
- [ ] Post the content from `FacebookPost.md`
- [ ] Add the informational follow-up comment with links
- [ ] Do not engage further

### Step 7: Instagram
**File:** `InstagramPost.md`

- [ ] Create Instagram account
- [ ] Add link to bio (linktree or direct to how-it-works)
- [ ] Post the content from `InstagramPost.md`
- [ ] Do not engage with comments

---

## Phase 3: Automated Distribution

These channels receive automatic posts every 30 minutes (or as configured).

### Step 8: Telegram Broadcast Channel
**Priority: Highest** — Purest whitepaper alignment

- [ ] Message @BotFather to create a bot
- [ ] Create channel @JTFNewsLive
- [ ] Add bot as admin with "Post Messages" permission
- [ ] Disable comments on channel
- [ ] Add credentials to `.env`
- [ ] Test with `--dry-run`

### Step 9: Bluesky
**Priority: High** — Open protocol, X replacement

- [ ] Create account at bsky.app
- [ ] Generate App Password (Settings → App Passwords)
- [ ] Add credentials to `.env`
- [ ] Test with `--dry-run`

### Step 10: Mastodon
**Priority: High** — Fediverse reach

- [ ] Create account on mastodon.social or newsie.social
- [ ] Create application (Preferences → Development)
- [ ] Request `write:statuses` scope only
- [ ] Add credentials to `.env`
- [ ] Test with `--dry-run`

### Step 11: Podcast RSS Feed
**Priority: High** — Passive discovery, audio already exists

- [ ] Run podcast-feed.js to generate podcast.xml
- [ ] Submit to Apple Podcasts (podcastsconnect.apple.com)
- [ ] Submit to Spotify (podcasters.spotify.com)
- [ ] Pocket Casts will auto-index

### Step 12: Email Newsletter (Buttondown)
**Priority: Medium** — Algorithm-proof, direct to inbox

- [ ] Create account at buttondown.com (free tier: 100 subscribers)
- [ ] Option A: Point Buttondown at feed.xml for auto-import
- [ ] Option B: Use API for custom sends
- [ ] Add credentials to `.env` if using API

### Step 13: Threads API (Automated)
**Priority: Medium** — Large audience, token management overhead

- [ ] Register at developers.facebook.com
- [ ] Create app, add Threads API product
- [ ] Generate long-lived access token
- [ ] Add credentials to `.env`
- [ ] Set reminder to refresh token (60 days)
- [ ] Test with `--dry-run`

---

## Phase 4: Voice Assistants

These are whitepaper promises. Implement after core distribution is stable.

### Step 14: Alexa Skill
- [ ] Create skill using ASK CLI
- [ ] Skill invocation: "Alexa, ask JTF News for the latest"
- [ ] Submit for review
- [ ] Wait for approval

### Step 15: Google Home Action
- [ ] Research current platform status
- [ ] Implement if Actions on Google still supported
- [ ] Submit for review

---

## Phase 5: Passive Presence

One-time efforts that work without maintenance.

### Step 16: SEO and Discoverability
- [ ] Ensure meta tags are correct on GitHub Pages
- [ ] Submit sitemap to Google Search Console
- [ ] Verify Open Graph tags for social sharing

### Step 17: GitHub Discoverability
- [ ] Add relevant topics to repository
- [ ] Ensure README is clear and links to live stream
- [ ] Add to "awesome" lists if appropriate

---

## Daily Operations

Once launched, the system runs itself:

| Time | Action |
|------|--------|
| Every 30 min | fan-out.js posts to all channels |
| Midnight GMT | Daily archive to GitHub |
| Weekly | Check token expirations |
| Quarterly | Ownership audit |

---

## If Something Breaks

1. Check fan-out-log.json for errors
2. One channel failure does not stop others (Promise.allSettled)
3. Refresh expired tokens
4. SMS alerts will notify of critical issues

---

## The Philosophy

Remember:
- We post once. We never reply.
- If someone shouts back, we stay quiet.
- We do not argue with the wind.
- The methodology belongs to no one. It serves everyone.

---

## Files in This Folder

| File | Purpose |
|------|---------|
| `StepByStep.md` | This document — launch sequence |
| `FanOutPlan.md` | Technical architecture for automated distribution |
| `SpreadTheNews.md` | Philosophy of discovery vs. promotion |
| `XPost.md` | X/Twitter announcement content |
| `ThreadsPost.md` | Threads announcement content |
| `LinkedInPost.md` | LinkedIn announcement content |
| `FacebookPost.md` | Facebook announcement content |
| `InstagramPost.md` | Instagram announcement content |
| `RumblePost.md` | Rumble video description |

---

*CC-BY-SA. Use it. Share it. Credit us.*
