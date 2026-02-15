# Funding-Based Regional Prioritization Design

## Date: 2026-02-14

---

## Overview

This document defines how JTF News uses community funding and interest signals to prioritize regional stream deployment. The system maintains editorial integrity while enabling sustainable expansion.

**Core Principle:** Coverage remains unbiased. Funding affects WHEN a regional stream launches, not WHAT gets covered. Interest determines ORDER, not WHETHER.

**Model:** Community Milestone Model — transparent tier-based funding with democratic interest signaling.

---

## Problem Statement

JTF News plans to expand from a single global stream to regional coverage (country, state, county, city levels). This expansion requires funding for:
- Additional OBS instances and infrastructure
- Increased API costs (more sources, more processing)
- Operational monitoring overhead

The challenge: How do we prioritize which regions launch first without compromising our editorial neutrality or creating a "pay-to-play" perception?

---

## Design Decisions

### Decision 1: Separate Donation from Interest

**Approach:** Donations go to general operations via GitHub Sponsors. Regional interest is captured separately via an optional form.

**Rationale:**
- Donation amount doesn't buy more influence
- Interest signals are democratic (available to non-donors)
- Legally clean (no earmarking claims)
- Simpler accounting

### Decision 2: Tier-Based Capacity Model

**Approach:** Total funding determines what depth of geographic coverage is possible. Interest determines deployment order within each tier.

**Rationale:**
- Fair: No region is "bought" — funding unlocks capacity for ALL regions at a tier
- Transparent: Public thresholds, public progress
- Sustainable: 3-month sustained funding requirement prevents boom/bust

### Decision 3: Percentage-Based Interest Display

**Approach:** Show interest as percentages, not raw counts. Update daily, not real-time.

**Rationale:**
- Normalizes across population sizes (Wyoming vs California)
- Reduces gaming incentive (can't see immediate impact)
- Easier to understand at a glance

### Decision 4: Identity-Verified Interest Signals

**Approach:** Require GitHub OAuth or email verification to indicate interest.

**Rationale:**
- One vote per person (prevents ballot stuffing)
- Aligns with open-source community norms
- Low friction for target audience

---

## Funding Tier Structure

| Tier | Granularity | Monthly Threshold | What Unlocks | Capacity |
|------|-------------|-------------------|--------------|----------|
| 1 | International | $0 (baseline) | Global stream (exists now) | 1 |
| 2 | Country | $500/month sustained | Country-level streams | Up to 20 |
| 3 | State/Province | $2,000/month sustained | State-level streams | Up to 50 |
| 4 | County/District | $5,000/month sustained | County-level streams | Up to 200 |
| 5 | Metro/City | $10,000/month sustained | City-level streams | Up to 500 |

**Sustained:** 3 consecutive months at or above threshold.

**Capacity limits** are adjustable as operational capacity grows.

---

## Interest Capture Mechanism

### Location
`jtfnews.com/interest`

### User Flow
1. User visits interest page
2. Authenticates via GitHub OAuth OR verifies email address
3. Selects regions of interest (multi-select checkbox tree)
4. Options organized hierarchically: Country → State → County → City
5. Submits preferences (can update anytime)

### Data Model

```json
{
  "user_id": "github:larryseyer",
  "verified": true,
  "is_donor": true,
  "interests": [
    {"level": "country", "code": "US"},
    {"level": "state", "code": "US-CA"},
    {"level": "county", "code": "US-CA-037"}
  ],
  "updated_at": "2026-02-14T10:30:00Z"
}
```

### Aggregation
- Interest percentages calculated daily at midnight UTC
- Stored in `data/interest.json`
- Synced to `gh-pages-dist/interest.json` for public dashboard

---

## Public Dashboard

### Location
`jtfnews.com/progress`

### Layout

```
┌─────────────────────────────────────────────────────────────┐
│  JTF NEWS EXPANSION PROGRESS                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  CURRENT TIER: 1 (International)                            │
│  ════════════════════════════════════════════════════════   │
│                                                             │
│  TIER 2 (Country-level): 73% funded                         │
│  ████████████████████████░░░░░░░  $365 / $500 monthly       │
│                                                             │
│  TIER 3 (State/Province): Locked                            │
│  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  Unlocks at $2,000/mo       │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  COMMUNITY INTEREST                                         │
│                                                             │
│  Countries:        States/Provinces:    Counties:           │
│  US ████████ 45%   California ███ 12%   (Tier 4 locked)     │
│  UK ███░░░░░ 18%   Texas ██░░░░░░ 8%                        │
│  CA ██░░░░░░ 10%   New York █░░░░ 5%                        │
│  AU █░░░░░░░  6%   Florida █░░░░░ 4%                        │
│  ...more            ...more                                 │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  DEPLOYMENT QUEUE                                           │
│                                                             │
│  ✓ Global (Live)                                            │
│  ◐ US (Pending Tier 2 unlock)                               │
│  ◐ UK (Pending Tier 2 unlock)                               │
│  ○ California (Pending Tier 3 unlock)                       │
│                                                             │
│  Interest determines order within each tier.                │
│  All regions at unlocked tiers eventually receive coverage. │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Key Elements
- Funding progress bars per tier
- Interest percentages (updated daily)
- Deployment queue with status indicators
- Clear messaging about prioritization logic

---

## Deployment Prioritization Logic

### Algorithm

```
1. Check tier eligibility
   └─ Is this tier unlocked? (funding threshold met for 3 months)

2. Sort regions by interest percentage
   └─ Highest interest % at top of queue

3. Check operational capacity
   └─ Can we support another stream? (OBS instances, monitoring)

4. Deploy next in queue
   └─ Launch stream, move to "Live" status

5. Repeat until tier capacity reached or no more interested regions
```

### Tiebreaker Rules
- Equal interest % → Earlier timestamp wins (first to request)
- No interest indicated → Alphabetical order (deterministic fallback)

### Example

| Region | Interest % | First Interest | Queue Position |
|--------|------------|----------------|----------------|
| US | 45% | 2026-01-15 | 1st |
| UK | 18% | 2026-01-20 | 2nd |
| Canada | 10% | 2026-02-01 | 3rd |
| Australia | 10% | 2026-01-18 | 4th (tied %, but earlier timestamp) |

---

## Legal & Communication Framework

### Core Legal Position

> "Donations support JTF News operations. Regional interest signals inform deployment priorities during our growth phase. All regions at unlocked tiers receive coverage."

### Messaging Matrix

| Context | What We Say | What We Avoid |
|---------|-------------|---------------|
| Sponsor page | "Support fact-based news for your community" | "Fund your region's stream" |
| Interest form | "Tell us which regions matter to you" | "Vote for your region" |
| Dashboard | "Interest helps us prioritize deployment order" | "Top donors choose regions" |
| Launch announcement | "Launching US stream based on community interest" | "US donors made this happen" |

### Required Disclaimer

Display on interest form and dashboard:

```
JTF News is a general-purpose news service. All donations support
operations. Regional interest signals help prioritize deployment
order but do not guarantee specific outcomes. Coverage standards
remain identical across all regions.
```

### Why This Protects Us
1. No promise of specific outcome tied to donation
2. Interest is separate from payment
3. Equal coverage explicitly stated
4. Public methodology = no hidden favoritism claims

---

## Integration with Existing Systems

| Existing System | Integration Point |
|-----------------|-------------------|
| GitHub Sponsors | Sync donor status via GitHub API |
| Regional filtering | Uses same location taxonomy |
| `stories.json` location tags | Same geographic schema |
| `gh-pages-dist/` website | Add `/progress` and `/interest` pages |
| `config.json` | Extend with tier status and capacity |

### New Files

| File | Purpose |
|------|---------|
| `gh-pages-dist/progress.html` | Public funding/interest dashboard |
| `gh-pages-dist/interest.html` | Interest indication form |
| `gh-pages-dist/js/progress.js` | Dashboard logic |
| `gh-pages-dist/js/interest.js` | Interest form logic |
| `data/interest.json` | Aggregated interest data |
| `data/funding.json` | Funding tier status |
| `docs/donation_tiers.md` | Public-facing tier documentation |

### No Changes Required
- `main.py` — This is a web/funding layer, not a content layer
- News coverage logic remains completely separate

---

## Transition to Equal Treatment

The prioritization system is temporary:

1. **During Growth:** Funding determines tier unlock. Interest determines deployment order.

2. **At Coverage-Complete:** Once all regions at all unlocked tiers have streams, prioritization ends. All regions receive equal maintenance.

3. **Future Tier Unlocks:** If funding grows to unlock a new tier, the cycle repeats for that tier only.

---

## Anti-Gaming Measures

1. **Identity Verification:** One interest indication per GitHub account or verified email
2. **Percentage Display:** Normalized view prevents raw-count manipulation
3. **Daily Updates:** No real-time feedback prevents gaming loops
4. **Audit Trail:** All interest changes logged with timestamps

---

## Success Criteria

1. Dashboard accurately reflects funding and interest
2. Deployment order matches documented algorithm
3. No donor complaints about earmarking expectations
4. No public perception of "pay-to-play"
5. Regional streams launch when tiers unlock

---

## File Changes Summary

| File | Changes |
|------|---------|
| `gh-pages-dist/progress.html` | New: funding/interest dashboard |
| `gh-pages-dist/interest.html` | New: interest indication form |
| `gh-pages-dist/js/progress.js` | New: dashboard rendering logic |
| `gh-pages-dist/js/interest.js` | New: form submission + GitHub OAuth |
| `data/interest.json` | New: aggregated interest storage |
| `data/funding.json` | New: tier status tracking |
| `docs/donation_tiers.md` | New: public tier documentation |
| `config.json` | Add: tier thresholds and capacity limits |

---

## Appendix: Geographic Code Format

Using ISO 3166 standard with extensions:

| Level | Format | Example |
|-------|--------|---------|
| Country | ISO 3166-1 alpha-2 | `US`, `UK`, `CA` |
| State/Province | ISO 3166-2 | `US-CA`, `US-TX`, `CA-ON` |
| County/District | ISO 3166-2 + FIPS | `US-CA-037` (Los Angeles County) |
| City/Metro | Custom: state + city slug | `US-CA-los-angeles` |

This aligns with the regional filtering design's location taxonomy.
