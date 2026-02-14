# Regional Filtering Design
## Date: 2026-02-13

---

## Overview

Add geographic tagging to all stories, enabling regional streams (JTF News US, JTF News California, etc.) without increasing operational costs.

**Scope:** Phase 1 — Regional filtering of global news only. Same sources, same thresholds, just tagged by location.

**Out of scope (Phase 2):** Local news sources, lowered thresholds, city-level granularity.

---

## Problem Statement

JTF News currently broadcasts all verified stories to a single global stream. Viewers interested only in US news, or California news, have no way to filter. YouTube live streams don't support viewer-side filtering, so regional content requires separate streams.

---

## Design Decisions

### Decision 1: Filter at display time, not write time

**Rejected approach:** Write stories to multiple directories (`data/global/`, `data/us/`, `data/us-california/`), each with its own OBS instance reading its directory.

**Chosen approach:** Single `stories.json` with location tags. Browser source (`lower-third.html?region=us`) filters client-side in JavaScript.

**Rationale:**
- Single source of truth (no data duplication)
- Add new regions by changing URL parameter, not code
- Simpler main.py (no region awareness)
- Same architecture powers RSS/screensaver filtering

### Decision 2: Hybrid location extraction

**Approach:** Claude extracts location as part of fact processing. Keyword matching as fallback if Claude returns null.

**Rationale:**
- Claude is already processing every headline
- Adding location fields costs ~20 extra output tokens (~$0.00001 with Haiku)
- Keyword fallback handles edge cases

### Decision 3: Persistent audio files

**Current:** `audio/current.wav` (overwritten each cycle)

**New:** `audio/{story_id}.wav` (persistent per story)

**Rationale:**
- Generate once, reuse across regions
- Reduces ElevenLabs API calls
- Multiple regions can play same audio file

### Decision 4: Playback control moves to JavaScript

**Current:** main.py controls which story displays when

**New:** lower-third.js handles playback loop, timing, freshness weighting

**Rationale:**
- Each regional browser source manages its own playback independently
- main.py simplified to data + audio generation only
- Easier to adjust timing without Python changes

---

## Architecture

### Data Flow

```
main.py                              lower-third.html?region=X
   │                                          │
   ├─ Scrape headlines                        │
   ├─ Process with Claude                     │
   │   └─ Extract: facts + location           │
   ├─ Verify 2 sources                        │
   ├─ Write to stories.json ────────────────► │ Load stories.json
   ├─ Generate audio/{id}.wav ──────────────► │ Filter by region
   ├─ Tweet once                              │ Play matching stories
   └─ Archive at midnight                     │ Cycle with timing logic
```

### Geographic Tagging Schema

```json
{
  "id": "a7f3c2",
  "fact": "Earthquake measuring 5.2 struck near Los Angeles.",
  "confidence": 95,
  "sources": [
    {"name": "Reuters", "rating": 9.8},
    {"name": "AP", "rating": 9.6}
  ],
  "location": {
    "city": "Los Angeles",
    "state": "California",
    "country": "US",
    "scope": "local"
  },
  "verified_at": "2026-02-13T14:30:00Z",
  "tweeted": true
}
```

### Scope Values and Bubble-Up Behavior

| Scope | Meaning | Appears In |
|-------|---------|------------|
| `local` | Affects one city/county | City*, State, Country, Global |
| `state` | Affects entire state | State, Country, Global |
| `national` | Affects entire country | Country, Global |
| `international` | Affects multiple countries | Global only |
| `global` | Worldwide significance | Global only |

*City-level filtering is Phase 2.

### Region Filter Logic

```javascript
function storyMatchesRegion(story, region) {
  const loc = story.location;

  if (region === 'global') return true;
  if (loc.scope === 'global') return true;

  const [country, state] = region.split('-');
  const countryUpper = country.toUpperCase();

  // Country-level (e.g., "us")
  if (!state) {
    return loc.country === countryUpper;
  }

  // State-level (e.g., "us-california")
  const stateMatch = loc.state?.toLowerCase() === state.toLowerCase();
  const nationalMatch = loc.country === countryUpper &&
                        ['national', 'global'].includes(loc.scope);

  return stateMatch || nationalMatch;
}
```

---

## Claude Prompt Addition

Add to existing `CLAUDE_SYSTEM_PROMPT`:

```
LOCATION EXTRACTION:
For each headline, extract geographic information:
1. Identify the PRIMARY location where the event occurred or has impact
2. If multiple locations, choose the most specific one mentioned
3. Determine the SCOPE of impact:
   - "local" = affects one city/county/metro area
   - "state" = affects entire state/province
   - "national" = affects entire country
   - "international" = affects multiple specific countries
   - "global" = worldwide significance or affects 3+ continents

Add to your JSON response:
- "location_city": City name or null
- "location_state": State/province name or null
- "location_country": Country code (US, UK, CA, etc.) or null
- "location_scope": One of: local, state, national, international, global
```

---

## Config Changes

New `regions` section in config.json:

```json
{
  "regions": {
    "enabled": ["global"],
    "definitions": {
      "global": {
        "name": "JTF News Global",
        "filter": "all"
      },
      "us": {
        "name": "JTF News US",
        "filter": {"country": "US"}
      },
      "us-california": {
        "name": "JTF News California",
        "filter": {"country": "US", "state": "California"}
      },
      "uk": {
        "name": "JTF News UK",
        "filter": {"country": "UK"}
      }
    }
  }
}
```

---

## OBS Configuration

Same scene template, different browser source URLs:

| Stream | Browser Source URL |
|--------|-------------------|
| JTF News Global | `lower-third.html?region=global` |
| JTF News US | `lower-third.html?region=us` |
| JTF News California | `lower-third.html?region=us-california` |

Each regional stream requires:
- Separate OBS instance (or scene collection)
- Separate YouTube stream key
- Same background slideshow source
- Browser source handles audio playback

---

## Migration Plan

### Step 1: Add location extraction
- Update Claude prompt
- Store location in stories.json
- No visible changes to output
- Validate tagging accuracy for ~1 week

### Step 2: Restructure audio files
- Change from `current.wav` to `{id}.wav`
- Update main.py: check-before-generate
- Update lower-third.js: play from story ID

### Step 3: Add region parameter support
- Update lower-third.js to read `?region=` param
- Default to `global` (backwards compatible)
- Test in browser with different params

### Step 4: Launch first regional stream
- Set up second OBS instance
- Configure `?region=us`
- New YouTube channel "JTF News US"

### Rollback Safety
- Each step is independent
- Location tagging is optional metadata (stories work without it)
- Global stream always works as fallback

---

## Cost Analysis

| Cost | Impact |
|------|--------|
| Claude API | +20 tokens/story (~$0.00001 with Haiku) |
| ElevenLabs TTS | **Decreased** (generate once, reuse) |
| Scraping | No change |
| Storage | Negligible (more small audio files) |
| **Total** | ~Zero increase |

---

## Future Phases

### Phase 2: Local News Coverage
- Add local news sources (LA Times, SF Chronicle, etc.)
- Lower thresholds for local significance
- City-level filtering
- **Cost impact:** Significant increase (more API calls)

### Phase 3: Language Support
- Country-level streams in native language
- Separate TTS voice per language
- Translation via Claude

---

## Success Criteria

1. All stories have location tags within 1 week of deployment
2. Global stream continues unchanged
3. US stream shows only US-relevant stories
4. No increase in API costs
5. Add new region in <5 minutes (config + URL change only)

---

## Appendix: File Changes Summary

| File | Changes |
|------|---------|
| `main.py` | Add location to Claude prompt, generate `{id}.wav`, remove playback loop |
| `config.json` | Add `regions` section |
| `web/lower-third.js` | Add region filtering, playback control, audio playback |
| `web/lower-third.html` | Read `?region=` parameter |
| `stories.json` | Add `location` object to each story |
| `audio/` | Change from `current.wav` to `{id}.wav` files |
