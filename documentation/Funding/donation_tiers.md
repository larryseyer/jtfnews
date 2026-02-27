# JTF News Donation Tiers

## Overview

This document defines the funding tier system for JTF News regional expansion. Total funding determines what depth of geographic coverage is possible globally. Donor interest determines deployment order within each tier.

**Core Principle:** Coverage remains unbiased. Funding affects WHEN a regional stream launches, not WHAT gets covered. All regions at an unlocked tier eventually receive coverage.

---

## Funding Tier Structure

| Tier | Granularity | Monthly Threshold | What Unlocks |
|------|-------------|-------------------|--------------|
| 1 | International | $0 (baseline) | Global stream (exists now) |
| 2 | Country | $500/month sustained | Country-level streams (US, UK, CA, etc.) |
| 3 | State/Province | $2,000/month sustained | State-level streams (California, Texas, etc.) |
| 4 | County/District | $5,000/month sustained | County-level streams (Los Angeles County, Travis County, etc.) |
| 5 | Metro/City | $10,000/month sustained | City-level streams (Los Angeles, Austin, etc.) |

### Definitions

**Sustained:** 3 consecutive months at or above the threshold. This prevents launching streams on funding spikes that cannot be maintained.

**Capacity Limits (adjustable as operational capacity grows):**
- Tier 2: Up to 20 country streams
- Tier 3: Up to 50 state/province streams
- Tier 4: Up to 200 county/district streams
- Tier 5: Up to 500 metro/city streams

---

## Key Principles

### 1. Funding Unlocks Capacity, Not Exclusive Access

When funding reaches a tier threshold, that level of granularity becomes possible for ALL regions—not just regions whose supporters donated most. A donor interested in Wyoming has the same access as a donor interested in California once Tier 3 is unlocked.

### 2. Interest Determines Order, Not Outcome

Within each tier, regions with more expressed interest launch first. But ALL regions at that tier eventually launch. Interest affects the queue position, not whether a region gets coverage.

### 3. No Earmarking

All donations go to general JTF News operations. Donors may indicate regional interest, but funds are not earmarked for specific regions. This is legally cleaner and operationally simpler.

### 4. Transparent Progress

Public dashboard shows:
- Current funding tier status (e.g., "Tier 3: 68% funded")
- Interest breakdown by region (percentages, not raw counts)
- Deployment queue and status

---

## Donation Model

### GitHub Sponsors (Existing)

Donations are accepted through GitHub Sponsors at `github.com/sponsors/JTFNews`. Sponsor tiers are based on amount, not region:

| Sponsor Tier | Monthly Amount |
|--------------|----------------|
| Supporter | $3 |
| Contributor | $10 |
| Sustainer | $25 |
| Champion | $50+ |

### Interest Indication (Separate)

Regional interest is captured separately from donation:
- Optional form at jtfnews.com/interest
- Requires GitHub account or email verification (one indication per person)
- Can be updated anytime
- Available to donors and non-donors alike

This separation ensures:
- Donation amount doesn't buy more "votes"
- Interest signals are democratic
- Legal clarity (no implied earmarking)

---

## Anti-Gaming Measures

To prevent manipulation of interest signals:

1. **Identity Verification:** Interest indication requires GitHub account or verified email (one vote per person)
2. **Percentage Display:** Show interest as percentages, not raw counts (normalizes across population sizes)
3. **No Real-Time Updates:** Interest percentages update daily, not in real-time (prevents gaming feedback loops)

---

## Communication Guidelines

### What We Say

> "Your donation supports JTF News operations. You may optionally indicate which regions interest you most—this helps us prioritize deployment order as we expand."

> "All regions at each funding tier will eventually receive coverage. Interest signals help us decide which to launch first."

### What We Don't Say

- "Donate to unlock California" (implies earmarking)
- "Your $50 builds the Texas stream" (implies direct allocation)
- "Top donors choose regions" (implies pay-to-play)

---

## Transition to Equal Treatment

The prioritization system is temporary—it applies only during the growth phase:

1. **During Growth:** Funding determines which tier is unlocked. Interest determines deployment order within tiers.

2. **At Coverage-Complete:** Once all regions at all unlocked tiers have streams, the prioritization phase ends. From that point, all regions receive equal maintenance and updates.

3. **Future Tiers:** If funding grows enough to unlock a new tier, the cycle repeats for that tier only.

---

## Legal Considerations

This model is designed to be legally defensible:

1. **No Earmarking:** Funds go to general operations, not specific regions
2. **No Broken Promises:** We never promise a specific region will launch
3. **Transparent Methodology:** Prioritization logic is public and consistent
4. **Democratic Signals:** Interest indication is available to all, not just donors
5. **Equal Eventual Coverage:** All regions at unlocked tiers receive coverage

---

## Document Status

**Last Updated:** 2026-02-14
**Status:** Design complete

**Full Design Document:** See `docs/plans/2026-02-14-funding-regional-prioritization-design.md` for complete technical specifications including:
- Interest capture mechanism
- Public dashboard layout
- Deployment prioritization algorithm
- Legal/communication framework
- Integration with existing systems
