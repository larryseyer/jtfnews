# JTF News Operations Dashboard Plan

## Summary
Add live operational cost tracking to the main JTF News page (**jtfnews.com**) to show donors exactly where their money goes, plus a detailed monitor page for system health.

## Two Components

### 1. Main Page Cost Widget (Public - for donors)
Embedded in index.html Support section showing:
- Time-based costs: Today / Week / Month / Year
- Service breakdown: Claude AI, TTS, SMS percentages
- Per-story cost: "Each verified fact costs ~$0.04"

### 2. Monitor Page (Public - for transparency)
Full dashboard at /monitor.html showing:
- All costs (detailed)
- System status, queue, sources
- Errors and health metrics

---

## Phase 1: Backend Data Collection (main.py)

### 1.1 Add API Cost Tracking (~50 lines)
Location: After line 85 (configuration section)

```python
# API cost rates (as of Feb 2026)
API_COSTS = {
    "claude": {"input_per_1k": 0.00025, "output_per_1k": 0.00125},  # Haiku 4.5
    "elevenlabs": {"per_character": 0.00003},  # ~$0.30 per 10k chars
    "twilio": {"per_sms": 0.0079}
}
STARTUP_TIME = datetime.now(timezone.utc)
```

New function `log_api_usage(service, usage)`:
- Appends to `data/api_usage_YYYY-MM-DD.json`
- Updates running totals

### 1.2 Instrument API Calls
- **extract_fact()**: Log Claude input/output tokens
- **generate_tts()**: Log character count
- **send_alert()**: Log SMS count

### 1.3 Cost Aggregation Functions (~40 lines)
```python
def get_costs_summary():
    """Return costs for today, week, month, year."""
    return {
        "today": calculate_day_cost(today),
        "week": sum([calculate_day_cost(d) for d in last_7_days]),
        "month": sum([calculate_day_cost(d) for d in current_month]),
        "year_estimate": month_cost * 12,
        "per_story": total_cost / stories_published,
        "breakdown": {
            "claude": {"amount": X, "percent": Y},
            "elevenlabs": {"amount": X, "percent": Y},
            "twilio": {"amount": X, "percent": Y}
        }
    }
```

### 1.4 Write Monitor Data (~60 lines)
New function `write_monitor_data()`:
- Writes `data/monitor.json` with full system data
- Includes cost summary for main page widget

### 1.5 Sync to gh-pages
- Copy `data/monitor.json` to `gh-pages-dist/data/monitor.json`
- Called at end of each cycle

---

## Phase 2: Main Page Cost Widget

### 2.1 Update gh-pages-dist/index.html
Add a "Live Operating Costs" section above the Support/Sponsors section:

```html
<h2>Live Operating Costs</h2>
<p>JTF News runs on AI and cloud services. Here's what it costs:</p>

<div id="costs-widget">
    <div class="cost-periods">
        <div class="cost-item">
            <span class="label">Today</span>
            <span class="value" id="cost-today">$--</span>
        </div>
        <div class="cost-item">
            <span class="label">This Week</span>
            <span class="value" id="cost-week">$--</span>
        </div>
        <div class="cost-item">
            <span class="label">This Month</span>
            <span class="value" id="cost-month">$--</span>
        </div>
        <div class="cost-item">
            <span class="label">Est. Annual</span>
            <span class="value" id="cost-year">$--</span>
        </div>
    </div>

    <div class="cost-breakdown">
        <h4>Where It Goes</h4>
        <div class="breakdown-bar">
            <div class="bar-segment claude" style="width: 72%">Claude AI</div>
            <div class="bar-segment tts" style="width: 26%">Voice</div>
            <div class="bar-segment sms" style="width: 2%"></div>
        </div>
    </div>

    <p class="per-story">Each verified fact costs approximately <strong id="cost-per-story">$0.04</strong></p>

    <p class="last-updated">Updated <span id="costs-updated">--</span></p>
</div>

<h2>Support</h2>
<p>Your donation keeps the facts flowing.</p>
<iframe src="https://github.com/sponsors/larryseyer/card" ...></iframe>
```

### 2.2 Add CSS for Cost Widget (~50 lines)
- Match existing dark theme (#0f172a background, #d4af37 gold accent)
- Responsive grid for cost periods
- Colored bar chart for breakdown (Claude=blue, TTS=green, SMS=gray)
- Clean, minimal styling

### 2.3 Add JS to Fetch Costs (~30 lines)
```javascript
async function updateCosts() {
    const response = await fetch('data/monitor.json?t=' + Date.now());
    const data = await response.json();

    document.getElementById('cost-today').textContent = '$' + data.costs.today.toFixed(2);
    document.getElementById('cost-week').textContent = '$' + data.costs.week.toFixed(2);
    // ... etc
}

// Update every 5 minutes
setInterval(updateCosts, 300000);
updateCosts();
```

---

## Phase 3: Full Monitor Page (gh-pages-dist/monitor.html)

### 3.1 Dashboard Layout
Full operational dashboard showing:
- **Costs Card**: All time periods + detailed service breakdown
- **System Status Card**: Uptime, next cycle, stream health
- **Current Cycle Card**: Headlines scraped/processed, stories published
- **Queue Card**: Size, oldest item age
- **Source Health Card**: Success/failure counts, blocked sources
- **Errors Card**: Recent warnings/errors list

### 3.2 Files
- `gh-pages-dist/monitor.html` (~80 lines)
- `gh-pages-dist/monitor.css` (~200 lines)
- `gh-pages-dist/monitor.js` (~250 lines)

---

## Phase 4: Data Files

### data/monitor.json (synced to gh-pages each cycle)
```json
{
  "timestamp": "2026-02-13T12:45:00Z",
  "uptime_start": "2026-02-13T06:30:00Z",

  "costs": {
    "today": 1.31,
    "week": 8.45,
    "month": 38.20,
    "year_estimate": 458.40,
    "per_story": 0.037,
    "breakdown": {
      "claude": {"amount": 0.94, "percent": 72},
      "elevenlabs": {"amount": 0.34, "percent": 26},
      "twilio": {"amount": 0.03, "percent": 2}
    },
    "stories_today": 35
  },

  "cycle": {
    "number": 42,
    "duration_seconds": 45,
    "headlines_scraped": 268,
    "headlines_processed": 15,
    "stories_published": 2,
    "stories_queued": 3
  },

  "queue": {"size": 47, "oldest_item_age_hours": 18.5},

  "sources": {
    "total": 32,
    "successful": 30,
    "failed": ["scmp", "independent"]
  },

  "recent_errors": [
    {"timestamp": "2026-02-13T12:30:15Z", "level": "WARNING", "message": "robots.txt blocks: scmp.com"}
  ],

  "status": {
    "state": "running",
    "stream_health": "online",
    "kill_switch": false
  }
}
```

### data/api_usage_YYYY-MM-DD.json (local only)
Detailed per-call logs for historical analysis.

---

## File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `main.py` | Modify | Add API tracking, cost aggregation, monitor data writer |
| `gh-pages-dist/index.html` | Modify | Add Live Operating Costs widget |
| `gh-pages-dist/monitor.html` | Create | Full dashboard page |
| `gh-pages-dist/monitor.css` | Create | Dashboard styles |
| `gh-pages-dist/monitor.js` | Create | Dashboard logic |
| `gh-pages-dist/data/monitor.json` | Create (auto) | Synced each cycle |

---

## User Experience

### For Donors (index.html)
1. Visit jtfnews.com
2. See "Live Operating Costs" section
3. Understand exactly what their donation funds
4. See per-story cost ("my $5 funds ~130 verified facts")
5. Click GitHub Sponsors to donate

### For Operators (monitor.html)
1. Visit jtfnews.com/monitor.html
2. See full system status at a glance
3. Check for errors or issues
4. Monitor costs and source health

---

## Verification Steps

1. **Backend test**: Run main.py, verify `data/monitor.json` created with cost data
2. **Main page test**: Open index.html, verify cost widget displays real numbers
3. **Monitor test**: Open monitor.html, verify full dashboard works
4. **Deploy test**: Push to gh-pages, verify live at jtfnews.com
5. **Update test**: Wait for cycle, confirm numbers update

---

## Estimated Scope

- **main.py changes**: ~150 lines added
- **index.html changes**: ~50 lines added
- **New monitor page files**: ~530 lines total
- **Total new code**: ~730 lines
- **Risk level**: Low (additive changes only)

---

## Fundraising Impact

The cost widget creates a **transparent funding narrative**:

> "JTF News costs about $1.30/day to run. Each verified fact costs 4 cents.
> Your $5 donation keeps the facts flowing for almost 4 days."

This concrete, real-time data makes the funding ask tangible and trustworthy - perfectly aligned with JTF's "just the facts" philosophy.
