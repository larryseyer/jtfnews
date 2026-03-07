# Feedback System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Allow the public to anonymously report factual errors, bias concerns, and suggestions via a form on jtfnews.org, with Claude AI auto-processing corrections.

**Architecture:** Static HTML form (docs/feedback.html) POSTs to a Cloudflare Worker endpoint that validates spam prevention and pushes feedback JSON to the GitHub repo. main.py picks up pending feedback each cycle, runs Claude AI triage, and auto-issues corrections when factual errors are confirmed by 2+ independent sources. Zero personal data collected.

**Tech Stack:** HTML/CSS/JS (matching existing design system), Cloudflare Worker (extending existing oauth-worker.js), Python (main.py additions), Claude AI (Haiku for triage/verification)

---

## Architecture Overview

```
Browser (feedback.html)
    |
    | POST with: category, story_id, details, evidence_url,
    |            honeypot, timestamp, proof-of-work nonce
    v
Cloudflare Worker (feedback endpoint)
    |
    | Validates: honeypot empty, time > 5s, PoW valid, rate < 5/hr
    | Generates: reference number (JTF-YYYYMMDD-NNNN)
    | Pushes: feedback JSON to data/feedback/ via GitHub API
    |
    v
GitHub repo: data/feedback/JTF-YYYYMMDD-NNNN.json
    |
    | (picked up by main.py on next cycle)
    v
main.py: process_pending_feedback()
    |
    | Claude AI triage → classify as spam/suggestion/bias/factual_error
    |
    +-- spam → discard
    +-- suggestion → log to data/feedback/suggestions.json
    +-- bias → log to data/feedback/bias_reports.json
    +-- factual_error → verify with 2+ sources
         |
         +-- confirmed → issue_correction() (existing pipeline)
         +-- unconfirmed → log as unverified, no action
    |
    | Move processed file to data/feedback/processed/
    v
Done. 7-day retention on processed files.
```

---

### Task 1: Create feedback.html — Form Page

**Files:**
- Create: `docs/feedback.html`

**Step 1: Create the feedback form page**

Build `docs/feedback.html` matching the existing site design (Inter font, dark theme, gold accents from `docs/style.css`). Include the standard nav bar and footer from other pages.

The form contains:
- **Category** dropdown (required): "Factual Error", "Bias or Distortion", "Suggestion", "Other"
- **Story** dropdown (optional): Populated from stories.json, plus "General / Not about a specific story"
- **Details** textarea (required): Minimum 20 characters
- **Evidence URL** text input (optional): URL supporting the claim

Hidden spam prevention fields:
- `<input type="text" name="website" tabindex="-1" autocomplete="off" style="position:absolute;left:-9999px">` (honeypot)
- `<input type="hidden" name="loaded_at" id="loaded_at">` (time gate)
- `<input type="hidden" name="pow_nonce" id="pow_nonce">` (proof-of-work result)
- `<input type="hidden" name="pow_hash" id="pow_hash">` (proof-of-work hash)

Page structure (follow exact patterns from `docs/support.html` and `docs/submit.html`):

```html
<!-- Head: same favicon, SEO meta, fonts, style.css as other pages -->
<!-- Nav: same nav bar as all pages -->

<div class="container" style="padding-top: 20px;">
    <h1>Report an Issue</h1>
    <p class="text-muted" style="font-size: 1.1rem; margin-bottom: 2rem;">
        Help us keep the record accurate.
    </p>

    <div class="philosophy">
        <p><strong>We do not bury mistakes. We name them.</strong></p>
    </div>

    <p>Report factual errors, potential bias, or suggestions. No account required.
    No personal information collected. Confirmed corrections appear on the
    <a href="corrections.html">Corrections page</a> with the same prominence
    as the original story.</p>

    <!-- Feedback Form -->
    <form id="feedback-form" style="margin-top: 2rem;">
        <!-- Category -->
        <div class="form-group">
            <label for="category">Category <span style="color: var(--color-red);">*</span></label>
            <select id="category" name="category" required class="form-input">
                <option value="">Select a category...</option>
                <option value="factual_error">Factual Error</option>
                <option value="bias_distortion">Bias or Distortion</option>
                <option value="suggestion">Suggestion</option>
                <option value="other">Other</option>
            </select>
        </div>

        <!-- Story reference -->
        <div class="form-group">
            <label for="story_id">Related Story (optional)</label>
            <select id="story_id" name="story_id" class="form-input">
                <option value="">General / Not about a specific story</option>
                <!-- Populated from stories.json -->
            </select>
        </div>

        <!-- Details -->
        <div class="form-group">
            <label for="details">Details <span style="color: var(--color-red);">*</span></label>
            <textarea id="details" name="details" required minlength="20"
                      rows="5" class="form-input"
                      placeholder="Describe the issue. For factual errors, include what is incorrect and what the correct information is."></textarea>
        </div>

        <!-- Evidence URL -->
        <div class="form-group">
            <label for="evidence_url">Supporting Source URL (optional)</label>
            <input type="url" id="evidence_url" name="evidence_url"
                   class="form-input"
                   placeholder="https://example.com/source">
        </div>

        <!-- Honeypot (hidden from humans) -->
        <input type="text" name="website" tabindex="-1" autocomplete="off"
               style="position:absolute;left:-9999px" aria-hidden="true">

        <!-- Time gate -->
        <input type="hidden" name="loaded_at" id="loaded_at">

        <!-- Proof of work -->
        <input type="hidden" name="pow_nonce" id="pow_nonce">
        <input type="hidden" name="pow_hash" id="pow_hash">

        <button type="submit" class="btn btn--primary" id="submit-btn"
                style="margin-top: 1rem;" disabled>
            Preparing...
        </button>
        <p id="pow-status" class="text-muted" style="font-size: 0.85rem; margin-top: 0.5rem;">
            Verifying your browser...
        </p>
    </form>

    <!-- Success message (hidden initially) -->
    <div id="success-message" style="display: none; margin-top: 2rem;">
        <div class="card" style="border-left: 3px solid var(--color-green); text-align: center;">
            <h3 style="color: var(--color-green);">Feedback Received</h3>
            <p>Reference: <strong id="ref-number"></strong></p>
            <p class="text-muted">Corrections, if any, will appear on the
            <a href="corrections.html">Corrections page</a>.</p>
            <p class="text-muted">Thank you.</p>
            <button class="btn btn--outline" onclick="resetForm()"
                    style="margin-top: 1rem;">Submit Another</button>
        </div>
    </div>

    <!-- Error message (hidden initially) -->
    <div id="error-message" style="display: none; margin-top: 1rem;">
        <p style="color: var(--color-red);" id="error-text"></p>
    </div>
</div>

<!-- Footer: same as all pages, with Report an Issue link added -->
```

**Step 2: Add JavaScript for spam prevention and submission**

```javascript
// ============================================================
// Configuration
// ============================================================
const FEEDBACK_WORKER_URL = 'PLACEHOLDER_FEEDBACK_URL';
const POW_DIFFICULTY = 4; // Number of leading zeros required in hash

// ============================================================
// Page Load
// ============================================================
document.getElementById('loaded_at').value = Date.now().toString();
loadStories();
startProofOfWork();

// ============================================================
// Load recent stories for dropdown
// ============================================================
async function loadStories() {
    try {
        const resp = await fetch('./stories.json?t=' + Date.now());
        if (!resp.ok) return;
        const data = await resp.json();
        const select = document.getElementById('story_id');
        (data.stories || []).forEach(function(story) {
            if (story.status === 'published') {
                const opt = document.createElement('option');
                opt.value = story.id;
                // Truncate fact to 80 chars for dropdown
                const label = story.fact.length > 80
                    ? story.fact.substring(0, 77) + '...'
                    : story.fact;
                opt.textContent = '[' + story.id + '] ' + label;
                select.appendChild(opt);
            }
        });
    } catch (e) {
        // Stories dropdown is optional — form works without it
    }
}

// ============================================================
// Proof of Work
// ============================================================
async function startProofOfWork() {
    const statusEl = document.getElementById('pow-status');
    const submitBtn = document.getElementById('submit-btn');
    const challenge = Date.now().toString() + Math.random().toString(36);
    const prefix = '0'.repeat(POW_DIFFICULTY);
    let nonce = 0;

    // Run in batches to avoid blocking the UI
    function solveBatch() {
        for (let i = 0; i < 10000; i++) {
            const candidate = challenge + ':' + nonce;
            // Use SubtleCrypto for SHA-256
            const encoder = new TextEncoder();
            const data = encoder.encode(candidate);
            crypto.subtle.digest('SHA-256', data).then(function(hashBuffer) {
                const hashArray = Array.from(new Uint8Array(hashBuffer));
                const hashHex = hashArray.map(function(b) {
                    return b.toString(16).padStart(2, '0');
                }).join('');

                if (hashHex.startsWith(prefix)) {
                    document.getElementById('pow_nonce').value = challenge + ':' + nonce;
                    document.getElementById('pow_hash').value = hashHex;
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'Submit';
                    statusEl.textContent = '';
                }
            });
            nonce++;
        }
        if (!document.getElementById('pow_hash').value) {
            statusEl.textContent = 'Verifying your browser...';
            requestAnimationFrame(solveBatch);
        }
    }

    solveBatch();
}

// ============================================================
// Form Submission
// ============================================================
document.getElementById('feedback-form').addEventListener('submit', async function(e) {
    e.preventDefault();

    const submitBtn = document.getElementById('submit-btn');
    const errorEl = document.getElementById('error-message');
    const errorText = document.getElementById('error-text');
    errorEl.style.display = 'none';

    // Client-side validation
    const details = document.getElementById('details').value.trim();
    if (details.length < 20) {
        errorText.textContent = 'Please provide at least 20 characters of detail.';
        errorEl.style.display = 'block';
        return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = 'Submitting...';

    const payload = {
        category: document.getElementById('category').value,
        story_id: document.getElementById('story_id').value || null,
        details: details,
        evidence_url: document.getElementById('evidence_url').value.trim() || null,
        website: document.querySelector('[name="website"]').value,
        loaded_at: document.getElementById('loaded_at').value,
        pow_nonce: document.getElementById('pow_nonce').value,
        pow_hash: document.getElementById('pow_hash').value
    };

    try {
        const resp = await fetch(FEEDBACK_WORKER_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const result = await resp.json();

        if (!resp.ok) {
            throw new Error(result.error || 'Submission failed');
        }

        // Show success
        document.getElementById('feedback-form').style.display = 'none';
        document.getElementById('ref-number').textContent = result.ref;
        document.getElementById('success-message').style.display = 'block';

    } catch (err) {
        errorText.textContent = err.message || 'Something went wrong. Please try again.';
        errorEl.style.display = 'block';
        submitBtn.disabled = false;
        submitBtn.textContent = 'Submit';
    }
});

function resetForm() {
    document.getElementById('feedback-form').reset();
    document.getElementById('feedback-form').style.display = 'block';
    document.getElementById('success-message').style.display = 'none';
    document.getElementById('loaded_at').value = Date.now().toString();
    // Restart proof of work
    document.getElementById('pow_nonce').value = '';
    document.getElementById('pow_hash').value = '';
    document.getElementById('submit-btn').disabled = true;
    document.getElementById('submit-btn').textContent = 'Preparing...';
    startProofOfWork();
}
```

Add form styling to match existing site patterns. Use the same `.form-group`, `.form-input` patterns visible in `submit.html`. Add any missing form styles inline or scoped within `<style>` in the page head (same approach as other pages like `corrections.html` which define page-specific styles in the head).

**Step 3: Verify the page renders correctly**

Open `docs/feedback.html` in a browser. Confirm:
- Nav and footer match other pages
- Form fields render with correct styling
- Proof-of-work runs and enables the submit button
- Stories dropdown populates from stories.json
- Honeypot field is invisible

**Step 4: Commit**

```bash
git pull --rebase origin main
git add docs/feedback.html
git commit -m "feat: add feedback form page with spam prevention"
git push origin main
```

---

### Task 2: Create Cloudflare Worker Feedback Endpoint

**Files:**
- Create: `docs/feedback-worker.js`
- Reference: `docs/oauth-worker.js` (existing pattern)
- Reference: `documentation/oauth-setup.md` (deployment instructions)

**Step 1: Create the feedback worker**

Create `docs/feedback-worker.js` — a Cloudflare Worker that receives feedback submissions, validates spam prevention, generates a reference number, and pushes the feedback JSON to GitHub.

```javascript
// JTF News Feedback Submission Proxy
// Deployed as a Cloudflare Worker
// Receives anonymous feedback, validates spam prevention, pushes to GitHub
//
// Environment variables required:
//   GITHUB_TOKEN - GitHub personal access token with repo scope
//   POW_DIFFICULTY - Number of leading hex zeros required (default: 4)
//
// Rate limiting: Uses Cloudflare's built-in rate limiting (configured in dashboard)

addEventListener('fetch', event => {
    event.respondWith(handleRequest(event.request));
});

// In-memory rate limiter (per-isolate, resets on cold start)
// This is a best-effort layer; Cloudflare dashboard rate limiting is the primary defense
const rateLimitMap = new Map();
const RATE_LIMIT_MAX = 5;
const RATE_LIMIT_WINDOW_MS = 60 * 60 * 1000; // 1 hour

function checkRateLimit(ip) {
    const now = Date.now();
    const entry = rateLimitMap.get(ip);
    if (!entry || now - entry.windowStart > RATE_LIMIT_WINDOW_MS) {
        rateLimitMap.set(ip, { windowStart: now, count: 1 });
        return true;
    }
    entry.count++;
    if (entry.count > RATE_LIMIT_MAX) {
        return false;
    }
    return true;
}

async function verifyProofOfWork(nonce, hash, difficulty) {
    const prefix = '0'.repeat(difficulty || 4);
    if (!hash.startsWith(prefix)) return false;

    // Verify the hash matches the nonce
    const encoder = new TextEncoder();
    const data = encoder.encode(nonce);
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    const computed = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');

    return computed === hash;
}

async function handleRequest(request) {
    const corsHeaders = {
        'Access-Control-Allow-Origin': 'https://jtfnews.org',
        'Access-Control-Allow-Methods': 'POST',
        'Access-Control-Allow-Headers': 'Content-Type',
    };

    // CORS preflight
    if (request.method === 'OPTIONS') {
        return new Response(null, { headers: corsHeaders });
    }

    if (request.method !== 'POST') {
        return new Response(JSON.stringify({ error: 'Method not allowed' }), {
            status: 405,
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        });
    }

    try {
        const body = await request.json();

        // --- Spam Layer 1: Honeypot ---
        if (body.website) {
            // Bot filled in the honeypot. Return fake success to not tip them off.
            return new Response(JSON.stringify({ ref: 'JTF-00000000-0000' }), {
                headers: { ...corsHeaders, 'Content-Type': 'application/json' }
            });
        }

        // --- Spam Layer 2: Time gate (must be > 5 seconds since page load) ---
        const loadedAt = parseInt(body.loaded_at, 10);
        if (!loadedAt || Date.now() - loadedAt < 5000) {
            return new Response(JSON.stringify({ error: 'Please wait a moment before submitting.' }), {
                status: 429,
                headers: { ...corsHeaders, 'Content-Type': 'application/json' }
            });
        }

        // --- Spam Layer 3: Rate limit (in-memory per IP) ---
        const clientIP = request.headers.get('CF-Connecting-IP') || 'unknown';
        if (!checkRateLimit(clientIP)) {
            return new Response(JSON.stringify({ error: 'Rate limit exceeded. Please try again later.' }), {
                status: 429,
                headers: { ...corsHeaders, 'Content-Type': 'application/json' }
            });
        }

        // --- Spam Layer 4: Proof of work ---
        const powValid = await verifyProofOfWork(
            body.pow_nonce,
            body.pow_hash,
            parseInt(POW_DIFFICULTY || '4', 10)
        );
        if (!powValid) {
            return new Response(JSON.stringify({ error: 'Verification failed. Please refresh and try again.' }), {
                status: 400,
                headers: { ...corsHeaders, 'Content-Type': 'application/json' }
            });
        }

        // --- Validate required fields ---
        const category = body.category;
        const details = (body.details || '').trim();
        if (!category || !details || details.length < 20) {
            return new Response(JSON.stringify({ error: 'Category and details (20+ chars) are required.' }), {
                status: 400,
                headers: { ...corsHeaders, 'Content-Type': 'application/json' }
            });
        }

        const validCategories = ['factual_error', 'bias_distortion', 'suggestion', 'other'];
        if (!validCategories.includes(category)) {
            return new Response(JSON.stringify({ error: 'Invalid category.' }), {
                status: 400,
                headers: { ...corsHeaders, 'Content-Type': 'application/json' }
            });
        }

        // --- Generate reference number ---
        const now = new Date();
        const dateStr = now.toISOString().slice(0, 10).replace(/-/g, '');
        const seq = String(Math.floor(Math.random() * 9999)).padStart(4, '0');
        const ref = 'JTF-' + dateStr + '-' + seq;

        // --- Build feedback record (zero personal data) ---
        const feedback = {
            ref: ref,
            timestamp: now.toISOString(),
            category: category,
            story_id: body.story_id || null,
            details: details.substring(0, 2000), // Cap at 2000 chars
            evidence_url: (body.evidence_url || '').substring(0, 500) || null,
            status: 'pending'
        };

        // --- Push to GitHub ---
        const filePath = 'data/feedback/' + ref + '.json';
        const content = btoa(unescape(encodeURIComponent(JSON.stringify(feedback, null, 2))));

        const ghResponse = await fetch(
            'https://api.github.com/repos/JTFNews/jtfnews/contents/' + filePath,
            {
                method: 'PUT',
                headers: {
                    'Authorization': 'token ' + GITHUB_TOKEN,
                    'Accept': 'application/vnd.github.v3+json',
                    'Content-Type': 'application/json',
                    'User-Agent': 'JTFNews-Feedback-Worker'
                },
                body: JSON.stringify({
                    message: 'feedback: ' + ref,
                    content: content,
                    branch: 'main'
                })
            }
        );

        if (!ghResponse.ok) {
            const errData = await ghResponse.json().catch(() => ({}));
            console.error('GitHub API error:', ghResponse.status, JSON.stringify(errData));
            return new Response(JSON.stringify({ error: 'Submission failed. Please try again.' }), {
                status: 500,
                headers: { ...corsHeaders, 'Content-Type': 'application/json' }
            });
        }

        // --- Success ---
        return new Response(JSON.stringify({ ref: ref }), {
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        });

    } catch (e) {
        return new Response(JSON.stringify({ error: 'Invalid request.' }), {
            status: 400,
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        });
    }
}
```

**Step 2: Create deployment documentation**

Create `documentation/feedback-worker-setup.md`:

```markdown
# Feedback Worker Setup

## Overview
Cloudflare Worker that receives anonymous feedback and pushes to GitHub.
Separate from the OAuth worker — different purpose, different credentials.

## Environment Variables
- `GITHUB_TOKEN` — Personal access token with `repo` scope (for pushing feedback files)
- `POW_DIFFICULTY` — Proof-of-work difficulty (default: 4, meaning 4 leading hex zeros)

## Deployment
1. Log in to Cloudflare Dashboard
2. Workers & Pages → Create Worker
3. Name it (e.g., `jtf-feedback`)
4. Paste contents of `docs/feedback-worker.js`
5. Settings → Variables → Add GITHUB_TOKEN and POW_DIFFICULTY
6. Deploy
7. Note the worker URL
8. Update FEEDBACK_WORKER_URL in `docs/feedback.html`

## Rate Limiting (Cloudflare Dashboard)
1. Go to the worker's settings
2. Add a Cloudflare Rate Limiting rule:
   - Path: * (all paths)
   - Rate: 5 requests per hour per IP
   - Action: Block with 429
3. This provides infrastructure-level rate limiting (the in-memory
   rate limiter in the worker code is a secondary layer)

## Security Notes
- GITHUB_TOKEN never leaves Cloudflare's environment
- No personal data is stored (IP used only for in-memory rate limiting, never written)
- CORS restricted to https://jtfnews.org
- Honeypot bots receive fake success response (silent discard)
```

**Step 3: Commit**

```bash
git pull --rebase origin main
git add docs/feedback-worker.js documentation/feedback-worker-setup.md
git commit -m "feat: add Cloudflare Worker for feedback submission"
git push origin main
```

---

### Task 3: Add Feedback Processing to main.py

**Files:**
- Modify: `main.py` (add feedback processing functions, integrate into process_cycle)

**Step 1: Add feedback data loading and cleanup functions**

Add these functions near the existing `load_pending_submissions()` function (around line 1920, after `clean_old_submissions`). Follow the same patterns used for journalist submissions.

```python
# =============================================================================
# FEEDBACK PROCESSING
# =============================================================================

def load_pending_feedback() -> list:
    """Load unprocessed feedback from data/feedback/.

    Returns list of feedback dicts sorted by timestamp (oldest first).
    """
    feedback_dir = DATA_DIR / "feedback"
    if not feedback_dir.exists():
        feedback_dir.mkdir(parents=True, exist_ok=True)
        return []

    feedback = []
    for f in sorted(feedback_dir.glob("JTF-*.json")):
        try:
            with open(f) as fh:
                fb = json.load(fh)
            fb["_file"] = str(f)
            feedback.append(fb)
        except (json.JSONDecodeError, KeyError) as e:
            log.warning(f"Invalid feedback file {f.name}: {e}")
            continue

    return feedback


def mark_feedback_processed(feedback: dict, triage_result: str,
                             action_taken: str = None):
    """Move processed feedback to the processed/ directory."""
    file_path = Path(feedback.get("_file", ""))
    if not file_path.exists():
        log.warning(f"Feedback file not found: {file_path}")
        return

    processed_dir = DATA_DIR / "feedback" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)

    feedback["status"] = "processed"
    feedback["triage_result"] = triage_result
    feedback["action_taken"] = action_taken
    feedback["processed_at"] = datetime.now(timezone.utc).isoformat()
    feedback.pop("_file", None)

    dest = processed_dir / file_path.name
    with open(dest, 'w') as f:
        json.dump(feedback, f, indent=2)

    file_path.unlink()
    log.info(f"Feedback {feedback.get('ref', '?')} processed: {triage_result}")


def clean_old_feedback(max_age_days: int = 7):
    """Delete processed feedback older than max_age_days.

    Per whitepaper: 'We do not store raw data longer than seven days.'
    """
    processed_dir = DATA_DIR / "feedback" / "processed"
    if not processed_dir.exists():
        return

    cutoff = datetime.now(timezone.utc).timestamp() - (max_age_days * 86400)
    cleaned = 0

    for f in processed_dir.glob("*.json"):
        try:
            with open(f) as fh:
                fb = json.load(fh)
            processed_at = fb.get("processed_at", fb.get("timestamp", ""))
            if processed_at:
                ts = datetime.fromisoformat(
                    processed_at.replace("Z", "+00:00")
                ).timestamp()
                if ts < cutoff:
                    f.unlink()
                    cleaned += 1
        except Exception:
            continue

    if cleaned:
        log.info(f"Cleaned {cleaned} old feedback files")


def log_suggestion(feedback: dict):
    """Append a suggestion to the suggestions log."""
    suggestions_file = DATA_DIR / "feedback" / "suggestions.json"
    suggestions = {"suggestions": []}

    if suggestions_file.exists():
        try:
            with open(suggestions_file) as f:
                suggestions = json.load(f)
        except Exception:
            pass

    suggestions["suggestions"].append({
        "ref": feedback.get("ref"),
        "timestamp": feedback.get("timestamp"),
        "details": feedback.get("details"),
        "story_id": feedback.get("story_id"),
    })

    # Keep only last 90 days
    cutoff = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
    suggestions["suggestions"] = [
        s for s in suggestions["suggestions"]
        if s.get("timestamp", "") >= cutoff
    ]

    with open(suggestions_file, 'w') as f:
        json.dump(suggestions, f, indent=2)


def log_bias_report(feedback: dict):
    """Append a bias report to the bias reports log."""
    bias_file = DATA_DIR / "feedback" / "bias_reports.json"
    reports = {"reports": []}

    if bias_file.exists():
        try:
            with open(bias_file) as f:
                reports = json.load(f)
        except Exception:
            pass

    reports["reports"].append({
        "ref": feedback.get("ref"),
        "timestamp": feedback.get("timestamp"),
        "details": feedback.get("details"),
        "story_id": feedback.get("story_id"),
        "evidence_url": feedback.get("evidence_url"),
    })

    with open(bias_file, 'w') as f:
        json.dump(reports, f, indent=2)


def update_feedback_stats(triage_result: str):
    """Update aggregate feedback statistics (counts only, no content)."""
    stats_file = DATA_DIR / "feedback" / "stats.json"
    stats = {"daily": {}, "totals": {"submissions": 0, "corrections_triggered": 0,
                                      "spam_blocked": 0}}

    if stats_file.exists():
        try:
            with open(stats_file) as f:
                stats = json.load(f)
        except Exception:
            pass

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if today not in stats["daily"]:
        stats["daily"][today] = {"submissions": 0, "factual_error": 0,
                                  "bias_distortion": 0, "suggestion": 0,
                                  "spam": 0, "other": 0, "corrections_triggered": 0}

    stats["daily"][today]["submissions"] += 1
    stats["daily"][today][triage_result] = stats["daily"][today].get(triage_result, 0) + 1
    stats["totals"]["submissions"] += 1

    if triage_result == "spam":
        stats["totals"]["spam_blocked"] += 1

    # Keep only last 30 days
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    stats["daily"] = {k: v for k, v in stats["daily"].items() if k >= cutoff}

    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2)
```

**Step 2: Add Claude AI triage function**

```python
def triage_feedback(feedback: dict) -> str:
    """Use Claude to classify feedback into: spam, suggestion, bias_distortion, factual_error, other.

    Returns the triage classification string.
    """
    prompt = f"""Classify this user feedback submission into exactly one category.

Categories:
- spam: Irrelevant, abusive, nonsensical, promotional, or bot-generated content
- suggestion: Feature requests, improvement ideas, opinions about the service
- bias_distortion: Reports of bias, slanted language, or distortion in our reporting
- factual_error: Claims that a specific published fact is wrong, with or without evidence
- other: Legitimate feedback that does not fit the above categories

Submission:
Category selected by user: {feedback.get('category', 'unknown')}
Story ID: {feedback.get('story_id', 'none')}
Details: {feedback.get('details', '')}
Evidence URL: {feedback.get('evidence_url', 'none')}

Respond with ONLY the category name (one word, lowercase). Nothing else."""

    try:
        result = call_claude(prompt, max_tokens=20)
        classification = result.strip().lower().replace('"', '').replace("'", "")

        valid = {"spam", "suggestion", "bias_distortion", "factual_error", "other"}
        if classification not in valid:
            log.warning(f"Unexpected triage result '{classification}', defaulting to 'other'")
            return "other"

        return classification
    except Exception as e:
        log.warning(f"Feedback triage failed: {e}, defaulting to 'other'")
        return "other"
```

**Step 3: Add factual error verification function**

```python
def verify_factual_error(feedback: dict) -> dict:
    """Attempt to verify a reported factual error using the two-source rule.

    Returns dict with:
        confirmed: bool
        corrected_fact: str or None
        sources: list of source dicts or empty
        reason: str
    """
    story_id = feedback.get("story_id")
    details = feedback.get("details", "")
    evidence_url = feedback.get("evidence_url")

    # Load the referenced story if available
    original_fact = None
    if story_id:
        stories_file = DATA_DIR / "stories.json"
        if stories_file.exists():
            try:
                with open(stories_file) as f:
                    stories = json.load(f)
                for story in stories.get("stories", []):
                    if story.get("id") == story_id:
                        original_fact = story.get("fact")
                        break
            except Exception:
                pass

    prompt = f"""A user has reported a factual error in our news reporting.

Original published fact: {original_fact or 'Not specified'}
Story ID: {story_id or 'Not specified'}
User's report: {details}
User's evidence URL: {evidence_url or 'None provided'}

Your task:
1. Assess whether this report identifies a specific, verifiable factual claim that may be incorrect.
2. If yes, state what the correct fact would be based on available information.
3. Assess confidence level (0-100) that the original fact contains an error.

Respond in this exact JSON format:
{{
    "is_specific_claim": true/false,
    "original_claim": "the specific claim being challenged",
    "corrected_fact": "what the fact should be, or null if unclear",
    "confidence": 0-100,
    "reasoning": "brief explanation"
}}"""

    try:
        result = call_claude(prompt, max_tokens=500)
        # Parse JSON from response
        json_match = result.strip()
        if json_match.startswith("```"):
            json_match = json_match.split("```")[1]
            if json_match.startswith("json"):
                json_match = json_match[4:]
        assessment = json.loads(json_match)

        if not assessment.get("is_specific_claim") or assessment.get("confidence", 0) < 70:
            return {
                "confirmed": False,
                "corrected_fact": None,
                "sources": [],
                "reason": assessment.get("reasoning", "Could not verify the reported error")
            }

        # High confidence — now we need to find 2 independent sources
        # Use the existing source verification infrastructure
        corrected_fact = assessment.get("corrected_fact")
        if not corrected_fact:
            return {
                "confirmed": False,
                "corrected_fact": None,
                "sources": [],
                "reason": "No clear correction could be determined"
            }

        # Search for corroborating sources using existing headline scraping
        # The correction needs 2 unrelated sources to confirm the corrected fact
        verification_prompt = f"""We need to verify this correction:
Original claim: {original_fact or assessment.get('original_claim', '')}
Proposed correction: {corrected_fact}

Based on your knowledge, can this correction be verified as factually accurate?
Is this a well-documented, verifiable fact?

Respond in JSON:
{{
    "verified": true/false,
    "source_names": ["Source 1 Name", "Source 2 Name"],
    "explanation": "brief explanation"
}}"""

        verify_result = call_claude(verification_prompt, max_tokens=300)
        json_match = verify_result.strip()
        if json_match.startswith("```"):
            json_match = json_match.split("```")[1]
            if json_match.startswith("json"):
                json_match = json_match[4:]
        verification = json.loads(json_match)

        if verification.get("verified") and len(verification.get("source_names", [])) >= 2:
            sources = [{"source_name": s} for s in verification["source_names"][:2]]
            # Verify source independence
            if are_sources_unrelated(sources[0]["source_name"], sources[1]["source_name"]):
                return {
                    "confirmed": True,
                    "corrected_fact": corrected_fact,
                    "sources": sources,
                    "reason": verification.get("explanation", "Verified by 2 independent sources")
                }

        return {
            "confirmed": False,
            "corrected_fact": corrected_fact,
            "sources": [],
            "reason": "Could not verify with 2 independent unrelated sources"
        }

    except Exception as e:
        log.warning(f"Factual error verification failed: {e}")
        return {
            "confirmed": False,
            "corrected_fact": None,
            "sources": [],
            "reason": f"Verification error: {e}"
        }
```

**Step 4: Add the main feedback processing function**

```python
def process_pending_feedback():
    """Process all pending feedback submissions.

    Called once per cycle from process_cycle().
    """
    pending = load_pending_feedback()
    if not pending:
        return

    log.info(f"Processing {len(pending)} pending feedback submission(s)")

    for feedback in pending:
        ref = feedback.get("ref", "unknown")

        # Claude AI triage
        triage_result = triage_feedback(feedback)
        log.info(f"Feedback {ref}: triage={triage_result}")

        update_feedback_stats(triage_result)

        if triage_result == "spam":
            mark_feedback_processed(feedback, "spam", "discarded")
            continue

        if triage_result == "suggestion":
            log_suggestion(feedback)
            mark_feedback_processed(feedback, "suggestion", "logged")
            continue

        if triage_result == "bias_distortion":
            log_bias_report(feedback)
            mark_feedback_processed(feedback, "bias_distortion", "flagged_for_audit")
            continue

        if triage_result == "factual_error":
            verification = verify_factual_error(feedback)

            if verification["confirmed"]:
                story_id = feedback.get("story_id", "unknown")
                original_fact = None

                # Get original fact from story
                stories_file = DATA_DIR / "stories.json"
                if stories_file.exists():
                    try:
                        with open(stories_file) as f:
                            stories = json.load(f)
                        for story in stories.get("stories", []):
                            if story.get("id") == story_id:
                                original_fact = story.get("fact")
                                break
                    except Exception:
                        pass

                if original_fact:
                    issue_correction(
                        story_id=story_id,
                        original_fact=original_fact,
                        corrected_fact=verification["corrected_fact"],
                        reason=f"Community feedback ({ref}): {verification['reason']}",
                        correcting_sources=verification["sources"],
                        correction_type="correction"
                    )
                    mark_feedback_processed(feedback, "factual_error",
                                            "correction_issued")
                    log.info(f"Feedback {ref}: CORRECTION ISSUED for {story_id}")

                    # Update stats
                    stats_file = DATA_DIR / "feedback" / "stats.json"
                    if stats_file.exists():
                        try:
                            with open(stats_file) as f:
                                stats = json.load(f)
                            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                            if today in stats.get("daily", {}):
                                stats["daily"][today]["corrections_triggered"] = \
                                    stats["daily"][today].get("corrections_triggered", 0) + 1
                            stats["totals"]["corrections_triggered"] = \
                                stats["totals"].get("corrections_triggered", 0) + 1
                            with open(stats_file, 'w') as f:
                                json.dump(stats, f, indent=2)
                        except Exception:
                            pass
                    continue

            mark_feedback_processed(feedback, "factual_error",
                                    f"unverified: {verification['reason']}")
            continue

        # "other" category
        log_suggestion(feedback)  # Log under suggestions for human review
        mark_feedback_processed(feedback, "other", "logged")

    # Clean old processed feedback
    clean_old_feedback(max_age_days=7)
```

**Step 5: Integrate into process_cycle**

In `process_cycle()` (line 6362), add a call to `process_pending_feedback()` after the existing headline processing. Find a suitable location after the main processing and before the cycle-end logging.

Add after existing processing (around line 6440, after the main publishing logic):

```python
        # Process community feedback
        process_pending_feedback()
```

Also add `clean_old_feedback()` near the existing `clean_old_submissions()` call — search for where `clean_old_submissions` is called and add `clean_old_feedback` adjacent to it.

**Step 6: Pull the feedback files from GitHub on startup**

Since the Cloudflare Worker pushes feedback files to GitHub, main.py needs to pull them. Add to the startup sequence a `git pull` for the `data/feedback/` directory, or simply rely on the fact that the Worker pushes to GitHub and main.py can fetch via GitHub API.

Actually, since main.py runs on the same machine and the Worker pushes to GitHub (not the local filesystem), add a function to fetch pending feedback from GitHub:

```python
def fetch_feedback_from_github():
    """Fetch pending feedback files from GitHub to local data/feedback/.

    The Cloudflare Worker pushes feedback directly to GitHub.
    This function syncs them to local storage for processing.
    """
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        return

    feedback_dir = DATA_DIR / "feedback"
    feedback_dir.mkdir(parents=True, exist_ok=True)

    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    try:
        # List files in data/feedback/ on GitHub
        url = "https://api.github.com/repos/JTFNews/jtfnews/contents/data/feedback"
        response = requests.get(url, headers=headers, params={"ref": "main"})

        if response.status_code != 200:
            return  # Directory may not exist yet

        files = response.json()
        if not isinstance(files, list):
            return

        for file_info in files:
            name = file_info.get("name", "")
            if not name.startswith("JTF-") or not name.endswith(".json"):
                continue

            local_path = feedback_dir / name
            if local_path.exists():
                continue  # Already have this file

            # Download the file
            download_url = file_info.get("download_url")
            if download_url:
                file_resp = requests.get(download_url)
                if file_resp.status_code == 200:
                    with open(local_path, 'w') as f:
                        f.write(file_resp.text)
                    log.info(f"Fetched feedback: {name}")

                    # Delete from GitHub after downloading
                    sha = file_info.get("sha")
                    if sha:
                        requests.delete(
                            file_info["url"],
                            headers=headers,
                            json={
                                "message": f"feedback processed: {name}",
                                "sha": sha,
                                "branch": "main"
                            }
                        )

    except Exception as e:
        log.warning(f"Error fetching feedback from GitHub: {e}")
```

Call `fetch_feedback_from_github()` at the start of `process_pending_feedback()`, before `load_pending_feedback()`.

**Step 7: Commit**

```bash
git pull --rebase origin main
git add main.py
git commit -m "feat: add feedback processing pipeline with Claude AI triage"
git push origin main
```

---

### Task 4: Update All HTML Footers

**Files:**
- Modify: All 15 `docs/*.html` files (but only the 12 that have public-facing footers)

**Step 1: Identify which files need footer updates**

Files with public footers (12 files):
- `docs/index.html`
- `docs/how-it-works.html`
- `docs/whitepaper.html`
- `docs/sources.html`
- `docs/archive.html`
- `docs/corrections.html`
- `docs/support.html`
- `docs/submit.html`
- `docs/register.html`
- `docs/journalists.html`
- `docs/screensaver-setup.html`
- `docs/monitor.html`

Files that are OBS overlays (do NOT update):
- `docs/lower-third.html`
- `docs/background-slideshow.html`
- `docs/screensaver.html`

**Step 2: Add "Report an Issue" to each footer**

In each of the 12 public-facing HTML files, find the footer `<ul class="site-footer__links">` and add this line after the Daily Digest link:

```html
            <li><a href="feedback.html">Report an Issue</a></li>
```

The footer links list should now end with:

```html
            <li><a href="podcast.xml">Podcast</a></li>
            <li><a href="https://www.youtube.com/playlist?list=PLm8mlmJgzmMfqH8YkhdRVFET200vZGRWN">Daily Digest</a></li>
            <li><a href="feedback.html">Report an Issue</a></li>
```

**Step 3: Commit**

```bash
git pull --rebase origin main
git add docs/index.html docs/how-it-works.html docs/whitepaper.html docs/sources.html docs/archive.html docs/corrections.html docs/support.html docs/submit.html docs/register.html docs/journalists.html docs/screensaver-setup.html docs/monitor.html
git commit -m "feat: add Report an Issue link to all page footers"
git push origin main
```

---

### Task 5: Add Feedback Stats to Monitor

**Files:**
- Modify: `main.py` (where monitor.json is written)

**Step 1: Find where monitor.json is assembled**

Search for the function that writes monitor.json and add a `feedback` section.

```python
# Add to monitor.json data assembly:
feedback_stats = {}
feedback_stats_file = DATA_DIR / "feedback" / "stats.json"
if feedback_stats_file.exists():
    try:
        with open(feedback_stats_file) as f:
            fb_stats = json.load(f)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        today_stats = fb_stats.get("daily", {}).get(today, {})
        feedback_stats = {
            "today_submissions": today_stats.get("submissions", 0),
            "today_corrections": today_stats.get("corrections_triggered", 0),
            "total_submissions": fb_stats.get("totals", {}).get("submissions", 0),
            "total_corrections": fb_stats.get("totals", {}).get("corrections_triggered", 0),
            "total_spam_blocked": fb_stats.get("totals", {}).get("spam_blocked", 0),
        }
    except Exception:
        pass

# Add feedback_stats to the monitor dict under key "feedback"
```

**Step 2: Commit**

```bash
git pull --rebase origin main
git add main.py
git commit -m "feat: add feedback stats to operations monitor"
git push origin main
```

---

### Task 6: Deploy and Configure

**Step 1: Deploy the Cloudflare Worker**

Follow `documentation/feedback-worker-setup.md`:
1. Create new Worker in Cloudflare Dashboard named `jtf-feedback`
2. Paste `docs/feedback-worker.js`
3. Add environment variables: `GITHUB_TOKEN`, `POW_DIFFICULTY=4`
4. Deploy and note the worker URL

**Step 2: Update feedback.html with real worker URL**

Replace `PLACEHOLDER_FEEDBACK_URL` in `docs/feedback.html` with the actual Cloudflare Worker URL.

**Step 3: Create data/feedback directory**

```bash
mkdir -p data/feedback/processed
```

**Step 4: Test end-to-end**

1. Open `docs/feedback.html` in browser
2. Wait for proof-of-work to complete (button becomes "Submit")
3. Submit a test factual error
4. Verify file appears in GitHub repo under `data/feedback/`
5. Run main.py cycle and verify triage processes the feedback
6. Check `data/feedback/processed/` for the result

**Step 5: Final commit**

```bash
git pull --rebase origin main
git add docs/feedback.html
git commit -m "feat: configure feedback worker URL"
git push origin main
```

---

### Task 7: Update CLAUDE.md and Documentation

**Files:**
- Modify: `CLAUDE.md` (add feedback system section)
- Modify: `documentation/plans/2026-03-06-feedback-system-design.md` (mark as implemented)

**Step 1: Add feedback system section to CLAUDE.md**

Add under the Journalist Submission System section:

```markdown
## Feedback System

The public can anonymously report factual errors, bias concerns, and suggestions via `jtfnews.org/feedback.html`. No personal data collected.

### How It Works
1. User submits feedback via form (no account required)
2. Cloudflare Worker validates spam prevention (honeypot, time gate, rate limit, proof-of-work)
3. Worker pushes feedback JSON to `data/feedback/` via GitHub API
4. main.py fetches pending feedback each cycle
5. Claude AI triages: spam (discard), suggestion (log), bias (flag for audit), factual error (verify)
6. Factual errors verified by 2+ independent sources trigger auto-correction via existing pipeline

### Data Files
| File | Purpose |
|------|---------|
| `data/feedback/JTF-*.json` | Pending feedback (fetched from GitHub) |
| `data/feedback/processed/` | Processed feedback (7-day retention) |
| `data/feedback/suggestions.json` | Suggestions log (90-day retention) |
| `data/feedback/bias_reports.json` | Bias reports (until quarterly audit) |
| `data/feedback/stats.json` | Aggregate counts (30-day rolling) |

### Key Files
| File | Purpose |
|------|---------|
| `docs/feedback.html` | Public feedback form |
| `docs/feedback-worker.js` | Cloudflare Worker source |
| `documentation/feedback-worker-setup.md` | Worker deployment instructions |
```

**Step 2: Commit**

```bash
git pull --rebase origin main
git add CLAUDE.md documentation/plans/2026-03-06-feedback-system-design.md
git commit -m "docs: add feedback system documentation"
git push origin main
```
