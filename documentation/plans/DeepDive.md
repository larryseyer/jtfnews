# JTF News Transparency Pages - Complete Implementation Plan

**Created:** 2026-02-15
**Status:** Ready for Implementation
**Scope:** Three new public pages + data pipeline additions + navigation updates

---

## Executive Summary

Add three transparency pages to the JTF News public website (GitHub Pages):

1. **Story Archive Browser** (`archive.html`) - Browse all stories ever published, filter by date and source
2. **Source Ratings Page** (`sources.html`) - View all 17 sources with ratings and expandable ownership details
3. **Corrections Log** (`corrections.html`) - View all corrections/retractions with full context

These pages embody the JTF philosophy: "The methodology belongs to no one. It serves everyone."

---

## Requirements Summary

| Page | Data Source | Filters | Refresh |
|------|-------------|---------|---------|
| Story Archive | `stories.json` + `archive/*.gz` | Date range + Source | Cycle-sync (30 min) |
| Source Ratings | New `sources.json` | Tier (1/2/3) | Cycle-sync (30 min) |
| Corrections | `corrections.json` | None (chronological) | Cycle-sync (30 min) |

**Navigation:** Add links to all three pages in `index.html` main navigation.

---

## Part 1: Data Pipeline Changes (main.py)

### 1.1 New Function: `export_sources_json()`

**Location:** Add after `update_stories_json()` (around line 1880)

**Purpose:** Extract source data from `config.json` and write to `docs/sources.json` for public consumption.

**Implementation:**

```python
def export_sources_json():
    """Export source ratings and ownership data to docs for public transparency pages."""
    try:
        config_file = BASE_DIR / "config.json"
        if not config_file.exists():
            log_event("SOURCES_EXPORT", "config.json not found", level="warning")
            return

        with open(config_file, 'r') as f:
            config = json.load(f)

        # Extract only the fields needed for public display
        public_sources = []
        for source in config.get("sources", []):
            public_source = {
                "id": source.get("id"),
                "name": source.get("name"),
                "tier": source.get("tier"),
                "control_type": source.get("control_type"),
                "owner_display": source.get("owner_display"),
                "institutional_holders": source.get("institutional_holders", []),
                "ratings": source.get("ratings", {}),
                "url": source.get("url", ""),
                "rss_url": source.get("rss_url", "")
            }
            public_sources.append(public_source)

        # Build the export object
        export_data = {
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "last_ownership_audit": config.get("last_ownership_audit", "Unknown"),
            "ratings_methodology": config.get("ratings_methodology", {}),
            "total_sources": len(public_sources),
            "sources": public_sources
        }

        # Write to docs
        docs_dir = BASE_DIR / "docs"
        if docs_dir.exists():
            sources_file = docs_dir / "sources.json"
            with open(sources_file, 'w') as f:
                json.dump(export_data, f, indent=2)
            log_event("SOURCES_EXPORT", f"Exported {len(public_sources)} sources to docs")

    except Exception as e:
        log_event("SOURCES_EXPORT", f"Error exporting sources: {e}", level="error")
```

### 1.2 Call `export_sources_json()` in the Main Loop

**Location:** In the `run_cycle()` function, after `update_stories_json()` is called.

**Add this line:**
```python
export_sources_json()
```

### 1.3 Expected `sources.json` Output Format

```json
{
  "last_updated": "2026-02-15T06:30:00+00:00",
  "last_ownership_audit": "2026-Q1",
  "ratings_methodology": {
    "version": "1.0",
    "formula": "Rating = (verification_successes / (verification_successes + failures)) * 10",
    "success_definition": "Story from source A was verified by unrelated source B",
    "failure_definition": "Story expired from queue after 24 hours without 2nd source verification",
    "min_data_points": 10
  },
  "total_sources": 30,
  "sources": [
    {
      "id": "reuters",
      "name": "Reuters",
      "tier": 1,
      "control_type": "corporate",
      "owner_display": "Thomson Reuters (Woodbridge 64.2%)",
      "institutional_holders": [
        {"name": "Woodbridge Company Limited", "percent": 64.2},
        {"name": "Vanguard Group", "percent": 4.1},
        {"name": "BlackRock", "percent": 3.2}
      ],
      "ratings": {
        "accuracy": 9.8,
        "bias": 0.1,
        "speed": 9.8,
        "consensus": 9.8
      },
      "url": "https://www.reuters.com",
      "rss_url": "https://www.reuters.com/rssFeed/..."
    }
  ]
}
```

---

## Part 2: Story Archive Browser (`archive.html`)

### 2.1 Overview

A page where users can browse ALL stories ever published by JTF News, with filtering by date range and source name.

### 2.2 Data Sources

1. **Today's stories:** Fetch from `stories.json`
2. **Historical stories:** Fetch from `archive/YYYY/YYYY-MM-DD.txt.gz` files

### 2.3 Archive File Format

Each daily archive is a gzipped text file with one story per line:
```
[timestamp]|[story_id]|[fact]|[sources]|[correction_marker]
```

Example:
```
2026-02-14T10:30:00Z|2026-02-14-001|Secretary of State...|BBC News 9.5*|9.0 · Reuters 9.9*|9.5|
2026-02-14T14:45:00Z|2026-02-14-002|The European Central Bank...|Financial Times 9.3*|8.8 · Bloomberg 9.6*|9.2|CORRECTED
```

### 2.4 JavaScript Architecture

**Key challenge:** Gzipped files need decompression in the browser.

**Solution:** Use the `pako` library (lightweight, MIT licensed, ~45KB minified)
- CDN: `https://cdnjs.cloudflare.com/ajax/libs/pako/2.1.0/pako.min.js`

**Pseudocode:**

```javascript
// 1. Build list of available archive dates
async function getAvailableArchiveDates() {
    // Fetch archive/index.json (we'll create this) or scan archive folders
    // Returns array of date strings: ["2026-02-14", "2026-02-13", ...]
}

// 2. Load stories for a date range
async function loadStoriesForDateRange(startDate, endDate) {
    const stories = [];

    // If today is in range, load from stories.json
    if (isToday(endDate)) {
        const todayStories = await fetch('stories.json').then(r => r.json());
        stories.push(...todayStories.stories);
    }

    // Load historical archives
    for (const date of getDatesInRange(startDate, endDate)) {
        if (isToday(date)) continue;

        const year = date.substring(0, 4);
        const archiveUrl = `archive/${year}/${date}.txt.gz`;

        try {
            const response = await fetch(archiveUrl);
            const arrayBuffer = await response.arrayBuffer();
            const decompressed = pako.ungzip(new Uint8Array(arrayBuffer), {to: 'string'});

            // Parse lines into story objects
            const lines = decompressed.split('\n').filter(line => line.trim());
            for (const line of lines) {
                const [timestamp, id, fact, sources, correction] = line.split('|');
                stories.push({
                    published_at: timestamp,
                    id: id,
                    fact: fact,
                    source: sources,
                    corrected: correction === 'CORRECTED'
                });
            }
        } catch (e) {
            console.warn(`No archive for ${date}`);
        }
    }

    return stories;
}

// 3. Filter by source
function filterBySource(stories, sourceName) {
    if (!sourceName) return stories;
    return stories.filter(s => s.source.toLowerCase().includes(sourceName.toLowerCase()));
}
```

### 2.5 UI Components

```
┌─────────────────────────────────────────────────────────────────┐
│  JTF NEWS - STORY ARCHIVE                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Date Range: [Start Date ▼] to [End Date ▼]   Source: [_____]  │
│                                                                 │
│  [Apply Filters]                                                │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  Showing 47 stories from Feb 10 - Feb 15, 2026                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Feb 15, 2026 • 10:30 AM                                 │   │
│  │                                                         │   │
│  │ Secretary of State Marco Rubio announced the United    │   │
│  │ States will impose new sanctions on...                  │   │
│  │                                                         │   │
│  │ Sources: BBC News 9.5|9.0 · Reuters 9.9|9.5            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Feb 15, 2026 • 9:15 AM                      [CORRECTED] │   │
│  │ ...                                                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  [Load More Stories]                                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.6 Archive Index File

**New file needed:** `docs/archive/index.json`

This file lists all available archive dates so the browser knows what's available without scanning directories.

**Format:**
```json
{
  "last_updated": "2026-02-15T00:00:00Z",
  "dates": [
    "2026-02-14",
    "2026-02-13",
    "2026-02-12"
  ]
}
```

**main.py addition:** Update `archive_daily_log()` to also update this index file when creating new archives.

```python
def update_archive_index():
    """Update archive/index.json with list of available archive dates."""
    archive_dir = BASE_DIR / "docs" / "archive"
    if not archive_dir.exists():
        return

    dates = []
    for year_dir in sorted(archive_dir.iterdir(), reverse=True):
        if year_dir.is_dir() and year_dir.name.isdigit():
            for archive_file in sorted(year_dir.glob("*.txt.gz"), reverse=True):
                date_str = archive_file.stem.replace(".txt", "")
                dates.append(date_str)

    index_data = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "dates": dates
    }

    with open(archive_dir / "index.json", 'w') as f:
        json.dump(index_data, f, indent=2)
```

---

## Part 3: Source Ratings Page (`sources.html`)

### 3.1 Overview

A page displaying all 30 news sources with their:
- Tier level (1/2/3)
- Accuracy, Bias, Speed, Consensus ratings
- Expandable ownership details (institutional holders with percentages)
- Control type (corporate, non-profit, government, etc.)

### 3.2 UI Design

```
┌─────────────────────────────────────────────────────────────────┐
│  JTF NEWS - SOURCE RATINGS                                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  How We Rate Sources                                            │
│  ─────────────────────────────────────────────────────────────  │
│  Ratings based on verification success rate. A "success" is    │
│  when a story from this source is independently verified by    │
│  an unrelated source. * indicates limited data (<10 stories).  │
│                                                                 │
│  Last ownership audit: Q1 2026                                  │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  Filter by Tier:  [All] [Tier 1] [Tier 2] [Tier 3]             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  TIER 1 - PRIMARY SOURCES (8)                                   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Reuters                                    [Corporate] │   │
│  │  ─────────────────────────────────────────────────────  │   │
│  │  Accuracy: 9.8   Bias: 0.1   Speed: 9.8   Consensus: 9.8│   │
│  │                                                         │   │
│  │  ▶ Ownership Details                                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Associated Press                           [Non-Profit]│   │
│  │  ─────────────────────────────────────────────────────  │   │
│  │  Accuracy: 9.7   Bias: 0.2   Speed: 9.6   Consensus: 9.7│   │
│  │                                                         │   │
│  │  ▼ Ownership Details                                    │   │
│  │  ┌───────────────────────────────────────────────────┐  │   │
│  │  │ Member-owned cooperative                          │  │   │
│  │  │ • 1,400 member newspapers (collective ownership)  │  │   │
│  │  │ • No single controlling shareholder               │  │   │
│  │  └───────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  TIER 2 - SECONDARY SOURCES (12)                                │
│  ...                                                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 JavaScript Implementation

```javascript
async function loadSources() {
    const response = await fetch('sources.json?t=' + Date.now());
    const data = await response.json();

    // Group by tier
    const tier1 = data.sources.filter(s => s.tier === 1);
    const tier2 = data.sources.filter(s => s.tier === 2);
    const tier3 = data.sources.filter(s => s.tier === 3);

    renderTierSection('tier-1-container', 'TIER 1 - PRIMARY SOURCES', tier1);
    renderTierSection('tier-2-container', 'TIER 2 - SECONDARY SOURCES', tier2);
    renderTierSection('tier-3-container', 'TIER 3 - TERTIARY SOURCES', tier3);

    // Update metadata
    document.getElementById('last-audit').textContent = data.last_ownership_audit;
    document.getElementById('total-sources').textContent = data.total_sources;
}

function renderSourceCard(source) {
    return `
        <div class="source-card" data-tier="${source.tier}">
            <div class="source-header">
                <h3 class="source-name">${source.name}</h3>
                <span class="control-type control-${source.control_type}">${source.control_type}</span>
            </div>
            <div class="source-ratings">
                <span class="rating">Accuracy: <strong>${source.ratings.accuracy}</strong></span>
                <span class="rating">Bias: <strong>${source.ratings.bias}</strong></span>
                <span class="rating">Speed: <strong>${source.ratings.speed}</strong></span>
                <span class="rating">Consensus: <strong>${source.ratings.consensus}</strong></span>
            </div>
            <details class="ownership-details">
                <summary>Ownership Details</summary>
                <div class="ownership-content">
                    <p class="owner-display">${source.owner_display}</p>
                    <ul class="institutional-holders">
                        ${source.institutional_holders.map(h =>
                            `<li>${h.name}: <strong>${h.percent}%</strong></li>`
                        ).join('')}
                    </ul>
                </div>
            </details>
        </div>
    `;
}
```

### 3.4 Styling Notes

- Use the existing glassmorphism design from `monitor.html`
- Color-code control types:
  - Corporate: Blue badge
  - Non-profit: Green badge
  - Government: Yellow badge
  - Cooperative: Purple badge
- Rating numbers should be large and prominent
- Use `<details>/<summary>` for expandable ownership (native, accessible, no JS needed)

---

## Part 4: Corrections Log (`corrections.html`)

### 4.1 Overview

A simple chronological list of all corrections/retractions, showing:
- Original fact
- Corrected fact
- Reason for correction
- Timestamps (original publish, correction time)

### 4.2 Data Source

`corrections.json` already exists and is synced by main.py.

**Expected format:**
```json
{
  "last_updated": "2026-02-15T06:30:00+00:00",
  "corrections": [
    {
      "story_id": "2026-02-15-001",
      "original_fact": "The Federal Reserve raised interest rates by 0.5%...",
      "corrected_fact": "The Federal Reserve raised interest rates by 0.25%...",
      "correction_reason": "Original reporting from Source A incorrectly stated the rate increase amount. Verified via Federal Reserve official press release.",
      "published_at": "2026-02-15T10:30:00+00:00",
      "corrected_at": "2026-02-15T14:45:00+00:00",
      "sources": ["Federal Reserve Press Release", "Reuters"]
    }
  ]
}
```

### 4.3 UI Design

```
┌─────────────────────────────────────────────────────────────────┐
│  JTF NEWS - CORRECTIONS LOG                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Our Commitment to Accuracy                                     │
│  ─────────────────────────────────────────────────────────────  │
│  When a fact passes our two-source verification but is later   │
│  proven false, we issue a correction within the next cycle.    │
│  Original statements are marked, never silently deleted.       │
│  Corrections receive the same prominence as the original.      │
│                                                                 │
│  Total corrections: 3                                           │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  CORRECTION #2026-02-15-001                             │   │
│  │  Corrected: Feb 15, 2026 at 2:45 PM                     │   │
│  │  ─────────────────────────────────────────────────────  │   │
│  │                                                         │   │
│  │  ORIGINAL (Published Feb 15, 2026 at 10:30 AM):         │   │
│  │  ┌───────────────────────────────────────────────────┐  │   │
│  │  │ The Federal Reserve raised interest rates by 0.5% │  │   │
│  │  │ following their February meeting...               │  │   │
│  │  └───────────────────────────────────────────────────┘  │   │
│  │                                                         │   │
│  │  CORRECTED:                                             │   │
│  │  ┌───────────────────────────────────────────────────┐  │   │
│  │  │ The Federal Reserve raised interest rates by 0.25%│  │   │
│  │  │ following their February meeting...               │  │   │
│  │  └───────────────────────────────────────────────────┘  │   │
│  │                                                         │   │
│  │  REASON:                                                │   │
│  │  Original reporting from Source A incorrectly stated   │   │
│  │  the rate increase amount. Verified via Federal        │   │
│  │  Reserve official press release.                       │   │
│  │                                                         │   │
│  │  Verification Sources: Federal Reserve Press Release,  │   │
│  │  Reuters                                                │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  No corrections? That's a good thing. It means our two-source  │
│  verification is working.                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.4 Empty State

When `corrections.json` is empty, display:

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  ✓ No corrections to date                                       │
│                                                                 │
│  This means our two-source verification process is working.    │
│  When we do make a mistake, it will be documented here with    │
│  full transparency.                                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Part 5: Navigation Updates (`index.html`)

### 5.1 Current Navigation Structure

The existing nav in `index.html` includes:
- Watch Live (YouTube)
- How It Works
- Whitepaper
- Operations Dashboard

### 5.2 Updated Navigation

Add three new links after "Operations Dashboard":

```html
<nav class="main-nav">
    <a href="https://www.youtube.com/@JTFNewsLive" class="nav-link">Watch Live</a>
    <a href="how-it-works.html" class="nav-link">How It Works</a>
    <a href="whitepaper.html" class="nav-link">Whitepaper</a>
    <a href="monitor.html" class="nav-link">Operations</a>
    <a href="archive.html" class="nav-link">Story Archive</a>
    <a href="sources.html" class="nav-link">Source Ratings</a>
    <a href="corrections.html" class="nav-link">Corrections</a>
</nav>
```

### 5.3 Mobile Considerations

The existing nav uses flexbox with wrap. Test that 7 items still look good on mobile. If not, consider:
- Hamburger menu for mobile
- Two-row nav
- Collapsing "Transparency" items under a dropdown

---

## Part 6: Shared Components

### 6.1 Cycle-Sync Auto-Refresh

All three pages should implement the same auto-refresh pattern:

```javascript
let lastKnownRefreshAt = null;

async function checkForCycleRefresh() {
    try {
        const response = await fetch('monitor.json?t=' + Date.now());
        const data = await response.json();
        const currentRefreshAt = data.web_refresh_at;

        if (lastKnownRefreshAt === null) {
            lastKnownRefreshAt = currentRefreshAt;
            return;
        }

        if (currentRefreshAt !== lastKnownRefreshAt) {
            console.log('[Cycle Refresh] New cycle detected, refreshing page...');
            location.reload();
        }
    } catch (e) {
        console.warn('Failed to check for cycle refresh:', e);
    }
}

// Check every 30 seconds
setInterval(checkForCycleRefresh, 30000);

// Initial check
checkForCycleRefresh();
```

### 6.2 Shared CSS

Create or extend `shared.css` with common components:

```css
/* Color Palette */
:root {
    --bg-primary: #0f172a;
    --bg-secondary: #1e293b;
    --bg-card: rgba(30, 41, 59, 0.6);
    --gold: #d4af37;
    --blue: #60a5fa;
    --gray: #94a3b8;
    --green: #22c55e;
    --red: #ef4444;
    --yellow: #eab308;
    --border: rgba(255, 255, 255, 0.1);
}

/* Glass Card */
.card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
    backdrop-filter: blur(40px) saturate(180%);
    -webkit-backdrop-filter: blur(40px) saturate(180%);
}

/* Status Badges */
.badge {
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.badge-corporate { background: rgba(96, 165, 250, 0.2); color: var(--blue); }
.badge-nonprofit { background: rgba(34, 197, 94, 0.2); color: var(--green); }
.badge-government { background: rgba(234, 179, 8, 0.2); color: var(--yellow); }
.badge-corrected { background: rgba(239, 68, 68, 0.2); color: var(--red); }

/* Section Headers */
.section-header {
    color: var(--gold);
    font-size: 14px;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 20px;
    padding-bottom: 10px;
    border-bottom: 1px solid var(--border);
}
```

### 6.3 Header/Footer Components

Each page should include consistent header/footer:

**Header:**
```html
<header class="page-header">
    <a href="index.html" class="logo">JTF NEWS</a>
    <nav class="main-nav">
        <!-- Navigation links -->
    </nav>
</header>
```

**Footer:**
```html
<footer class="page-footer">
    <p>JTF News - Just the Facts</p>
    <p>Two sources. Different owners. Strip the adjectives. State the facts. Stop.</p>
    <p class="footer-links">
        <a href="feed.xml">RSS Feed</a> ·
        <a href="https://github.com/JTFNews/jtfnews">GitHub</a> ·
        <a href="whitepaper.html">Whitepaper</a>
    </p>
</footer>
```

---

## Part 7: Implementation Order

### Phase 1: Data Pipeline (main.py)
1. Add `export_sources_json()` function
2. Call it in `run_cycle()` after `update_stories_json()`
3. Add `update_archive_index()` function
4. Call it in `archive_daily_log()` after creating gzip
5. Test: Run a cycle and verify `sources.json` and `archive/index.json` are created

### Phase 2: Source Ratings Page (simplest, no decompression)
1. Create `sources.html` with full HTML structure
2. Add JavaScript to fetch and render `sources.json`
3. Implement expandable ownership details
4. Add tier filtering
5. Add cycle-sync refresh
6. Test: Open page, verify all 17 sources display correctly

### Phase 3: Corrections Page (simple, may be empty)
1. Create `corrections.html` with full HTML structure
2. Add JavaScript to fetch and render `corrections.json`
3. Handle empty state gracefully
4. Add cycle-sync refresh
5. Test: Open page, verify empty state OR corrections display

### Phase 4: Story Archive Browser (most complex)
1. Create `archive.html` with full HTML structure
2. Include pako.js for gzip decompression
3. Implement date range picker
4. Implement source filter
5. Load and parse today's `stories.json`
6. Load and decompress historical archives
7. Add pagination ("Load More")
8. Add cycle-sync refresh
9. Test: Open page, select date range, verify stories load

### Phase 5: Navigation & Integration
1. Update `index.html` nav with three new links
2. Update any other pages that share the nav (how-it-works.html, etc.)
3. Test: Click through all nav links, verify navigation works

### Phase 6: Final Testing
1. Run full cycle on develop machine
2. Verify all JSON files update correctly
3. Open each page, verify data displays
4. Wait for cycle refresh, verify pages auto-update
5. Test on mobile viewport
6. Run `./bu.sh` to deploy to GitHub Pages
7. Verify live site at https://jtfnews.org/

---

## Part 8: File Checklist

### Files to Create
- [ ] `docs/archive.html`
- [ ] `docs/sources.html`
- [ ] `docs/corrections.html`
- [ ] `docs/archive/index.json` (generated by main.py)
- [ ] `docs/sources.json` (generated by main.py)

### Files to Modify
- [ ] `main.py` - Add `export_sources_json()` and `update_archive_index()`
- [ ] `docs/index.html` - Update navigation

### External Dependencies
- [ ] pako.js (for archive.html gzip decompression)
  - CDN: `https://cdnjs.cloudflare.com/ajax/libs/pako/2.1.0/pako.min.js`
  - Or download and host locally in `docs/js/pako.min.js`

---

## Part 9: Verification Checklist

After implementation, verify:

### Data Pipeline
- [ ] `sources.json` is created in `docs/` after cycle runs
- [ ] `sources.json` contains all 17 sources with correct data
- [ ] `archive/index.json` lists all available archive dates
- [ ] Data updates every 30 minutes (cycle-sync)

### Story Archive Page
- [ ] Page loads without errors
- [ ] Today's stories appear from `stories.json`
- [ ] Historical stories load when date range selected
- [ ] Source filter works correctly
- [ ] "CORRECTED" badge shows on corrected stories
- [ ] Page auto-refreshes on new cycle

### Source Ratings Page
- [ ] All 17 sources display
- [ ] Ratings are accurate (match config.json)
- [ ] Ownership expands/collapses correctly
- [ ] Tier filter works
- [ ] Control type badges display correctly
- [ ] Page auto-refreshes on new cycle

### Corrections Page
- [ ] Empty state displays correctly when no corrections
- [ ] Corrections display with all fields when present
- [ ] Original vs corrected facts clearly distinguished
- [ ] Page auto-refreshes on new cycle

### Navigation
- [ ] All three new links appear in nav
- [ ] Links work on desktop
- [ ] Links work on mobile
- [ ] Active page is highlighted (if applicable)

---

## Appendix A: Color Reference

From existing pages:

| Purpose | Color | Hex |
|---------|-------|-----|
| Background (primary) | Dark slate | `#0f172a` |
| Background (cards) | Lighter slate | `#1e293b` |
| Headings/Gold accent | Gold | `#d4af37` |
| Links | Blue | `#60a5fa` |
| Secondary text | Gray | `#94a3b8` |
| Success/Online | Green | `#22c55e` |
| Error/Offline | Red | `#ef4444` |
| Warning | Yellow | `#eab308` |
| Borders | Semi-transparent white | `rgba(255,255,255,0.1)` |

---

## Appendix B: Rating Display Format

Per existing convention:
- Display format: `Accuracy|Bias` (e.g., `9.8|0.1`)
- Asterisk (*) indicates cold-start (<10 data points)
- Example: `9.5*|9.0` means accuracy 9.5 with limited data, bias 9.0

---

## Appendix C: Archive Line Parser

Python reference for archive file format (for understanding):

```python
def format_archive_line(story):
    correction_marker = "CORRECTED" if story.get("corrected") else ""
    return f"{story['published_at']}|{story['id']}|{story['fact']}|{story['source']}|{correction_marker}"

def parse_archive_line(line):
    parts = line.strip().split('|')
    return {
        "published_at": parts[0],
        "id": parts[1],
        "fact": parts[2],
        "source": parts[3],
        "corrected": len(parts) > 4 and parts[4] == "CORRECTED"
    }
```

---

*End of Implementation Plan*
