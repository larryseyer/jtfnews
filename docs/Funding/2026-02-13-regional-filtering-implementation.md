# Regional Filtering Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add geographic tagging to all stories and enable regional stream filtering via URL parameters.

**Architecture:** Single `stories.json` with location tags. Browser source filters client-side based on `?region=` parameter. Audio files named by story hash for persistence.

**Tech Stack:** Python (main.py), JavaScript (lower-third.js), JSON (config.json, stories.json)

---

## Task 1: Add Location Extraction to Claude Prompt

**Files:**
- Modify: `main.py:473-539` (FACT_EXTRACTION_PROMPT)

**Step 1: Update the prompt to request location fields**

Add before the `OUTPUT FORMAT:` section (around line 530):

```python
LOCATION EXTRACTION:
For each headline, also extract geographic information:
1. Identify the PRIMARY location where the event occurred or has impact
2. If multiple locations, choose the most specific one mentioned
3. Determine the SCOPE of impact:
   - "local" = affects one city/county/metro area
   - "state" = affects entire state/province
   - "national" = affects entire country
   - "international" = affects multiple specific countries
   - "global" = worldwide significance or affects 3+ continents

LOCATION EXAMPLES:
- "Shooting at Sacramento high school" → city: "Sacramento", state: "California", country: "US", scope: "local"
- "Texas passes voting reform" → city: null, state: "Texas", country: "US", scope: "state"
- "President signs executive order" → city: null, state: null, country: "US", scope: "national"
- "UK and France sign treaty" → city: null, state: null, country: null, scope: "international"
- "WHO declares pandemic over" → city: null, state: null, country: null, scope: "global"
```

**Step 2: Update OUTPUT FORMAT section**

Replace the OUTPUT FORMAT section with:

```python
OUTPUT FORMAT:
Return a JSON object with:
- "fact": The clean, factual sentence (or "SKIP" if no verifiable facts)
- "confidence": Your confidence percentage (0-100) that this is purely factual
- "newsworthy": true or false based on the threshold criteria above
- "threshold_met": Which threshold it meets (e.g., "death/violence", "500+ affected", "$1M+ cost/investment", "law change", "border change", "scientific achievement", "humanitarian milestone", "head of state", "economic indicator", "international diplomacy") or "none"
- "location_city": City name or null
- "location_state": State/province name or null
- "location_country": Two-letter country code (US, UK, CA, FR, DE, etc.) or null
- "location_scope": One of: "local", "state", "national", "international", "global"

Headline to process:
```

**Step 3: Verify the change doesn't break existing parsing**

Run: `python -c "import main; print('Prompt loaded successfully')"`

Expected: No errors

**Step 4: Commit**

```bash
./bu.sh "Add location extraction to Claude prompt"
```

---

## Task 2: Add Keyword Fallback for Location Detection

**Files:**
- Modify: `main.py` (add after extract_fact function, around line 607)

**Step 1: Create keyword location lookup data**

Add after the `extract_fact` function:

```python
# =============================================================================
# LOCATION FALLBACK - Keyword-based location detection
# =============================================================================

# Common US state names and abbreviations
US_STATES = {
    "alabama": "Alabama", "alaska": "Alaska", "arizona": "Arizona", "arkansas": "Arkansas",
    "california": "California", "colorado": "Colorado", "connecticut": "Connecticut",
    "delaware": "Delaware", "florida": "Florida", "georgia": "Georgia", "hawaii": "Hawaii",
    "idaho": "Idaho", "illinois": "Illinois", "indiana": "Indiana", "iowa": "Iowa",
    "kansas": "Kansas", "kentucky": "Kentucky", "louisiana": "Louisiana", "maine": "Maine",
    "maryland": "Maryland", "massachusetts": "Massachusetts", "michigan": "Michigan",
    "minnesota": "Minnesota", "mississippi": "Mississippi", "missouri": "Missouri",
    "montana": "Montana", "nebraska": "Nebraska", "nevada": "Nevada", "new hampshire": "New Hampshire",
    "new jersey": "New Jersey", "new mexico": "New Mexico", "new york": "New York",
    "north carolina": "North Carolina", "north dakota": "North Dakota", "ohio": "Ohio",
    "oklahoma": "Oklahoma", "oregon": "Oregon", "pennsylvania": "Pennsylvania",
    "rhode island": "Rhode Island", "south carolina": "South Carolina", "south dakota": "South Dakota",
    "tennessee": "Tennessee", "texas": "Texas", "utah": "Utah", "vermont": "Vermont",
    "virginia": "Virginia", "washington": "Washington", "west virginia": "West Virginia",
    "wisconsin": "Wisconsin", "wyoming": "Wyoming", "district of columbia": "District of Columbia"
}

# Country indicators (keywords that suggest a specific country)
COUNTRY_KEYWORDS = {
    "US": ["united states", "u.s.", "american", "washington d.c.", "capitol hill", "congress",
           "senate", "house of representatives", "white house", "pentagon", "federal reserve"],
    "UK": ["united kingdom", "britain", "british", "england", "scotland", "wales", "london",
           "parliament", "downing street", "westminster"],
    "CA": ["canada", "canadian", "ottawa", "toronto", "vancouver"],
    "AU": ["australia", "australian", "sydney", "melbourne", "canberra"],
    "FR": ["france", "french", "paris", "macron"],
    "DE": ["germany", "german", "berlin", "merkel", "scholz"],
    "JP": ["japan", "japanese", "tokyo"],
    "CN": ["china", "chinese", "beijing", "shanghai"],
    "RU": ["russia", "russian", "moscow", "kremlin", "putin"],
    "IN": ["india", "indian", "new delhi", "mumbai"],
}


def extract_location_fallback(fact: str) -> dict:
    """Extract location from fact text using keyword matching.

    Used as fallback when Claude doesn't return location data.
    Returns: {"city": str|None, "state": str|None, "country": str|None, "scope": str}
    """
    fact_lower = fact.lower()
    location = {"city": None, "state": None, "country": None, "scope": "global"}

    # Check for US states first (most specific)
    for state_lower, state_proper in US_STATES.items():
        if state_lower in fact_lower:
            location["state"] = state_proper
            location["country"] = "US"
            location["scope"] = "state"
            break

    # Check for country keywords
    if not location["country"]:
        for country_code, keywords in COUNTRY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in fact_lower:
                    location["country"] = country_code
                    location["scope"] = "national"
                    break
            if location["country"]:
                break

    # If we found a state but not a more specific scope, it's state-level
    if location["state"] and location["scope"] == "global":
        location["scope"] = "state"

    # If we found a country but nothing more specific, it's national
    if location["country"] and location["scope"] == "global":
        location["scope"] = "national"

    return location
```

**Step 2: Test the fallback function**

Run: `python -c "from main import extract_location_fallback; print(extract_location_fallback('Earthquake strikes California'))"`

Expected: `{'city': None, 'state': 'California', 'country': 'US', 'scope': 'state'}`

**Step 3: Commit**

```bash
./bu.sh "Add keyword fallback for location detection"
```

---

## Task 3: Update stories.json Structure with Location

**Files:**
- Modify: `main.py:1551-1593` (update_stories_json function)

**Step 1: Update update_stories_json to include location**

Replace the `update_stories_json` function:

```python
def update_stories_json(fact: str, sources: list, audio_file: str = None, location: dict = None):
    """Update stories.json for the JS loop display."""
    stories_file = DATA_DIR / "stories.json"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Load existing stories
    stories = {"date": today, "stories": []}
    if stories_file.exists():
        try:
            with open(stories_file) as f:
                stories = json.load(f)
            # Reset if it's a new day
            if stories.get("date") != today:
                stories = {"date": today, "stories": []}
        except:
            pass

    # Format source info with evidence-based ratings
    source_text = " | ".join([
        f"{s['source_name']} - {get_display_rating(s['source_id'])}"
        for s in sources[:2]
    ])

    # Generate story ID from fact hash (for audio filename)
    story_id = hashlib.md5(fact.encode()).hexdigest()[:8]

    # Build story object
    story = {
        "id": story_id,
        "fact": fact,
        "source": source_text,
        "audio": f"../audio/{audio_file}" if audio_file else "../audio/current.mp3",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Add location if provided
    if location:
        story["location"] = {
            "city": location.get("location_city") or location.get("city"),
            "state": location.get("location_state") or location.get("state"),
            "country": location.get("location_country") or location.get("country"),
            "scope": location.get("location_scope") or location.get("scope", "global")
        }

    stories["stories"].append(story)

    # Write back
    with open(stories_file, 'w') as f:
        json.dump(stories, f, indent=2)

    # Also copy to gh-pages-dist for screensaver
    gh_pages_dir = BASE_DIR / "gh-pages-dist"
    if gh_pages_dir.exists():
        import shutil
        shutil.copy(stories_file, gh_pages_dir / "stories.json")

    # Update RSS feed
    update_rss_feed(fact, sources)

    # Update Alexa Flash Briefing feed
    update_alexa_feed(fact, sources)
```

**Step 2: Find all callers of update_stories_json and update them**

Search for: `update_stories_json(` in main.py

The function is called from:
- `append_daily_log` (line 1548)
- Potentially other places

**Step 3: Update append_daily_log to pass location**

Modify the `append_daily_log` function signature and call:

```python
def append_daily_log(fact: str, sources: list, audio_file: str = None, location: dict = None):
    """Append story to daily log."""
    # ... existing code ...

    # Also update stories.json for JS loop
    update_stories_json(fact, sources, audio_file, location)
```

**Step 4: Commit**

```bash
./bu.sh "Update stories.json structure with location fields"
```

---

## Task 4: Pass Location Through the Publishing Pipeline

**Files:**
- Modify: `main.py` (find publish_verified_story or equivalent function)

**Step 1: Find where stories are published**

Search for where `append_daily_log` is called and trace back to where `extract_fact` results are used.

**Step 2: Extract location from Claude result and pass through**

In the main processing loop (around line 2480-2590), after calling `extract_fact`:

```python
result = extract_fact(headline["text"])

# Extract location from result, with fallback
location = {
    "city": result.get("location_city"),
    "state": result.get("location_state"),
    "country": result.get("location_country"),
    "scope": result.get("location_scope", "global")
}

# If Claude didn't return location, use keyword fallback
if not location["country"] and not location["state"]:
    location = extract_location_fallback(result.get("fact", ""))
```

**Step 3: Pass location through to append_daily_log**

Wherever `append_daily_log` is called, add the location parameter:

```python
append_daily_log(fact, sources, audio_file, location)
```

**Step 4: Commit**

```bash
./bu.sh "Pass location through publishing pipeline"
```

---

## Task 5: Add Region Filtering to lower-third.js

**Files:**
- Modify: `web/lower-third.js`

**Step 1: Add region parameter parsing at top of file**

Add after the constant declarations (around line 25):

```javascript
// Region filtering
const urlParams = new URLSearchParams(window.location.search);
const REGION = urlParams.get('region') || 'global';
console.log(`Region filter: ${REGION}`);
```

**Step 2: Add storyMatchesRegion function**

Add after the `getFreshnessWeight` function (around line 97):

```javascript
/**
 * Check if a story matches the current region filter
 * Region format: "global", "us", "uk", "us-california", etc.
 */
function storyMatchesRegion(story, region) {
    // Global shows everything
    if (region === 'global') return true;

    // Stories without location data appear everywhere
    const loc = story.location;
    if (!loc) return true;

    // Global-scope stories appear everywhere
    if (loc.scope === 'global') return true;

    // Parse region: "us" or "us-california"
    const parts = region.split('-');
    const country = parts[0].toUpperCase();
    const state = parts[1] || null;

    // Country-level region (e.g., "us")
    if (!state) {
        return loc.country === country;
    }

    // State-level region (e.g., "us-california")
    // Include: this state's stories + national stories from this country
    const stateMatch = loc.state?.toLowerCase() === state.toLowerCase();
    const nationalMatch = loc.country === country &&
                          ['national', 'global'].includes(loc.scope);

    return stateMatch || nationalMatch;
}
```

**Step 3: Apply filter in loadStories function**

Modify the `loadStories` function to filter stories:

```javascript
async function loadStories() {
    try {
        const response = await fetch(STORIES_URL + '?t=' + Date.now());
        if (!response.ok) return;

        const data = await response.json();
        if (data.stories && data.stories.length > 0) {
            // Filter stories by region
            const filteredStories = data.stories.filter(s => storyMatchesRegion(s, REGION));

            const oldCount = stories.length;
            const newCount = filteredStories.length;

            // Check if stories changed or this is first load
            if (newCount !== oldCount || isFirstLoad) {
                console.log(`Stories ${isFirstLoad ? 'loaded' : 'changed'}: ${oldCount} -> ${newCount} (${data.stories.length} total, ${REGION} filter)`);
                stories = filteredStories;

                // Always reshuffle on first load, or if queue is nearly empty
                if (isFirstLoad || shuffledQueue.length <= 1) {
                    reshuffleForNewCycle();
                    isFirstLoad = false;
                }
            } else {
                stories = filteredStories;
            }
        }
    } catch (error) {
        console.log('No stories yet or error loading:', error.message);
    }
}
```

**Step 4: Test in browser**

Open: `file:///path/to/JTFNews/web/lower-third.html?region=us`

Check console for: `Region filter: us`

**Step 5: Commit**

```bash
./bu.sh "Add region filtering to lower-third.js"
```

---

## Task 6: Add Regions Configuration to config.json

**Files:**
- Modify: `config.json`

**Step 1: Add regions section to config.json**

Add after the `channel` section:

```json
"regions": {
  "enabled": ["global"],
  "definitions": {
    "global": {
      "name": "JTF News Global",
      "description": "All verified news worldwide"
    },
    "us": {
      "name": "JTF News US",
      "description": "United States national and local news"
    },
    "us-california": {
      "name": "JTF News California",
      "description": "California state and local news"
    },
    "us-texas": {
      "name": "JTF News Texas",
      "description": "Texas state and local news"
    },
    "uk": {
      "name": "JTF News UK",
      "description": "United Kingdom national and local news"
    }
  }
},
```

**Step 2: Commit**

```bash
./bu.sh "Add regions configuration to config.json"
```

---

## Task 7: Update Screensaver to Support Region Filtering

**Files:**
- Modify: `web/screensaver.html`

**Step 1: Check if screensaver has inline JS or external**

Read the file to determine structure.

**Step 2: Add region parameter support**

Add similar region filtering logic as lower-third.js.

**Step 3: Commit**

```bash
./bu.sh "Add region filtering to screensaver"
```

---

## Task 8: Validation and Testing

**Step 1: Start the service and verify location extraction**

```bash
./start.sh
```

Watch logs for: `location_city`, `location_state`, `location_country` in Claude responses.

**Step 2: Check stories.json has location data**

```bash
cat data/stories.json | python -m json.tool | grep -A5 "location"
```

**Step 3: Test region filtering in browser**

Open: `web/lower-third.html?region=us`

Verify only US stories appear (or all if no stories have location yet).

**Step 4: Test fallback for stories without Claude location**

Add a test headline manually and verify keyword fallback works.

---

## Summary of Changes

| File | Changes |
|------|---------|
| `main.py` | Add location to Claude prompt, add keyword fallback, pass location through pipeline |
| `web/lower-third.js` | Add region parameter parsing, add storyMatchesRegion function, filter in loadStories |
| `config.json` | Add regions configuration section |
| `web/screensaver.html` | Add region filtering support |

## Rollback Plan

Each task is independent. If issues occur:

1. **Prompt change fails**: Revert FACT_EXTRACTION_PROMPT to original
2. **Fallback breaks**: Remove extract_location_fallback function
3. **stories.json breaks**: Clear stories.json, stories rebuild from daily log
4. **JS filtering breaks**: Remove region parameter parsing, default to showing all

The global stream continues unchanged throughout - regional filtering is additive.
