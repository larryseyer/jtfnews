# Journalist Submission System — Design Document

## Version 1.0 | March 2, 2026

---

## Overview

This document defines the design for allowing independent journalists to submit original reporting to JTF News. The system extends the existing automated pipeline with a human input channel while preserving every principle in the whitepaper.

**Governing principle:** A journalist is a source. Sources follow the methodology. The methodology does not bend.

---

## 1. What a Journalist Submits

Journalists submit **original reporting** — firsthand factual accounts of events they witnessed or investigated. This is new information not yet published elsewhere.

A journalist does NOT submit links to existing articles. That is source curation, which is a separate concern. This system handles original human-generated facts entering the pipeline.

---

## 2. Verification Standard

**The two-source rule applies identically.**

A journalist's submission enters the queue like any scraped headline. It is ONE source. The system requires an independent second source (either from the automated scraper or from another journalist) to corroborate before publication. If no second source appears within the queue timeout window (24 hours), the story is dropped.

No special treatment. No expedited publication. The whitepaper says: *"Two unrelated sources minimum."* This applies without exception.

---

## 3. Financial Independence Rule

**"No common majority shareholder is the minimum threshold."**

This existing rule applies identically when one source is a journalist:

- The journalist's financial disclosures identify who provides their majority funding
- A corroborating institutional source's ownership is already known from `config.json`
- The `are_sources_unrelated()` function determines independence

**Example — Valid pair:**
- Jane Doe (self-funded, Independent) submits a story
- BBC (UK Public Broadcaster) corroborates
- No common majority funder → Valid verification

**Example — Invalid pair:**
- Jane Doe (funded 60% by Foundation X) submits a story
- News outlet funded 55% by Foundation X corroborates
- Common majority funder → Same source. Verification rejected.

---

## 4. Identity and Transparency

### 4.1 Real Identity, Fully Disclosed

Journalists must register with:
- **Full legal name** — displayed publicly as the source name
- **Location** — city, state/province, country
- **Professional affiliation** — employer or "Independent"
- **Financial disclosures** — all entities providing majority funding, with percentages

This mirrors the institutional source ownership disclosure the whitepaper requires for every story. The audience sees who funds the information they receive, whether the source is BBC or Jane Doe.

### 4.2 Display Format

**Lower-third (compact):**
```
Jane Doe 8.7|8.2 · BBC 9.4|9.2
```
Format: `Name Accuracy|Bias` — identical to institutional sources.

**Website (full disclosure):**
```
Jane Doe, Independent – Portland, OR
├─ Accuracy: 8.7
├─ Bias: 8.2
├─ Speed: 7.5
├─ Consensus: 8.9
└─ Funding: Self-funded (100%)
```

**RSS feed:**
```xml
<source name="Jane Doe, Independent" accuracy="8.7" bias="8.2" speed="7.5" consensus="8.9">
  <owner name="Self-funded" percent="100"/>
</source>
```

---

## 5. AI Processing

**Identical to institutional sources.**

The journalist's submission goes through the exact same Claude prompt (`CLAUDE_SYSTEM_PROMPT`) as every scraped headline. Strip adjectives, remove speculation, extract what/where/when/who/how many. No special prompt. No different treatment.

Journalists are informed of this **at registration time**:

> "Your submission will be processed identically to any institutional source. The AI will strip all adjectives, editorial language, and speculation. Only verifiable facts (what, where, when, who, how many) will remain. Your original text will not appear as-is. If the facts cannot be corroborated by an independent source within 24 hours, the story will not be published."

---

## 6. Scoring System

### 6.1 Four Identical Metrics

Journalists receive the same four scores as institutional sources:

| Score | Calculation for Journalists | Meaning |
|-------|---------------------------|---------|
| **Accuracy** | `(verified_submissions / total_submissions) × 10` | How often their submissions get corroborated |
| **Bias** | `10 - (avg_text_removed_percentage × 10)` | How neutral their writing is (high = good) |
| **Speed** | `10 - (avg_minutes_behind_first / 60)` capped at 0 | How early they report events |
| **Consensus** | `(matching_facts / total_facts) × 10` | How often their facts align with other sources |

### 6.2 Cold Start

New journalists start with no scores (displayed with asterisk `*` per existing convention). Scores emerge from data:
- First submission: `*` (no data)
- After 10 verified submissions: scores lose the asterisk
- Scores are evidence-based, never editorial

### 6.3 Top 10 Leaderboard

A public leaderboard page at `jtfnews.org/journalists` displays the top 10 journalists ranked by a composite of their four scores (weighted by the same priority as institutional sources: Accuracy > Bias > Speed > Consensus).

This is the journalist's reward: public, algorithmically calculated recognition for factual integrity. No financial compensation. No editorial endorsement. Just numbers.

---

## 7. Registration and Vetting

### 7.1 Open Registration

Anyone can register. No credential requirements. No press badges. No gatekeeping.

The two-source verification rule IS the gatekeeper. Nothing publishes without independent corroboration. The system learns who is reliable through performance data, just as it does for institutional sources.

This aligns with: *"The methodology belongs to no one. It serves everyone."*

### 7.2 Registration Flow

1. Journalist visits `jtfnews.org/submit`
2. Authenticates via GitHub OAuth (provides traceable identity)
3. Completes registration form:
   - Full legal name
   - Location (city, state/province, country)
   - Professional affiliation (or "Independent")
   - Financial disclosures: entities providing majority funding, with percentages
   - Acknowledgment checkbox (methodology disclosure — see Section 5)
4. Registration reviewed and stored in `data/journalists.json`
5. Journalist can now submit via the form

### 7.3 GitHub OAuth Rationale

GitHub OAuth provides:
- Traceable identity (GitHub accounts are real, linked to email)
- No new auth infrastructure to build
- Consistent with JTF's GitHub-centric architecture
- Free for users
- Auditable (GitHub usernames are persistent)

### 7.4 Data Structure

```json
{
  "journalists": {
    "janedoe": {
      "github_username": "janedoe",
      "name": "Jane Doe",
      "location": "Portland, OR, USA",
      "affiliation": "Independent",
      "owner": "Self-funded",
      "owner_display": "Self-funded (100%)",
      "financial_disclosures": [
        {
          "entity": "Self-funded",
          "relationship": "primary income",
          "percentage": 100
        }
      ],
      "registered": "2026-03-02T14:30:00Z",
      "last_disclosure_update": "2026-03-02T14:30:00Z",
      "disclosure_quarter": "Q1 2026",
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
  }
}
```

---

## 8. Submission Form and Workflow

### 8.1 Submission Page

A web form at `jtfnews.org/submit` (static HTML page in `docs/`):

**Required fields:**
- **Event description** — What happened (the journalist's factual account)
- **Location** — Where the event occurred
- **Date/time** — When the event occurred
- **People involved** — Who was formally involved (with official titles)
- **Quantifiable outcomes** — Numbers, if available (casualties, dollar amounts, vote counts)

**Optional fields:**
- **Supporting evidence** — URLs, document references, public records (for context, not verification)

### 8.2 Technical Flow

1. Authenticated journalist fills the form on `jtfnews.org/submit`
2. Client-side JavaScript submits via GitHub API → creates a JSON file in the submissions directory of the repository
3. `main.py` reads pending submissions during each processing cycle
4. Each submission is processed through the same `extract_fact()` function as scraped headlines
5. Extracted fact enters the queue with the journalist as the source
6. Normal verification proceeds: wait for corroboration from independent source

### 8.3 Submission Data Structure

```json
{
  "id": "sub-2026-03-02-janedoe-a1b2c3",
  "journalist_id": "janedoe",
  "submitted": "2026-03-02T15:00:00Z",
  "status": "pending",
  "event_description": "Portland City Council voted 7-2 to approve rezoning of the Pearl District for mixed-use development.",
  "location": "Portland, OR, USA",
  "event_date": "2026-03-02",
  "people_involved": "Mayor Ted Wheeler, Councilor Carmen Rubio",
  "quantifiable_outcomes": "7-2 vote, affects 12 city blocks",
  "supporting_evidence": ["https://portland.gov/council/agenda/2026-03-02"],
  "processed_fact": null,
  "confidence": null
}
```

### 8.4 Integration with process_cycle()

Within `process_cycle()`, after scraping headlines:

```python
# Existing: scrape headlines
headlines = scrape_all_sources()

# NEW: load journalist submissions
submissions = load_pending_submissions()
for sub in submissions:
    # Process through same Claude pipeline
    result = extract_fact(sub["event_description"])
    if result["fact"] != "SKIP" and result["confidence"] >= min_confidence:
        # Add to queue as a journalist-sourced headline
        queue_item = {
            "fact": result["fact"],
            "source_id": f"journalist:{sub['journalist_id']}",
            "source_name": get_journalist_display_name(sub["journalist_id"]),
            "confidence": result["confidence"],
            "timestamp": sub["submitted"],
            "type": "journalist_submission"
        }
        queue.append(queue_item)
        mark_submission_processed(sub["id"])
```

The journalist's submission becomes a queue item indistinguishable from a scraped headline. The only difference is `source_id` starts with `journalist:` to route to journalist data instead of `config.json` source data.

---

## 9. Source Independence Check

### 9.1 Extended are_sources_unrelated()

The existing function checks `config.json` sources. It must be extended to handle journalist sources:

```python
def are_sources_unrelated(source1_id: str, source2_id: str) -> bool:
    """Check if two sources are unrelated (different owners).

    Handles both institutional sources (from config.json)
    and journalists (from journalists.json).
    """
    s1 = get_source_info(source1_id)  # Returns from config or journalists
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

A journalist's `owner` is their majority funder. Their `institutional_holders` are derived from their financial disclosures. The same independence rules apply.

### 9.2 Journalist-to-Journalist Verification

Two different journalists CAN verify each other, provided:
- They have different `owner` values (different majority funders)
- No common majority shareholder
- Standard independence rules pass

This is identical to how two institutional sources verify each other.

---

## 10. Abuse Prevention

### 10.1 Rate Limiting

Each journalist has a `submission_quota` that starts low and grows with performance:

| Accuracy Score | Daily Submission Quota |
|---------------|----------------------|
| No data (new) | 3 per day |
| < 5.0 | 2 per day |
| 5.0 - 7.0 | 5 per day |
| 7.0 - 9.0 | 10 per day |
| > 9.0 | 20 per day |

### 10.2 Web Form Protections

- CAPTCHA on submission form (prevents automated spam)
- GitHub OAuth required (prevents anonymous abuse)
- Rate limiting enforced server-side (main.py checks quota before processing)

### 10.3 Natural Gatekeeper

The two-source rule is the ultimate abuse prevention. A bad actor can submit fabricated stories all day — none will publish without independent corroboration. Their accuracy score will drop to zero as submissions expire unverified. The system self-corrects.

---

## 11. Quarterly Financial Disclosure Audit

### 11.1 Same Cadence as Institutions

Journalist financial disclosures are audited on the same quarterly schedule as institutional source ownership:

- Q1 Review: January
- Q2 Review: April
- Q3 Review: July
- Q4 Review: October

### 11.2 Process

1. At the start of each quarter, `main.py` checks if journalists have updated their disclosures
2. Journalists whose disclosures are stale (last update > 1 quarter ago) are suspended
3. Suspended journalists cannot submit until they update their disclosures
4. Updates are logged to the same `data/ownership_audit.json` used for institutional sources

### 11.3 Suspension

A journalist with stale disclosures:
- Status changes from `active` to `suspended_disclosure`
- Existing submissions in the queue remain (they've already been accepted)
- No new submissions accepted until disclosures are updated
- Suspension is visible on their public profile

---

## 12. Corrections

**Identical to institutional corrections.**

When a journalist-sourced story is later proven false:
- A correction is issued within the next update cycle
- The original item is marked as corrected in the archive, never silently deleted
- The corrections log names the journalist and the corroborating source
- The journalist's accuracy score drops (same formula as institutional sources)
- Corrections are given the same prominence as the original item

*"We do not bury mistakes. We name them."* — This applies to journalists the same as it applies to BBC.

---

## 13. Top 10 Leaderboard Page

### 13.1 Page Design

A new page at `jtfnews.org/journalists` displays:

**Leaderboard (Top 10 by composite score):**

```
TOP 10 JOURNALISTS — By the Numbers

 # | Name                        | Accuracy | Bias | Speed | Consensus | Verified
---|-----------------------------|---------:|-----:|------:|----------:|---------:
 1 | Jane Doe, Independent – Portland    |     9.2 |  9.0 |   8.5 |      9.1 |       47
 2 | John Smith, Independent – Austin    |     8.8 |  8.7 |   9.0 |      8.6 |       38
 3 | Maria Garcia, Freelance – Mexico City |   8.5 |  9.2 |   7.8 |      8.8 |       31
...
```

Numbers only. No labels. No "best journalist" language. Just data.

### 13.2 Composite Score

Weighted by the same priority as institutional source scores:

```
composite = (accuracy × 4) + (bias × 3) + (speed × 2) + (consensus × 1)
            ─────────────────────────────────────────────────────────────
                                      10
```

### 13.3 Update Frequency

The leaderboard is recalculated and pushed to GitHub Pages during each daily archive cycle (midnight GMT).

---

## 14. Data Storage

All journalist data lives in the existing `data/` directory (gitignored, not committed):

| File | Purpose |
|------|---------|
| `data/journalists.json` | Journalist profiles, disclosures, scores, stats |
| `data/submissions/` | Directory of pending submission JSON files |
| `data/submissions/processed/` | Processed submissions (moved here after processing) |
| `data/ratings_audit.jsonl` | Extended to include journalist rating events |
| `data/learned_ratings.json` | Extended to include journalist ratings |

Public data pushed to GitHub Pages:

| File | Purpose |
|------|---------|
| `docs/journalists.json` | Public journalist profiles and scores (no private data) |
| `docs/journalists.html` | Top 10 leaderboard page |

### 14.1 Data Retention

Per the whitepaper: *"We do not store raw data longer than seven days."*

- Raw submission text is retained for 7 days maximum
- After 7 days, only the extracted fact and metadata remain
- Journalist profiles and scores are permanent (they are summary data, not raw data)

---

## 15. Website Changes

### 15.1 New Pages

| Page | Purpose |
|------|---------|
| `docs/submit.html` | Submission form (authenticated journalists) |
| `docs/register.html` | Journalist registration form |
| `docs/journalists.html` | Top 10 leaderboard and journalist directory |

### 15.2 Updated Pages

| Page | Change |
|------|--------|
| `docs/index.html` | Add link to journalist submission system |
| `docs/how-it-works.html` | Add section explaining journalist submissions |

### 15.3 Design Aesthetic

All new pages follow the existing JTF design language:
- Dark glassmorphism aesthetic
- Inter font family
- Calm, professional, no urgency
- No engagement features (no comments, no likes, no social share buttons)
- Numbers presented plainly

---

## 16. main.py Changes

### 16.1 New Functions

| Function | Purpose |
|----------|---------|
| `load_pending_submissions()` | Read unprocessed submissions from `data/submissions/` |
| `mark_submission_processed()` | Move processed submission to `processed/` |
| `get_journalist_info()` | Load journalist profile from `data/journalists.json` |
| `get_source_info()` | Unified source lookup (institutional OR journalist) |
| `get_journalist_display_name()` | Format: "Jane Doe, Independent – Portland" |
| `check_journalist_quota()` | Verify journalist hasn't exceeded daily limit |
| `update_journalist_scores()` | Recalculate journalist's four scores after verification |
| `check_disclosure_freshness()` | Suspend journalists with stale quarterly disclosures |
| `generate_leaderboard()` | Calculate top 10, push to GitHub Pages |
| `register_journalist()` | Process new journalist registration |

### 16.2 Modified Functions

| Function | Change |
|----------|--------|
| `process_cycle()` | Add step: load and process journalist submissions alongside scraped headlines |
| `are_sources_unrelated()` | Extend to handle `journalist:` source IDs |
| `get_learned_rating()` | Extend to handle `journalist:` source IDs |
| `get_reliability_score()` | Works without change (calls `get_learned_rating()`) |
| `record_verification_success()` | Extend to update journalist stats |
| `record_verification_failure()` | Extend to update journalist stats |
| `clean_expired_queue()` | Record failures for journalist sources too |
| `push_to_github()` | Push journalist leaderboard data alongside existing files |
| `archive_daily()` | Include journalist submission metadata in daily archives |

### 16.3 Quarterly Audit Extension

The existing quarterly ownership audit system is extended to include journalist disclosures. The same `--audit` flag triggers both institutional and journalist reviews.

---

## 17. Scope and Constraints

### 17.1 Global Stream Only

Journalist submissions feed into the global stream with the same newsworthiness thresholds (500+ people, $1M+, etc.). Community channels are a future feature.

### 17.2 No Compensation

Journalists submit voluntarily. No financial compensation. The Top 10 leaderboard and publicly verifiable accuracy scores are the reward.

### 17.3 No Engagement

Per the whitepaper: *"We do not reply. No engagement. No likes."*

There is no messaging system between JTF and journalists. No feedback on submissions. No "your story was published" notification. The journalist checks the stream or the website to see if their fact was corroborated and published. The system is a billboard, not a conversation.

### 17.4 CC-BY-SA

All journalist submissions fall under the same CC-BY-SA license as all JTF output. By submitting, journalists agree that their extracted facts (not raw text) are licensed CC-BY-SA. This is disclosed at registration.

---

## 18. Security Considerations

- **No raw submission storage beyond 7 days** — per whitepaper data retention policy
- **GitHub OAuth tokens** — stored only in the client browser session, never on the server
- **Financial disclosures** — stored in `data/` (gitignored), public scores pushed to `docs/`
- **Submission rate limiting** — prevents queue flooding and API cost abuse
- **No PII in public files** — only name, location, affiliation, and scores appear publicly (journalist consented to this at registration)

---

## 19. What This System Does NOT Do

- Does not accept source curation (links to existing articles) — only original reporting
- Does not provide feedback on submissions — the stream is the output
- Does not create a journalist community or forum — no engagement
- Does not pay journalists — voluntary contributions
- Does not expedite publication — same queue timeout, same verification rules
- Does not lower newsworthiness thresholds — global stream thresholds apply
- Does not give journalist submissions any priority over automated sources — equal treatment
