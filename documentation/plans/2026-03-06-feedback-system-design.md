# Feedback System Design

**Date:** 2026-03-06
**Status:** Approved

---

## Purpose

Allow the public to report factual errors, bias concerns, and suggestions. Fully automated via Claude AI. Zero personal data collected. Aligns with the whitepaper's stated requirement for "community reporting of detected bias or distortion."

---

## Principles

- No email. No name. No IP storage. No personal data of any kind.
- Acknowledge receipt on-screen immediately. No follow-up channel.
- Factual corrections are fully automated via the two-source rule.
- Suggestions are logged for human review, never auto-acted on.
- Raw submissions retained for 7 days maximum (whitepaper compliance).
- Feedback is not engagement. It is operational input that serves accuracy.

---

## User Experience

### Entry Point

A "Report an Issue" link in the footer of every page on jtfnews.org, linking to `feedback.html`.

### Form Fields

| Field | Type | Required |
|-------|------|----------|
| Category | Dropdown: Factual Error, Bias/Distortion, Suggestion, Other | Yes |
| Story | Dropdown of recent stories from stories.json, plus "General / Not about a specific story" | No |
| Details | Free-text textarea | Yes |
| Evidence URL | Text input for a supporting source link | No |

No name. No email. No account. No login.

### On Submission

The page displays:

> Feedback received. Reference #JTF-20260306-0042.
> Corrections, if any, will appear on the Corrections page.
> Thank you.

Form resets. Done.

### Reference Numbers

Format: `JTF-YYYYMMDD-NNNN` (sequential per day). Public, anonymous. No personal data attached.

---

## Spam Prevention

Four layers. Zero stored data.

| Layer | Implementation | Data Stored |
|-------|---------------|-------------|
| Honeypot | Hidden field `<input name="website" style="display:none">`. If filled, discard silently. | Nothing |
| Time gate | Page records load timestamp in JS. Reject if submitted < 5 seconds after load. | Nothing |
| Rate limit | Server-side in-memory counter per IP. Max 5 submissions/hour. Never written to disk. | Nothing |
| Proof-of-work | Browser computes SHA-256 hash with nonce producing N leading zeros (~1-2s for humans, expensive for bots). | Nothing |

Fifth layer: Claude AI triage classifies and discards spam that passes through the form.

---

## AI Processing Pipeline

```
Submission arrives
    |
    v
Spam filters (honeypot, time gate, rate limit, proof-of-work)
    |
    v
Claude AI Triage
    |-- SPAM/ABUSE ........... discard silently, increment counter
    |-- SUGGESTION ........... log to suggestions.json, done
    |-- BIAS/DISTORTION ...... log to bias_reports.json, flag for audit
    |-- FACTUAL ERROR ........ enter verification pipeline
                                   |
                                   v
                          Claude searches for 2+ independent sources
                                   |
                          +--------+--------+
                          |                 |
                   Confirmed error    Cannot confirm
                          |                 |
                   Auto-issue          Log as unverified
                   correction          No action
```

### Triage Prompt

Claude receives the submission text and classifies it into one of the four categories. For factual error reports, Claude also:

1. Identifies the specific claim being challenged
2. Looks up the referenced story in stories.json
3. Searches for 2+ independent sources (different owners) that confirm or deny the claim
4. If confirmed as error: triggers the existing corrections pipeline
5. If unconfirmed: logs as unverified, takes no action

The same ownership-independence rules apply to verification sources as to original reporting.

---

## Data Storage

| File | Contents | Retention |
|------|----------|-----------|
| `data/feedback/pending.json` | Incoming submissions awaiting AI triage | Processed within minutes, then moved |
| `data/feedback/suggestions.json` | Logged suggestions for periodic human review | 90 days, then archived |
| `data/feedback/bias_reports.json` | Bias/distortion reports flagged for audit | Until next quarterly audit |
| `data/feedback/processed/` | Processed submissions (JSON per submission) | 7 days (whitepaper compliance) |
| `data/feedback/stats.json` | Aggregate counts only: submissions today, corrections triggered, spam blocked | Rolling 30 days |

No personal data in any file. Each submission record contains only:

```json
{
  "ref": "JTF-20260306-0042",
  "timestamp": "2026-03-06T14:23:00Z",
  "category": "factual_error",
  "story_id": "abc123",
  "details": "The reported figure was 500 but official records show 347.",
  "evidence_url": "https://example.com/official-report",
  "status": "confirmed_correction",
  "triage_result": "factual_error",
  "processed_at": "2026-03-06T14:25:00Z"
}
```

---

## Integration Points

| System | Integration |
|--------|-------------|
| Corrections pipeline | Confirmed factual errors feed directly into existing correction issuance in main.py |
| Quarterly audit | Bias reports surface during existing quarterly ownership audit |
| Corrections page | Already public at corrections.html -- no change needed |
| Operations dashboard | Feedback volume can optionally appear on monitor.html |
| GitHub API | Stats and processed corrections pushed alongside existing runtime files |

---

## New/Modified Files

### New Files

| File | Purpose |
|------|---------|
| `docs/feedback.html` | Public feedback form with spam prevention |
| `data/feedback/` | Runtime directory for feedback data (not committed) |

### Modified Files

| File | Change |
|------|--------|
| All `docs/*.html` footers | Add "Report an Issue" link to feedback.html |
| `main.py` | Add feedback processing: API endpoint, spam checks, Claude triage, verification pipeline, data retention cleanup |

---

## What This System Does NOT Do

- Collect email, name, IP address, or any personal data
- Reply to or follow up with submitters
- Auto-act on suggestions (log only)
- Store raw submissions longer than 7 days
- Create user accounts or profiles
- Engage in dialogue with submitters
- Store any data that could identify a person

---

## Whitepaper Alignment

| Whitepaper Requirement | How This System Complies |
|------------------------|--------------------------|
| "Community reporting of detected bias or distortion" | Direct implementation of this requirement |
| "No logs" (user tracking) | Zero personal data collected or stored |
| "We do not store raw data longer than 7 days" | 7-day retention on processed submissions |
| "We do not bury mistakes. We name them." | Corrections issued publicly with same prominence |
| "No ads. No tracking." | No analytics, no fingerprinting, no cookies |
| "Nothing hidden. Nothing sold." | All feedback stats and corrections are public |
| "Corrections are given the same prominence as the original item" | Uses existing corrections pipeline which already handles this |
