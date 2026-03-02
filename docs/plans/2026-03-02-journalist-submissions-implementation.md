# Journalist Submission System — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a system for independent journalists to submit original reporting to JTF News, fully integrated into the existing automated verification pipeline, with every design decision documented in `docs/plans/2026-03-02-journalist-submissions-design.md`.

**Architecture:** Extend the existing single-script architecture (main.py) with journalist data management functions, extend the existing `are_sources_unrelated()` / `get_learned_rating()` / `record_verification_success()` functions to handle journalist source IDs (prefixed `journalist:`), and add three new static HTML pages (register, submit, leaderboard) to the GitHub Pages site in `docs/`. Submissions arrive as JSON files in `data/submissions/` (written by client-side GitHub API calls from the submit form) and are consumed by `process_cycle()` on each 30-minute cycle.

**Tech Stack:** Python 3 (main.py), static HTML/CSS/JS (docs/), GitHub OAuth (authentication), GitHub Contents API (submission transport), existing JTF design system (style.css, Inter font, dark glassmorphism).

**Design Reference:** `docs/plans/2026-03-02-journalist-submissions-design.md` — ALL sections (1-19) of this design document MUST be fully implemented. Nothing deferred.

**IMPORTANT — Read before starting:**
- Read the whitepaper: `documentation/WhitePaper Ver 1.3 CURRENT.md`
- Read the design document: `docs/plans/2026-03-02-journalist-submissions-design.md`
- Read the CLAUDE.md project instructions
- Understand: A journalist is a source. Sources follow the methodology. The methodology does not bend.
- Use `./bu.sh "message"` for ALL commits. NEVER use raw `git commit`.
- ALWAYS `git pull --rebase origin main` BEFORE running `./bu.sh`.

---

## Task Dependency Graph

```
Task 1 (data layer) ──────────────┐
Task 2 (get_source_info)  ────────┤
Task 3 (are_sources_unrelated) ───┤──→ Task 7 (process_cycle integration)
Task 4 (scoring functions) ───────┤
Task 5 (quota system) ────────────┤
Task 6 (submission I/O) ──────────┘

Task 8 (GitHub OAuth app setup) ──→ Task 9 (register.html) ──→ Task 10 (submit.html)

Task 7 + Task 10 ──→ Task 11 (leaderboard page)
                  ──→ Task 12 (nav + how-it-works updates)
                  ──→ Task 13 (quarterly audit extension)
                  ──→ Task 14 (data retention cleanup)
                  ──→ Task 15 (leaderboard generation in push_to_github)

All above ──→ Task 16 (end-to-end verification)
           ──→ Task 17 (commit final)
```

**Parallelization opportunities:**
- Tasks 1-6 can be done in parallel (all are independent main.py functions)
- Task 8 (OAuth setup) can happen in parallel with Tasks 1-6
- Tasks 9, 10 depend on Task 8 but are sequential to each other
- Tasks 11-15 can be parallelized after Tasks 7 and 10 are complete

---

## Task 1: Journalist Data Layer

**Design sections covered:** 7.4 (Data Structure), 14 (Data Storage)

**Files:**
- Modify: `main.py` (add after line ~1220, before `are_sources_unrelated()`)
- Create: `data/journalists.json` (initial empty structure)
- Create: `data/submissions/` directory
- Create: `data/submissions/processed/` directory

**Step 1: Create the data directories and initial journalists.json**

```bash
mkdir -p data/submissions/processed
```

Write `data/journalists.json`:
```json
{
  "journalists": {},
  "last_updated": null
}
```

**Step 2: Add journalist data functions to main.py**

Add these functions to main.py after the existing source-related functions (around line 1220, before `are_sources_unrelated()`):

```python
# =============================================================================
# JOURNALIST DATA MANAGEMENT
# =============================================================================

def load_journalists() -> dict:
    """Load journalist profiles from data/journalists.json."""
    journalists_file = DATA_DIR / "journalists.json"
    if journalists_file.exists():
        with open(journalists_file) as f:
            data = json.load(f)
        return data.get("journalists", {})
    return {}


def save_journalists(journalists: dict):
    """Save journalist profiles to data/journalists.json."""
    journalists_file = DATA_DIR / "journalists.json"
    data = {
        "journalists": journalists,
        "last_updated": datetime.now(timezone.utc).isoformat()
    }
    with open(journalists_file, 'w') as f:
        json.dump(data, f, indent=2)


def get_journalist_info(journalist_id: str) -> dict:
    """Load a single journalist's profile.

    Args:
        journalist_id: GitHub username of the journalist

    Returns:
        Journalist profile dict, or None if not found
    """
    journalists = load_journalists()
    return journalists.get(journalist_id)


def get_journalist_display_name(journalist_id: str) -> str:
    """Format journalist name for display.

    Returns: "Jane Doe, Independent – Portland, OR" or "Unknown Journalist"
    """
    info = get_journalist_info(journalist_id)
    if not info:
        return "Unknown Journalist"

    name = info.get("name", journalist_id)
    affiliation = info.get("affiliation", "Independent")
    location = info.get("location", "")

    if location:
        return f"{name}, {affiliation} – {location}"
    return f"{name}, {affiliation}"


def register_journalist(github_username: str, name: str, location: str,
                        affiliation: str, financial_disclosures: list) -> dict:
    """Register a new journalist.

    Args:
        github_username: GitHub username (serves as journalist_id)
        name: Full legal name
        location: City, state/province, country
        affiliation: Employer or "Independent"
        financial_disclosures: List of dicts with entity, relationship, percentage

    Returns:
        The created journalist profile dict
    """
    journalists = load_journalists()

    if github_username in journalists:
        log.warning(f"Journalist {github_username} already registered")
        return journalists[github_username]

    # Determine majority funder (owner) from disclosures
    owner = "Self-funded"
    owner_display = "Self-funded (100%)"
    for disclosure in financial_disclosures:
        if disclosure.get("percentage", 0) > 50:
            owner = disclosure["entity"]
            owner_display = f"{disclosure['entity']} ({disclosure['percentage']}%)"
            break

    now = datetime.now(timezone.utc).isoformat()
    current_quarter = f"Q{(datetime.now(timezone.utc).month - 1) // 3 + 1} {datetime.now(timezone.utc).year}"

    profile = {
        "github_username": github_username,
        "name": name,
        "location": location,
        "affiliation": affiliation,
        "owner": owner,
        "owner_display": owner_display,
        "financial_disclosures": financial_disclosures,
        "registered": now,
        "last_disclosure_update": now,
        "disclosure_quarter": current_quarter,
        "status": "active",
        "ratings": {
            "accuracy": 5.0,
            "bias": 5.0,
            "speed": 5.0,
            "consensus": 5.0
        },
        "stats": {
            "submitted": 0,
            "verified": 0,
            "expired": 0,
            "successes": 0,
            "failures": 0
        },
        "submission_quota": 3,
        "control_type": "journalist",
        "institutional_holders": []
    }

    journalists[github_username] = profile
    save_journalists(journalists)
    log.info(f"Registered journalist: {name} ({github_username})")
    return profile
```

**Step 3: Verify the data layer works**

Run Python interactively to confirm:
```bash
cd /Users/larryseyer/JTFNews && source venv/bin/activate && python3 -c "
from main import load_journalists, save_journalists, register_journalist, get_journalist_info, get_journalist_display_name
# Test empty load
j = load_journalists()
assert j == {}, f'Expected empty dict, got {j}'
# Test register
profile = register_journalist('testuser', 'Test User', 'Austin, TX, USA', 'Independent', [{'entity': 'Self-funded', 'relationship': 'primary income', 'percentage': 100}])
assert profile['name'] == 'Test User'
assert profile['owner'] == 'Self-funded'
assert profile['submission_quota'] == 3
# Test retrieval
info = get_journalist_info('testuser')
assert info is not None
assert info['name'] == 'Test User'
# Test display name
display = get_journalist_display_name('testuser')
assert display == 'Test User, Independent – Austin, TX, USA', f'Got: {display}'
# Clean up test data
import json
from pathlib import Path
with open(Path('data/journalists.json'), 'w') as f:
    json.dump({'journalists': {}, 'last_updated': None}, f)
print('All journalist data layer tests passed.')
"
```

**Step 4: Commit**

```bash
git pull --rebase origin main && ./bu.sh "feat: add journalist data layer (load, save, register, get info)"
```

---

## Task 2: Unified Source Info Lookup

**Design sections covered:** 9.1 (Extended are_sources_unrelated)

**Files:**
- Modify: `main.py` — add `get_source_info()` function near the journalist data functions

**Step 1: Add get_source_info() to main.py**

Add this function after the journalist data functions (after `register_journalist()`):

```python
def get_source_info(source_id: str) -> dict:
    """Unified source lookup — works for both institutional sources and journalists.

    Args:
        source_id: Either a config source ID ("bbc", "npr") or "journalist:username"

    Returns:
        Dict with at minimum: owner, institutional_holders, control_type, name
        Returns None if source not found.
    """
    if source_id.startswith("journalist:"):
        journalist_id = source_id.split(":", 1)[1]
        info = get_journalist_info(journalist_id)
        if info:
            return {
                "id": source_id,
                "name": get_journalist_display_name(journalist_id),
                "owner": info["owner"],
                "owner_display": info.get("owner_display", info["owner"]),
                "control_type": "journalist",
                "institutional_holders": info.get("institutional_holders", []),
                "ratings": info.get("ratings", {}),
                "status": info.get("status", "active")
            }
        return None

    # Institutional source from config.json
    for source in CONFIG["sources"]:
        if source["id"] == source_id:
            return source

    return None
```

**Step 2: Verify**

```bash
cd /Users/larryseyer/JTFNews && source venv/bin/activate && python3 -c "
from main import get_source_info, register_journalist, load_journalists, save_journalists
import json
from pathlib import Path

# Test institutional source lookup
bbc = get_source_info('bbc')
assert bbc is not None, 'BBC not found'
assert 'owner' in bbc
print(f'BBC owner: {bbc[\"owner\"]}')

# Test journalist source lookup (register first)
register_journalist('testuser2', 'Test User 2', 'Portland, OR', 'Independent', [{'entity': 'Self-funded', 'relationship': 'primary', 'percentage': 100}])
j = get_source_info('journalist:testuser2')
assert j is not None, 'Journalist not found'
assert j['owner'] == 'Self-funded'
assert j['control_type'] == 'journalist'
print(f'Journalist owner: {j[\"owner\"]}')

# Test non-existent
assert get_source_info('nonexistent') is None
assert get_source_info('journalist:nobody') is None

# Clean up
with open(Path('data/journalists.json'), 'w') as f:
    json.dump({'journalists': {}, 'last_updated': None}, f)
print('All get_source_info tests passed.')
"
```

**Step 3: Commit**

```bash
git pull --rebase origin main && ./bu.sh "feat: add unified get_source_info() for institutional and journalist sources"
```

---

## Task 3: Extend are_sources_unrelated() for Journalists

**Design sections covered:** 3 (Financial Independence Rule), 9 (Source Independence Check)

**Files:**
- Modify: `main.py` line 1224-1246 — replace `are_sources_unrelated()` function

**Step 1: Replace are_sources_unrelated()**

Replace the existing function at line 1224 with:

```python
def are_sources_unrelated(source1_id: str, source2_id: str) -> bool:
    """Check if two sources are unrelated (different owners).

    Works for institutional sources (from config.json), journalists
    (from journalists.json), and cross-type pairs (journalist + institutional).

    Rule: "No common majority shareholder is the minimum threshold."
    This applies identically regardless of source type.
    """
    s1 = get_source_info(source1_id)
    s2 = get_source_info(source2_id)

    if not s1 or not s2:
        return False

    # Same owner = related
    if s1["owner"] == s2["owner"]:
        return False

    # Check institutional holder overlap (same rule for all source types)
    holders1 = {h["name"] for h in s1.get("institutional_holders", [])}
    holders2 = {h["name"] for h in s2.get("institutional_holders", [])}

    shared = holders1 & holders2
    if len(shared) >= CONFIG["unrelated_rules"]["max_shared_top_holders"]:
        return False

    return True
```

**Step 2: Verify the extended function**

```bash
cd /Users/larryseyer/JTFNews && source venv/bin/activate && python3 -c "
from main import are_sources_unrelated, register_journalist, load_journalists, save_journalists
import json
from pathlib import Path

# Register test journalists
register_journalist('jdoe', 'Jane Doe', 'Portland, OR', 'Independent', [{'entity': 'Self-funded', 'relationship': 'primary', 'percentage': 100}])
register_journalist('jsmith', 'John Smith', 'Austin, TX', 'Independent', [{'entity': 'Self-funded', 'relationship': 'primary', 'percentage': 100}])
register_journalist('jfunded', 'Funded Person', 'NYC, NY', 'Foundation Employee', [{'entity': 'Foundation X', 'relationship': 'employer', 'percentage': 80}])

# Test 1: Institutional vs institutional (existing behavior)
assert are_sources_unrelated('bbc', 'npr') == True, 'BBC and NPR should be unrelated'
print('PASS: BBC vs NPR = unrelated')

# Test 2: Journalist vs institutional (different owners)
assert are_sources_unrelated('journalist:jdoe', 'bbc') == True, 'Journalist vs BBC should be unrelated'
print('PASS: journalist:jdoe vs bbc = unrelated')

# Test 3: Two journalists (both self-funded = same owner!)
assert are_sources_unrelated('journalist:jdoe', 'journalist:jsmith') == False, 'Both self-funded = same owner'
print('PASS: Two self-funded journalists = related (same owner)')

# Test 4: Non-existent source
assert are_sources_unrelated('journalist:nobody', 'bbc') == False, 'Unknown source = False'
print('PASS: Unknown source = False')

# Clean up
with open(Path('data/journalists.json'), 'w') as f:
    json.dump({'journalists': {}, 'last_updated': None}, f)
print('All are_sources_unrelated tests passed.')
"
```

**Step 3: Commit**

```bash
git pull --rebase origin main && ./bu.sh "feat: extend are_sources_unrelated() for journalist source IDs"
```

---

## Task 4: Extend Scoring Functions for Journalists

**Design sections covered:** 6 (Scoring System), 6.1 (Four Identical Metrics), 6.2 (Cold Start)

**Files:**
- Modify: `main.py` lines 1425-1506 — extend `record_verification_success()`, `record_verification_failure()`, `get_learned_rating()`

**Step 1: Extend record_verification_success() (line ~1425)**

Find the existing `record_verification_success()` function and add journalist handling. At the end of the function, after writing to `learned_ratings.json`, add:

```python
    # If this is a journalist source, also update journalist stats
    if source_id.startswith("journalist:"):
        journalist_id = source_id.split(":", 1)[1]
        journalists = load_journalists()
        if journalist_id in journalists:
            journalists[journalist_id]["stats"]["successes"] += 1
            journalists[journalist_id]["stats"]["verified"] += 1
            # Recalculate accuracy rating
            stats = journalists[journalist_id]["stats"]
            total = stats["successes"] + stats["failures"]
            if total > 0:
                journalists[journalist_id]["ratings"]["accuracy"] = round(
                    (stats["successes"] / total) * 10, 1
                )
            save_journalists(journalists)
```

**Step 2: Extend record_verification_failure() (line ~1442)**

Same pattern — at the end of the existing function:

```python
    # If this is a journalist source, also update journalist stats
    if source_id.startswith("journalist:"):
        journalist_id = source_id.split(":", 1)[1]
        journalists = load_journalists()
        if journalist_id in journalists:
            journalists[journalist_id]["stats"]["failures"] += 1
            journalists[journalist_id]["stats"]["expired"] += 1
            # Recalculate accuracy rating
            stats = journalists[journalist_id]["stats"]
            total = stats["successes"] + stats["failures"]
            if total > 0:
                journalists[journalist_id]["ratings"]["accuracy"] = round(
                    (stats["successes"] / total) * 10, 1
                )
            save_journalists(journalists)
```

**Step 3: Extend get_learned_rating() (line ~1459)**

At the beginning of the function, before the config lookup, add:

```python
    # Handle journalist sources
    if source_id.startswith("journalist:"):
        journalist_id = source_id.split(":", 1)[1]
        info = get_journalist_info(journalist_id)
        if info:
            stats = info.get("stats", {})
            total = stats.get("successes", 0) + stats.get("failures", 0)
            if total >= 5:
                return round((stats["successes"] / total) * 10, 1)
            elif total > 0:
                # Blend with default (5.0) during cold start
                observed = (stats["successes"] / total) * 10
                weight = total / 5
                return round(5.0 * (1 - weight) + observed * weight, 1)
        return 5.0  # Default for new journalists
```

**Step 4: Add journalist bias tracking function**

Add this new function after the scoring functions:

```python
def update_journalist_bias_score(journalist_id: str, original_length: int, fact_length: int):
    """Update a journalist's bias score based on how much text the AI stripped.

    Bias score = 10 - (avg_percentage_of_text_removed × 10)
    Higher = more neutral writing (less stripping needed).
    """
    journalists = load_journalists()
    if journalist_id not in journalists:
        return

    profile = journalists[journalist_id]

    # Track running average of text removed percentage
    if original_length > 0:
        pct_removed = (original_length - fact_length) / original_length
    else:
        pct_removed = 0

    # Use simple running average via stats
    stats = profile.get("stats", {})
    prev_count = stats.get("bias_samples", 0)
    prev_avg = stats.get("bias_avg_removed", 0)

    new_count = prev_count + 1
    new_avg = ((prev_avg * prev_count) + pct_removed) / new_count

    stats["bias_samples"] = new_count
    stats["bias_avg_removed"] = round(new_avg, 4)
    profile["stats"] = stats

    # Update bias rating
    profile["ratings"]["bias"] = round(10 - (new_avg * 10), 1)

    journalists[journalist_id] = profile
    save_journalists(journalists)
```

**Step 5: Add submission quota calculation**

```python
def get_journalist_quota(journalist_id: str) -> int:
    """Get daily submission quota based on accuracy score.

    | Accuracy Score | Daily Quota |
    |---------------|-------------|
    | No data (new) | 3           |
    | < 5.0         | 2           |
    | 5.0 - 7.0     | 5           |
    | 7.0 - 9.0     | 10          |
    | > 9.0         | 20          |
    """
    info = get_journalist_info(journalist_id)
    if not info:
        return 0

    stats = info.get("stats", {})
    total = stats.get("successes", 0) + stats.get("failures", 0)

    if total == 0:
        return 3  # New journalist

    accuracy = info.get("ratings", {}).get("accuracy", 5.0)

    if accuracy < 5.0:
        return 2
    elif accuracy < 7.0:
        return 5
    elif accuracy < 9.0:
        return 10
    else:
        return 20


def check_journalist_quota(journalist_id: str) -> bool:
    """Check if journalist has remaining submissions for today.

    Returns True if they can submit, False if quota exceeded.
    """
    quota = get_journalist_quota(journalist_id)

    # Count today's submissions
    submissions_dir = DATA_DIR / "submissions"
    processed_dir = submissions_dir / "processed"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    count = 0

    # Count pending submissions from today
    if submissions_dir.exists():
        for f in submissions_dir.glob("*.json"):
            try:
                with open(f) as fh:
                    sub = json.load(fh)
                if sub.get("journalist_id") == journalist_id and sub.get("submitted", "").startswith(today):
                    count += 1
            except (json.JSONDecodeError, KeyError):
                continue

    # Count processed submissions from today
    if processed_dir.exists():
        for f in processed_dir.glob("*.json"):
            try:
                with open(f) as fh:
                    sub = json.load(fh)
                if sub.get("journalist_id") == journalist_id and sub.get("submitted", "").startswith(today):
                    count += 1
            except (json.JSONDecodeError, KeyError):
                continue

    return count < quota
```

**Step 6: Verify scoring functions**

```bash
cd /Users/larryseyer/JTFNews && source venv/bin/activate && python3 -c "
from main import register_journalist, get_learned_rating, get_journalist_quota, check_journalist_quota, update_journalist_bias_score, load_journalists, save_journalists
import json
from pathlib import Path

# Register test journalist
register_journalist('scoretest', 'Score Test', 'NYC, NY', 'Independent', [{'entity': 'Self-funded', 'relationship': 'primary', 'percentage': 100}])

# Test default rating
r = get_learned_rating('journalist:scoretest')
assert r == 5.0, f'Expected 5.0, got {r}'
print(f'Default rating: {r}')

# Test default quota
q = get_journalist_quota('scoretest')
assert q == 3, f'Expected 3, got {q}'
print(f'Default quota: {q}')

# Test can submit
assert check_journalist_quota('scoretest') == True
print('Quota check: can submit')

# Test bias update
update_journalist_bias_score('scoretest', 100, 80)  # 20% removed
j = load_journalists()
assert j['scoretest']['ratings']['bias'] == 8.0, f'Expected 8.0 bias'
print(f'Bias after 20% strip: {j[\"scoretest\"][\"ratings\"][\"bias\"]}')

# Clean up
with open(Path('data/journalists.json'), 'w') as f:
    json.dump({'journalists': {}, 'last_updated': None}, f)
print('All scoring tests passed.')
"
```

**Step 7: Commit**

```bash
git pull --rebase origin main && ./bu.sh "feat: add journalist scoring, bias tracking, and quota system"
```

---

## Task 5: Submission I/O Functions

**Design sections covered:** 8 (Submission Form and Workflow), 14.1 (Data Retention)

**Files:**
- Modify: `main.py` — add submission loading/processing functions

**Step 1: Add submission I/O functions to main.py**

```python
def load_pending_submissions() -> list:
    """Load unprocessed journalist submissions from data/submissions/.

    Returns list of submission dicts sorted by submission time (oldest first).
    """
    submissions_dir = DATA_DIR / "submissions"
    if not submissions_dir.exists():
        submissions_dir.mkdir(parents=True, exist_ok=True)
        return []

    submissions = []
    for f in sorted(submissions_dir.glob("*.json")):
        if f.name == "processed":
            continue
        try:
            with open(f) as fh:
                sub = json.load(fh)
            sub["_file"] = str(f)  # Track file path for later move
            submissions.append(sub)
        except (json.JSONDecodeError, KeyError) as e:
            log.warning(f"Invalid submission file {f.name}: {e}")
            continue

    return submissions


def mark_submission_processed(submission: dict, processed_fact: str = None,
                               confidence: int = None):
    """Move a processed submission to the processed/ directory.

    Updates the submission with processing results before moving.
    """
    file_path = Path(submission.get("_file", ""))
    if not file_path.exists():
        log.warning(f"Submission file not found: {file_path}")
        return

    processed_dir = DATA_DIR / "submissions" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)

    # Update submission with processing results
    submission["status"] = "processed"
    submission["processed_fact"] = processed_fact
    submission["confidence"] = confidence
    submission["processed_at"] = datetime.now(timezone.utc).isoformat()

    # Remove internal tracking field
    submission.pop("_file", None)

    # Write to processed directory
    dest = processed_dir / file_path.name
    with open(dest, 'w') as f:
        json.dump(submission, f, indent=2)

    # Remove from pending
    file_path.unlink()


def clean_old_submissions(max_age_days: int = 7):
    """Delete processed submissions older than max_age_days.

    Per whitepaper: 'We do not store raw data longer than seven days.'
    """
    processed_dir = DATA_DIR / "submissions" / "processed"
    if not processed_dir.exists():
        return

    cutoff = datetime.now(timezone.utc).timestamp() - (max_age_days * 86400)
    cleaned = 0

    for f in processed_dir.glob("*.json"):
        try:
            with open(f) as fh:
                sub = json.load(fh)
            processed_at = sub.get("processed_at", sub.get("submitted", ""))
            if processed_at:
                ts = datetime.fromisoformat(processed_at.replace("Z", "+00:00")).timestamp()
                if ts < cutoff:
                    f.unlink()
                    cleaned += 1
        except Exception:
            continue

    if cleaned > 0:
        log.info(f"Cleaned {cleaned} old submissions (>{max_age_days} days)")
```

**Step 2: Verify**

```bash
cd /Users/larryseyer/JTFNews && source venv/bin/activate && python3 -c "
from main import load_pending_submissions, mark_submission_processed, clean_old_submissions
from pathlib import Path
import json

# Create a test submission
sub_dir = Path('data/submissions')
sub_dir.mkdir(parents=True, exist_ok=True)
test_sub = {
    'id': 'sub-test-001',
    'journalist_id': 'testuser',
    'submitted': '2026-03-02T15:00:00Z',
    'status': 'pending',
    'event_description': 'Test event description.',
    'location': 'Portland, OR',
    'event_date': '2026-03-02'
}
with open(sub_dir / 'sub-test-001.json', 'w') as f:
    json.dump(test_sub, f)

# Load it
subs = load_pending_submissions()
assert len(subs) == 1, f'Expected 1 submission, got {len(subs)}'
assert subs[0]['id'] == 'sub-test-001'
print(f'Loaded {len(subs)} submission(s)')

# Process it
mark_submission_processed(subs[0], processed_fact='Test event occurred in Portland.', confidence=90)
assert not (sub_dir / 'sub-test-001.json').exists(), 'Pending file should be removed'
assert (sub_dir / 'processed' / 'sub-test-001.json').exists(), 'Processed file should exist'
print('Submission marked as processed')

# Verify processed content
with open(sub_dir / 'processed' / 'sub-test-001.json') as f:
    processed = json.load(f)
assert processed['processed_fact'] == 'Test event occurred in Portland.'
assert processed['status'] == 'processed'
print('Processed content verified')

# Clean up
(sub_dir / 'processed' / 'sub-test-001.json').unlink()
print('All submission I/O tests passed.')
"
```

**Step 3: Commit**

```bash
git pull --rebase origin main && ./bu.sh "feat: add submission I/O (load, process, clean old submissions)"
```

---

## Task 6: Quarterly Disclosure Freshness Check

**Design sections covered:** 11 (Quarterly Financial Disclosure Audit)

**Files:**
- Modify: `main.py` — add disclosure freshness check function

**Step 1: Add disclosure freshness function**

```python
def check_disclosure_freshness():
    """Suspend journalists with stale quarterly disclosures.

    Same quarterly cadence as institutional ownership audits:
    Q1=Jan, Q2=Apr, Q3=Jul, Q4=Oct.

    Journalists whose last disclosure update is from a previous quarter
    are suspended until they update.
    """
    now = datetime.now(timezone.utc)
    current_quarter = f"Q{(now.month - 1) // 3 + 1} {now.year}"

    journalists = load_journalists()
    suspended_count = 0

    for jid, profile in journalists.items():
        if profile.get("status") == "active":
            disclosure_quarter = profile.get("disclosure_quarter", "")
            if disclosure_quarter != current_quarter:
                profile["status"] = "suspended_disclosure"
                suspended_count += 1
                log.warning(
                    f"Journalist {profile.get('name', jid)} suspended: "
                    f"disclosure from {disclosure_quarter}, current is {current_quarter}"
                )

    if suspended_count > 0:
        save_journalists(journalists)
        log.info(f"Suspended {suspended_count} journalist(s) for stale disclosures")

    return suspended_count


def update_journalist_disclosure(journalist_id: str, financial_disclosures: list):
    """Update a journalist's financial disclosures and reactivate if suspended.

    Called when a journalist submits updated disclosures.
    """
    journalists = load_journalists()
    if journalist_id not in journalists:
        log.warning(f"Cannot update disclosure: journalist {journalist_id} not found")
        return

    profile = journalists[journalist_id]
    now = datetime.now(timezone.utc)
    current_quarter = f"Q{(now.month - 1) // 3 + 1} {now.year}"

    profile["financial_disclosures"] = financial_disclosures
    profile["last_disclosure_update"] = now.isoformat()
    profile["disclosure_quarter"] = current_quarter

    # Recalculate owner from new disclosures
    owner = "Self-funded"
    owner_display = "Self-funded (100%)"
    for disclosure in financial_disclosures:
        if disclosure.get("percentage", 0) > 50:
            owner = disclosure["entity"]
            owner_display = f"{disclosure['entity']} ({disclosure['percentage']}%)"
            break

    profile["owner"] = owner
    profile["owner_display"] = owner_display

    # Reactivate if suspended for disclosure
    if profile.get("status") == "suspended_disclosure":
        profile["status"] = "active"
        log.info(f"Journalist {profile.get('name', journalist_id)} reactivated after disclosure update")

    journalists[journalist_id] = profile
    save_journalists(journalists)
```

**Step 2: Verify**

```bash
cd /Users/larryseyer/JTFNews && source venv/bin/activate && python3 -c "
from main import register_journalist, check_disclosure_freshness, update_journalist_disclosure, load_journalists
import json
from pathlib import Path

# Register journalist with old quarter
register_journalist('staletest', 'Stale Test', 'NYC', 'Independent', [{'entity': 'Self-funded', 'relationship': 'primary', 'percentage': 100}])

# Manually set to old quarter
j = load_journalists()
j['staletest']['disclosure_quarter'] = 'Q4 2025'
from main import save_journalists
save_journalists(j)

# Check freshness — should suspend
count = check_disclosure_freshness()
assert count == 1, f'Expected 1 suspended, got {count}'
j = load_journalists()
assert j['staletest']['status'] == 'suspended_disclosure'
print('Stale journalist suspended')

# Update disclosure — should reactivate
update_journalist_disclosure('staletest', [{'entity': 'Self-funded', 'relationship': 'primary', 'percentage': 100}])
j = load_journalists()
assert j['staletest']['status'] == 'active'
print('Journalist reactivated after disclosure update')

# Clean up
with open(Path('data/journalists.json'), 'w') as f:
    json.dump({'journalists': {}, 'last_updated': None}, f)
print('All disclosure freshness tests passed.')
"
```

**Step 3: Commit**

```bash
git pull --rebase origin main && ./bu.sh "feat: add quarterly disclosure freshness check and update"
```

---

## Task 7: Integrate Journalist Submissions into process_cycle()

**Design sections covered:** 8.4 (Integration with process_cycle), 2 (Verification Standard), 5 (AI Processing)

**Files:**
- Modify: `main.py` line ~5790 (inside `process_cycle()`, after `headlines = scrape_all_sources()`)

**Step 1: Add journalist submission processing to process_cycle()**

After line `headlines = scrape_all_sources()` (line ~5790) and before the `for headline in headlines:` loop, insert:

```python
    # =========================================================================
    # JOURNALIST SUBMISSIONS — Process pending submissions from data/submissions/
    # A journalist is a source. Sources follow the methodology.
    # =========================================================================
    submissions = load_pending_submissions()
    if submissions:
        log.info(f"Processing {len(submissions)} journalist submission(s)")

    for sub in submissions:
        journalist_id = sub.get("journalist_id", "")
        journalist_info = get_journalist_info(journalist_id)

        # Skip if journalist not found or suspended
        if not journalist_info:
            log.warning(f"Submission from unknown journalist: {journalist_id}")
            mark_submission_processed(sub, processed_fact="SKIP", confidence=0)
            continue

        if journalist_info.get("status") != "active":
            log.info(f"Skipping submission from suspended journalist: {journalist_id}")
            mark_submission_processed(sub, processed_fact="SKIP", confidence=0)
            continue

        # Check quota
        if not check_journalist_quota(journalist_id):
            log.info(f"Journalist {journalist_id} exceeded daily quota, skipping")
            mark_submission_processed(sub, processed_fact="SKIP_QUOTA", confidence=0)
            continue

        # Process through same Claude pipeline as scraped headlines
        event_text = sub.get("event_description", "")
        if not event_text.strip():
            mark_submission_processed(sub, processed_fact="SKIP", confidence=0)
            continue

        result = extract_fact(event_text)
        processed_count += 1

        if result["fact"] == "SKIP":
            mark_submission_processed(sub, processed_fact="SKIP", confidence=0)
            # Increment submitted count
            journalists = load_journalists()
            if journalist_id in journalists:
                journalists[journalist_id]["stats"]["submitted"] += 1
                save_journalists(journalists)
            continue

        fact = result["fact"]
        confidence = result["confidence"]

        # Track bias score (how much was stripped)
        original_length = len(event_text)
        fact_length = len(fact)
        update_journalist_bias_score(journalist_id, original_length, fact_length)

        # Check confidence threshold (same as institutional)
        if confidence < CONFIG["thresholds"]["min_confidence"]:
            log.info(f"Low confidence journalist submission ({confidence}%): {fact[:40]}...")
            mark_submission_processed(sub, processed_fact=fact, confidence=confidence)
            continue

        # Check newsworthiness (same thresholds as institutional)
        newsworthy = result.get("newsworthy", True)
        if not newsworthy:
            log.info(f"Journalist submission not newsworthy: {fact[:40]}...")
            mark_submission_processed(sub, processed_fact=fact, confidence=confidence)
            continue

        # Check for duplicates
        if is_duplicate(fact):
            log.info(f"Duplicate journalist submission: {fact[:40]}...")
            mark_submission_processed(sub, processed_fact=fact, confidence=confidence)
            continue

        # Capitalize first letter
        if fact and fact[0].islower():
            fact = fact[0].upper() + fact[1:]

        # Increment submitted count
        journalists_data = load_journalists()
        if journalist_id in journalists_data:
            journalists_data[journalist_id]["stats"]["submitted"] += 1
            save_journalists(journalists_data)

        # Look for matching stories in queue (same logic as scraped headlines)
        matches = find_matching_stories(fact, queue)

        if matches:
            for match in matches:
                if are_sources_unrelated(f"journalist:{journalist_id}", match["source_id"]):
                    # VERIFIED! Journalist + independent source
                    new_reliability = get_reliability_score(f"journalist:{journalist_id}", confidence)
                    queue_confidence = match.get("confidence", 85)
                    queue_reliability = get_reliability_score(match["source_id"], queue_confidence)

                    if queue_reliability > new_reliability:
                        best_fact = match["fact"]
                        log.info(
                            f"Preferring queued source ({match['source_name']}: {queue_reliability:.1f}) "
                            f"over journalist ({journalist_id}: {new_reliability:.1f})"
                        )
                    else:
                        best_fact = fact

                    journalist_headline = {
                        "source_id": f"journalist:{journalist_id}",
                        "source_name": get_journalist_display_name(journalist_id),
                        "source_rating": get_learned_rating(f"journalist:{journalist_id}"),
                        "source_url": "",
                        "timestamp": sub.get("submitted", datetime.now(timezone.utc).isoformat())
                    }
                    sources = [journalist_headline, match]

                    # Check for contradictions
                    recent_facts = get_recent_facts()
                    if check_contradiction(best_fact, recent_facts):
                        log.warning(f"Contradiction blocked (journalist): {best_fact[:40]}...")
                        send_alert(f"Contradiction: {best_fact[:50]}")
                        continue

                    if best_fact and best_fact[0].islower():
                        best_fact = best_fact[0].upper() + best_fact[1:]

                    story_audio_id = get_story_audio_id(best_fact)
                    audio_file = generate_tts(best_fact, story_id=story_audio_id)
                    write_current_story(best_fact, sources)
                    append_daily_log(best_fact, sources, audio_file)
                    add_shown_hash(get_story_hash(best_fact))

                    queue = [q for q in queue if q["fact"] != match["fact"]]
                    published_count += 1
                    log.info(f"VERIFIED (journalist): {best_fact[:50]}...")

                    fact_hash = get_story_hash(best_fact)
                    record_verification_success(f"journalist:{journalist_id}", fact_hash)
                    record_verification_success(match["source_id"], fact_hash)

                    # Check for corrections (same as institutional)
                    recent_stories = get_recent_stories_for_correction(days=7)
                    correction_info = detect_correction_needed(best_fact, sources, recent_stories)
                    if correction_info:
                        correction_type = correction_info.get("correction_type", "correction")
                        story_id = correction_info.get("story_id", "").strip("[]")
                        original = correction_info.get("original_fact", "")
                        reason = correction_info.get("reason", "")
                        if correction_type == "retraction":
                            issue_retraction(story_id, original, reason, sources)
                        else:
                            issue_correction(story_id, original, best_fact, reason, sources, correction_type)

                    break
        else:
            # No match — add to queue
            queue.append({
                "fact": fact,
                "source_id": f"journalist:{journalist_id}",
                "source_name": get_journalist_display_name(journalist_id),
                "source_rating": get_learned_rating(f"journalist:{journalist_id}"),
                "source_url": "",
                "timestamp": sub.get("submitted", datetime.now(timezone.utc).isoformat()),
                "confidence": confidence,
                "type": "journalist_submission"
            })
            queued_count += 1
            log.info(f"Queued (journalist): {fact[:40]}...")

        mark_submission_processed(sub, processed_fact=fact, confidence=confidence)

    # Clean old processed submissions (7-day retention)
    clean_old_submissions(max_age_days=7)
```

**Step 2: Also extend clean_expired_queue() (line ~1666)**

In the existing `clean_expired_queue()` function, ensure verification failures are recorded for journalist sources too. Find the line where `record_verification_failure()` is called and verify it already handles the `journalist:` prefix (it will if Task 4 was done correctly — the function checks `source_id.startswith("journalist:")`).

**Step 3: Verify process_cycle integration compiles**

```bash
cd /Users/larryseyer/JTFNews && source venv/bin/activate && python3 -c "
import main
# Just verify the module loads without syntax errors
print('main.py loaded successfully')
print(f'process_cycle function exists: {hasattr(main, \"process_cycle\")}')
print(f'load_pending_submissions exists: {hasattr(main, \"load_pending_submissions\")}')
print(f'check_journalist_quota exists: {hasattr(main, \"check_journalist_quota\")}')
"
```

**Step 4: Commit**

```bash
git pull --rebase origin main && ./bu.sh "feat: integrate journalist submissions into process_cycle()"
```

---

## Task 8: GitHub OAuth Application Setup

**Design sections covered:** 7.2 (Registration Flow), 7.3 (GitHub OAuth Rationale)

**Files:**
- Documentation only — record OAuth app details

**Step 1: Create GitHub OAuth App**

The overseer must guide/confirm that a GitHub OAuth App exists for JTF News. This requires:

1. Go to GitHub → Settings → Developer settings → OAuth Apps → New OAuth App
2. Application name: `JTF News Contributor`
3. Homepage URL: `https://jtfnews.org`
4. Authorization callback URL: `https://jtfnews.org/submit.html`
5. Record the **Client ID** (this is public, goes in the HTML)
6. Generate a **Client Secret** (but note: for a static site using the implicit flow, we use the Client ID only with a PKCE flow or use a lightweight proxy)

**IMPORTANT NOTE ON STATIC SITE AUTH:**

GitHub Pages is a static site. GitHub OAuth requires a server-side callback to exchange the authorization code for a token. There are three professional approaches:

**Option A (Recommended): GitHub OAuth with Gatekeeper proxy**
- Deploy a tiny proxy service (e.g., on Cloudflare Workers, free tier) that handles the OAuth code-to-token exchange
- The static site redirects to GitHub for auth, GitHub redirects back with a code, the site sends the code to the proxy, the proxy exchanges it for a token
- The proxy is ~20 lines of code

**Option B: GitHub Device Flow**
- Use GitHub's Device Authorization Grant (no server needed)
- User gets a code, enters it on github.com
- Less seamless UX but zero server-side infrastructure

**Option C: Use GitHub Issues directly**
- Skip OAuth entirely
- Journalists fork a submissions repo, create a PR with their submission JSON
- Most GitHub-native approach but worst UX for non-developers

**The overseer should implement Option A** as the most professional approach. Create a minimal Cloudflare Worker (or equivalent free serverless function) that:
1. Receives the OAuth code from the callback
2. Exchanges it for an access token via GitHub API
3. Returns the token to the client

**Step 2: Create the OAuth proxy**

Create file `docs/oauth-worker.js` (this is the Cloudflare Worker source, deployed separately):

```javascript
// JTF News GitHub OAuth Proxy
// Deployed as a Cloudflare Worker (free tier)
// Exchanges GitHub OAuth code for access token
// This is needed because GitHub Pages is static and cannot do server-side token exchange

addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request));
});

async function handleRequest(request) {
  // Handle CORS preflight
  if (request.method === 'OPTIONS') {
    return new Response(null, {
      headers: {
        'Access-Control-Allow-Origin': 'https://jtfnews.org',
        'Access-Control-Allow-Methods': 'POST',
        'Access-Control-Allow-Headers': 'Content-Type',
      },
    });
  }

  if (request.method !== 'POST') {
    return new Response('Method not allowed', { status: 405 });
  }

  const { code } = await request.json();
  if (!code) {
    return new Response(JSON.stringify({ error: 'Missing code' }), { status: 400 });
  }

  // Exchange code for token
  const tokenResponse = await fetch('https://github.com/login/oauth/access_token', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify({
      client_id: GITHUB_CLIENT_ID,       // Set as Worker environment variable
      client_secret: GITHUB_CLIENT_SECRET, // Set as Worker environment variable
      code: code,
    }),
  });

  const tokenData = await tokenResponse.json();

  return new Response(JSON.stringify(tokenData), {
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': 'https://jtfnews.org',
    },
  });
}
```

**Step 3: Add OAuth Client ID to environment**

Add to `.env`:
```
GITHUB_OAUTH_CLIENT_ID=<client_id_from_github>
```

**Step 4: Document the OAuth setup**

Create `documentation/oauth-setup.md` with the deployment instructions for the Cloudflare Worker proxy.

**Step 5: Commit**

```bash
git pull --rebase origin main && ./bu.sh "feat: add GitHub OAuth proxy for journalist authentication"
```

---

## Task 9: Registration Page (docs/register.html)

**Design sections covered:** 7.2 (Registration Flow), 4 (Identity and Transparency), 5 (AI Processing disclosure), 17.4 (CC-BY-SA)

**Files:**
- Create: `docs/register.html`

**Step 1: Create the registration page**

Create `docs/register.html` — a full, professional HTML page that follows the existing JTF design system (dark glassmorphism, Inter font, style.css). Must include:

1. **HTML head** — Same pattern as other pages (favicon, SEO meta, OpenGraph, fonts, style.css)
2. **Navigation** — Same nav bar as all other pages (include "Submit" link)
3. **GitHub OAuth login button** — "Sign in with GitHub" that initiates the OAuth flow
4. **Registration form** (shown after auth):
   - Full legal name (required text input)
   - Location: city, state/province, country (required text input)
   - Professional affiliation (required text input, default "Independent")
   - Financial disclosures section:
     - Dynamic rows: entity name, relationship, percentage
     - "Add disclosure" button to add rows
     - At least one row required
   - Methodology acknowledgment (required checkbox with full text from design doc Section 5)
   - CC-BY-SA license agreement (required checkbox: "I agree that extracted facts from my submissions are licensed CC-BY-SA 4.0")
5. **Submit button** — creates the journalist profile in `data/journalists.json` via GitHub API

**The registration page JavaScript must:**
- Handle GitHub OAuth flow (redirect to GitHub, receive callback with code, exchange for token via proxy)
- Validate all required fields
- Calculate majority funder from disclosed percentages
- Submit registration data as a JSON file to the repository via GitHub Contents API
- Display success/error states

**Step 2: Verify the page renders correctly**

Open `docs/register.html` in a browser and verify:
- Matches existing JTF design aesthetic
- All form fields present
- Methodology disclosure text is complete
- CC-BY-SA checkbox present
- JavaScript has no console errors (auth flow won't work without real OAuth app, but form should render)

**Step 3: Commit**

```bash
git pull --rebase origin main && ./bu.sh "feat: add journalist registration page (docs/register.html)"
```

---

## Task 10: Submission Page (docs/submit.html)

**Design sections covered:** 8.1 (Submission Page), 8.2 (Technical Flow), 8.3 (Submission Data Structure), 10.2 (Web Form Protections)

**Files:**
- Create: `docs/submit.html`

**Step 1: Create the submission page**

Create `docs/submit.html` — follows the existing JTF design system. Must include:

1. **HTML head** — Same pattern as other pages
2. **Navigation** — Same nav bar (include "Submit" link)
3. **Auth check** — If not logged in, show "Sign in with GitHub" button. If logged in but not registered, redirect to register.html. If registered but suspended, show suspension message.
4. **Submission form** (shown only for active, authenticated journalists):
   - Event description (required textarea — "What happened?")
   - Location (required text input — "Where did it occur?")
   - Date/time (required date/time input — "When did it occur?")
   - People involved (text input — "Who was formally involved? Use official titles.")
   - Quantifiable outcomes (text input — "Numbers: casualties, dollar amounts, vote counts")
   - Supporting evidence (optional textarea — "URLs, document references, public records")
   - Disclosure confirmation checkbox: "My financial disclosures are current as of this quarter"
5. **Quota display** — Show "X of Y submissions remaining today"
6. **Submit button** — Creates a JSON file in `data/submissions/` via GitHub API

**The submission page JavaScript must:**
- Check authentication state (GitHub token in sessionStorage)
- Check registration status (fetch journalist profile from repository)
- Check if journalist is active (not suspended)
- Validate all required fields
- Generate submission ID: `sub-YYYY-MM-DD-{journalist_id}-{6char_hash}`
- Create the submission JSON matching the structure in design doc Section 8.3
- Submit via GitHub Contents API to `data/submissions/{id}.json`
- Display success message with: "Your submission has entered the verification queue. If an independent source corroborates your facts within 24 hours, the story will be published."
- Display remaining quota after submission

**Step 2: Verify**

Open `docs/submit.html` in a browser:
- Matches JTF design aesthetic
- All form fields present
- JavaScript has no console errors
- Form validation works (try submitting empty)
- Quota display shows correctly

**Step 3: Commit**

```bash
git pull --rebase origin main && ./bu.sh "feat: add journalist submission page (docs/submit.html)"
```

---

## Task 11: Leaderboard Page (docs/journalists.html)

**Design sections covered:** 13 (Top 10 Leaderboard Page)

**Files:**
- Create: `docs/journalists.html`
- Create: `docs/journalists.json` (initial empty structure, pushed by main.py)

**Step 1: Create initial journalists.json for public site**

Create `docs/journalists.json`:
```json
{
  "leaderboard": [],
  "total_journalists": 0,
  "last_updated": null
}
```

**Step 2: Create the leaderboard page**

Create `docs/journalists.html` — follows JTF design system. Must include:

1. **HTML head** — Same pattern as other pages
2. **Navigation** — Same nav bar (include "Submit" link)
3. **Page title**: "Contributors" (not "Journalists" — more inclusive)
4. **Methodology summary**: Brief explanation of how journalist scoring works
   - "Contributors are scored by the same four metrics as institutional sources."
   - "Numbers only. No labels."
5. **Top 10 leaderboard table** (loaded from `journalists.json`):
   - Rank
   - Name (with affiliation and location)
   - Accuracy score
   - Bias score
   - Speed score
   - Consensus score
   - Verified count (total published stories)
   - Composite score
6. **Funding disclosure** — For each journalist in the leaderboard, show their `owner_display` (same transparency as institutional sources)
7. **"Become a Contributor" call-to-action** — Link to register.html
8. **Empty state** — If no journalists yet: "No contributors yet. Be the first." with link to register.

**The page fetches `journalists.json` and renders the table dynamically.** Same pattern as how `sources.html` fetches source data.

**Step 3: Commit**

```bash
git pull --rebase origin main && ./bu.sh "feat: add journalist leaderboard page (docs/journalists.html)"
```

---

## Task 12: Navigation and How It Works Updates

**Design sections covered:** 15.2 (Updated Pages)

**Files:**
- Modify: `docs/index.html` — add "Submit" to navigation and link in appropriate section
- Modify: `docs/how-it-works.html` — add section explaining journalist submissions
- Modify: ALL other HTML pages with nav bar — add "Submit" link

**Step 1: Update navigation across all pages**

Every page with the nav bar (`site-nav__links`) needs "Submit" and "Contributors" added:

```html
<li><a href="journalists.html">Contributors</a></li>
<li><a href="submit.html">Submit</a></li>
```

Also update the mobile overlay nav (`nav-overlay`) in each page.

Pages to update:
- `docs/index.html`
- `docs/how-it-works.html`
- `docs/sources.html`
- `docs/whitepaper.html`
- `docs/archive.html`
- `docs/corrections.html`
- `docs/screensaver-setup.html`

**Step 2: Add journalist submission section to how-it-works.html**

Add a new section explaining how journalist submissions work, covering:
- What journalists submit (original reporting)
- The two-source verification rule (same as automated sources)
- AI processing (identical treatment)
- Financial independence check
- Scoring (same four metrics)
- The leaderboard

Use the same HTML structure and CSS classes as existing sections in the file.

**Step 3: Add contributor mention to index.html**

Add a brief mention in the appropriate section of the landing page, linking to the submit page and the contributors page.

**Step 4: Verify all pages render correctly**

Open each updated page in a browser and verify:
- Navigation links work
- No broken layout
- New sections match existing design language

**Step 5: Commit**

```bash
git pull --rebase origin main && ./bu.sh "feat: add Submit/Contributors navigation to all pages, update how-it-works"
```

---

## Task 13: Extend Quarterly Audit for Journalists

**Design sections covered:** 11 (Quarterly Financial Disclosure Audit), 16.3 (Quarterly Audit Extension)

**Files:**
- Modify: `main.py` — find the existing quarterly audit section (line ~6012) and extend it

**Step 1: Integrate disclosure freshness into startup**

In the existing quarterly audit check (around line 6012 in the `# QUARTERLY OWNERSHIP AUDIT` section), add a call to `check_disclosure_freshness()` alongside the existing institutional audit.

Find the startup audit check and add:

```python
    # Also check journalist disclosure freshness (same quarterly cadence)
    check_disclosure_freshness()
```

**Step 2: Extend the --audit flag**

If the `--audit` flag triggers an interactive ownership review, extend it to also list journalists with stale disclosures and show their current status.

Add to the audit output:

```python
    # Journalist disclosure audit
    journalists = load_journalists()
    now = datetime.now(timezone.utc)
    current_quarter = f"Q{(now.month - 1) // 3 + 1} {now.year}"

    stale_journalists = []
    for jid, profile in journalists.items():
        if profile.get("disclosure_quarter") != current_quarter:
            stale_journalists.append(profile)

    if stale_journalists:
        print(f"\n{'='*60}")
        print(f"JOURNALISTS WITH STALE DISCLOSURES ({len(stale_journalists)})")
        print(f"{'='*60}")
        for j in stale_journalists:
            print(f"  {j['name']} ({j['github_username']}) — last: {j.get('disclosure_quarter', 'never')}")
        print(f"\nThese journalists are suspended until they update disclosures.")
    else:
        print(f"\nAll journalist disclosures current for {current_quarter}.")
```

**Step 3: Commit**

```bash
git pull --rebase origin main && ./bu.sh "feat: extend quarterly audit to include journalist disclosure freshness"
```

---

## Task 14: Leaderboard Generation in Push Cycle

**Design sections covered:** 13.3 (Update Frequency), 14 (Data Storage public files)

**Files:**
- Modify: `main.py` — add leaderboard generation function and integrate into the daily archive/push cycle

**Step 1: Add generate_leaderboard() function**

```python
def generate_leaderboard():
    """Calculate Top 10 journalist leaderboard and push to GitHub Pages.

    Composite score = (accuracy × 4 + bias × 3 + speed × 2 + consensus × 1) / 10

    Only includes active journalists with at least 1 verified submission.
    Pushed to docs/journalists.json for the public website.
    """
    journalists = load_journalists()

    # Filter: active journalists with verified submissions
    eligible = []
    for jid, profile in journalists.items():
        if profile.get("status") == "active" and profile.get("stats", {}).get("verified", 0) > 0:
            ratings = profile.get("ratings", {})
            composite = (
                ratings.get("accuracy", 0) * 4 +
                ratings.get("bias", 0) * 3 +
                ratings.get("speed", 0) * 2 +
                ratings.get("consensus", 0) * 1
            ) / 10

            eligible.append({
                "rank": 0,  # Set after sorting
                "name": profile.get("name", jid),
                "affiliation": profile.get("affiliation", "Independent"),
                "location": profile.get("location", ""),
                "accuracy": ratings.get("accuracy", 0),
                "bias": ratings.get("bias", 0),
                "speed": ratings.get("speed", 0),
                "consensus": ratings.get("consensus", 0),
                "composite": round(composite, 2),
                "verified": profile.get("stats", {}).get("verified", 0),
                "owner_display": profile.get("owner_display", "Undisclosed"),
                "registered": profile.get("registered", ""),
                "data_points": profile.get("stats", {}).get("successes", 0) + profile.get("stats", {}).get("failures", 0)
            })

    # Sort by composite score (descending), take top 10
    eligible.sort(key=lambda x: x["composite"], reverse=True)
    top_10 = eligible[:10]

    # Assign ranks
    for i, entry in enumerate(top_10):
        entry["rank"] = i + 1

    # Write to local docs/journalists.json
    leaderboard_data = {
        "leaderboard": top_10,
        "total_journalists": len(journalists),
        "total_active": sum(1 for j in journalists.values() if j.get("status") == "active"),
        "total_verified_stories": sum(j.get("stats", {}).get("verified", 0) for j in journalists.values()),
        "last_updated": datetime.now(timezone.utc).isoformat()
    }

    leaderboard_file = BASE_DIR / "docs" / "journalists.json"
    with open(leaderboard_file, 'w') as f:
        json.dump(leaderboard_data, f, indent=2)

    # Push to GitHub Pages
    push_to_ghpages(
        [(leaderboard_file, "journalists.json")],
        "Update journalist leaderboard"
    )

    log.info(f"Leaderboard updated: {len(top_10)} journalists ranked")
```

**Step 2: Integrate into the daily cycle**

Find the midnight archive section (around `check_midnight_archive()` at line ~6246) and add:

```python
    # Update journalist leaderboard (daily at midnight alongside archive)
    generate_leaderboard()
```

**Step 3: Commit**

```bash
git pull --rebase origin main && ./bu.sh "feat: add leaderboard generation and daily push to GitHub Pages"
```

---

## Task 15: RSS Feed Extension for Journalist Sources

**Design sections covered:** 4.2 (Display Format — RSS feed)

**Files:**
- Modify: `main.py` — find the RSS feed generation functions and ensure journalist source attribution is properly formatted

**Step 1: Verify RSS source attribution handles journalist sources**

Check the existing RSS feed functions (`update_rss_feed()` around line 2180). Ensure the source attribution includes journalist names correctly. The existing format should work if `source_name` is properly set (which it is — `get_journalist_display_name()` returns the formatted name).

If the RSS feed includes `<source>` elements with ownership data, extend to include journalist ownership:

```python
    # Handle journalist source ownership in RSS
    for source_data in story_sources:
        source_id = source_data.get("source_id", "")
        if source_id.startswith("journalist:"):
            journalist_id = source_id.split(":", 1)[1]
            info = get_journalist_info(journalist_id)
            if info:
                source_el = ET.SubElement(item, "jtf:source")
                source_el.set("name", get_journalist_display_name(journalist_id))
                source_el.set("accuracy", str(info.get("ratings", {}).get("accuracy", 0)))
                source_el.set("bias", str(info.get("ratings", {}).get("bias", 0)))
                owner_el = ET.SubElement(source_el, "jtf:owner")
                owner_el.set("name", info.get("owner_display", "Undisclosed"))
```

**Step 2: Commit**

```bash
git pull --rebase origin main && ./bu.sh "feat: extend RSS feed to include journalist source attribution"
```

---

## Task 16: End-to-End Verification

**Design sections covered:** ALL sections 1-19

**Files:**
- All modified files

**This task verifies that EVERY section of the design document has been implemented.**

**Step 1: Design Document Compliance Checklist**

Go through each section of `docs/plans/2026-03-02-journalist-submissions-design.md` and verify:

| Section | What to Verify | How |
|---------|---------------|-----|
| 1. What a Journalist Submits | Submit form accepts event descriptions | Open submit.html, verify form fields |
| 2. Verification Standard | Submissions enter queue, need 2nd source | Read process_cycle() code, trace submission flow |
| 3. Financial Independence | are_sources_unrelated() checks journalist funding | Run the Task 3 verification test |
| 4. Identity and Transparency | Registration requires name, location, disclosures | Open register.html, verify form |
| 5. AI Processing | extract_fact() is called on submissions | Read process_cycle() journalist section |
| 6. Scoring System | All four scores calculated for journalists | Run the Task 4 verification test |
| 7. Registration and Vetting | Open registration, GitHub OAuth, data stored | Open register.html, verify flow |
| 8. Submission Form | Web form with all required fields, GitHub API | Open submit.html, verify form |
| 9. Source Independence | get_source_info() handles journalist: prefix | Run Task 2 verification |
| 10. Abuse Prevention | Quota system based on accuracy | Run Task 4 quota test |
| 11. Quarterly Audit | check_disclosure_freshness() integrated | Run Task 6 verification |
| 12. Corrections | Corrections code handles journalist sources | Read process_cycle() correction section |
| 13. Top 10 Leaderboard | generate_leaderboard() produces JSON, page renders | Open journalists.html |
| 14. Data Storage | journalists.json, submissions/, processed/ exist | ls data/journalists.json data/submissions/ |
| 15. Website Changes | 3 new pages, nav updated on all pages | Open each page, check navigation |
| 16. main.py Changes | All 10 new functions exist, 9 functions modified | grep for each function name |
| 17. Scope/Constraints | No community channels, no compensation | Read code — no extra features |
| 18. Security | 7-day retention, no PII in public files | Read clean_old_submissions(), journalists.json |
| 19. What It Does NOT Do | No source curation, no engagement, no payment | Verify none implemented |

**Step 2: Function existence check**

```bash
cd /Users/larryseyer/JTFNews && source venv/bin/activate && python3 -c "
import main

# New functions that MUST exist
required = [
    'load_journalists', 'save_journalists', 'get_journalist_info',
    'get_journalist_display_name', 'register_journalist', 'get_source_info',
    'load_pending_submissions', 'mark_submission_processed', 'clean_old_submissions',
    'check_journalist_quota', 'get_journalist_quota', 'update_journalist_bias_score',
    'check_disclosure_freshness', 'update_journalist_disclosure', 'generate_leaderboard'
]

missing = [f for f in required if not hasattr(main, f)]
if missing:
    print(f'FAIL: Missing functions: {missing}')
else:
    print(f'PASS: All {len(required)} new functions exist')
"
```

**Step 3: File existence check**

```bash
# New files that MUST exist
for f in docs/register.html docs/submit.html docs/journalists.html docs/journalists.json docs/oauth-worker.js; do
    if [ -f "$f" ]; then
        echo "PASS: $f exists"
    else
        echo "FAIL: $f missing"
    fi
done

# Data directories
for d in data/submissions data/submissions/processed; do
    if [ -d "$d" ]; then
        echo "PASS: $d directory exists"
    else
        echo "FAIL: $d directory missing"
    fi
done
```

**Step 4: Navigation check**

```bash
# Verify all HTML pages have "Submit" and "Contributors" in navigation
for f in docs/index.html docs/how-it-works.html docs/sources.html docs/whitepaper.html docs/archive.html docs/corrections.html docs/screensaver-setup.html docs/register.html docs/submit.html docs/journalists.html; do
    if grep -q "submit.html" "$f" 2>/dev/null && grep -q "journalists.html" "$f" 2>/dev/null; then
        echo "PASS: $f has Submit and Contributors links"
    else
        echo "FAIL: $f missing nav links"
    fi
done
```

**Step 5: Whitepaper compliance check**

Manually verify:
- [ ] No compensation mechanism exists in the code
- [ ] No engagement/reply/messaging features exist
- [ ] 7-day data retention enforced via `clean_old_submissions(max_age_days=7)`
- [ ] CC-BY-SA license referenced in registration form
- [ ] Two-source verification cannot be bypassed
- [ ] Financial independence check cannot be bypassed
- [ ] Same AI prompt used for journalist and institutional sources
- [ ] Quarterly audit covers journalists

**Step 6: main.py loads without errors**

```bash
cd /Users/larryseyer/JTFNews && source venv/bin/activate && python3 -c "import main; print('main.py loads successfully')"
```

---

## Task 17: Final Commit and CLAUDE.md Update

**Files:**
- Modify: `CLAUDE.md` — document the journalist submission system

**Step 1: Update CLAUDE.md**

Add a new section to CLAUDE.md documenting the journalist submission system:

```markdown
## Journalist Submission System

Independent journalists can submit original reporting via `jtfnews.org/submit`. Submissions enter the same verification pipeline as automated sources.

### Key Principle
A journalist is a source. Sources follow the methodology. The methodology does not bend.

### How It Works
1. Journalist registers at `jtfnews.org/register` (GitHub OAuth, real name, financial disclosures)
2. Submits original reporting via web form at `jtfnews.org/submit`
3. Submission processed by same AI (extract_fact) — identical treatment
4. Enters queue awaiting independent corroboration (24-hour timeout)
5. Two-source rule: journalist + unrelated source = published
6. Financial independence check: no common majority funder between journalist and corroborating source

### Journalist Source IDs
Journalist source IDs use the prefix `journalist:` (e.g., `journalist:janedoe`). Functions that handle source IDs (are_sources_unrelated, get_learned_rating, record_verification_success, etc.) check for this prefix and route to journalist data.

### Data Files
| File | Purpose |
|------|---------|
| `data/journalists.json` | Journalist profiles, disclosures, scores |
| `data/submissions/` | Pending submission JSON files |
| `data/submissions/processed/` | Processed submissions (7-day retention) |
| `docs/journalists.json` | Public leaderboard data (pushed to GitHub Pages) |

### Quarterly Audit
Journalist financial disclosures are audited on the same quarterly schedule as institutional source ownership. Stale disclosures → journalist suspended until updated.
```

**Step 2: Final commit**

```bash
git pull --rebase origin main && ./bu.sh "docs: update CLAUDE.md with journalist submission system documentation"
```

---

## Completion Criteria

**The plan is complete ONLY when ALL of the following are true:**

1. All 17 tasks are completed with passing verification
2. All 15 new Python functions exist in main.py and load without errors
3. All 3 new HTML pages (register.html, submit.html, journalists.html) exist and render
4. Navigation is updated on ALL existing HTML pages
5. how-it-works.html has a journalist submission section
6. The end-to-end verification (Task 16) passes every check
7. CLAUDE.md is updated with journalist system documentation
8. Every section (1-19) of the design document is implemented — nothing deferred
9. All commits are made via `./bu.sh` with `git pull --rebase` first
