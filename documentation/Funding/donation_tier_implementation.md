# Donation Tier Implementation Guide

**Last updated:** 2026-02-14
**Status:** Design complete, ready for implementation

---

## What Was Done

1. **Brainstormed** funding-based regional prioritization approaches
2. **Chose model:** Community Milestone Model — tier-based funding with democratic interest signals
3. **Wrote design docs:**
   - `docs/plans/2026-02-14-funding-regional-prioritization-design.md` (full technical design)
   - `docs/donation_tiers.md` (public-facing tier documentation)

---

## Key Design Decisions

- **Separate donation from interest** — GitHub Sponsors for funding, separate form for regional interest
- **5-tier funding structure** — International → Country → State → County → City
- **Percentage-based interest display** — Normalizes across population sizes, updated daily
- **Identity-verified interest signals** — GitHub OAuth or email verification (one vote per person)
- **No earmarking** — All donations support general operations
- **Public dashboard** — Transparent progress and prioritization

---

## Implementation Tasks

### Phase 1: Core Infrastructure

| Task | Files | Priority |
|------|-------|----------|
| 1. Add tier config to config.json | `config.json` | High |
| 2. Create interest data schema | `data/interest.json` | High |
| 3. Create funding status schema | `data/funding.json` | High |

### Phase 2: Interest Capture

| Task | Files | Priority |
|------|-------|----------|
| 4. Create interest form page | `docs/interest.html` | High |
| 5. Implement GitHub OAuth flow | `docs/js/interest.js` | High |
| 6. Implement email verification fallback | `docs/js/interest.js` | Medium |
| 7. Create region selection UI (hierarchical) | `docs/js/interest.js` | High |
| 8. Build interest aggregation logic | Backend or static generation | High |

### Phase 3: Public Dashboard

| Task | Files | Priority |
|------|-------|----------|
| 9. Create progress dashboard page | `docs/progress.html` | High |
| 10. Implement funding progress bars | `docs/js/progress.js` | High |
| 11. Implement interest percentage display | `docs/js/progress.js` | High |
| 12. Implement deployment queue view | `docs/js/progress.js` | Medium |
| 13. Style dashboard (match JTF aesthetic) | `docs/css/progress.css` | Medium |

### Phase 4: Integration

| Task | Files | Priority |
|------|-------|----------|
| 14. Sync GitHub Sponsors donor status | Script or GitHub Actions | Medium |
| 15. Daily interest aggregation job | Script or GitHub Actions | Medium |
| 16. Add progress link to index.html | `docs/index.html` | Low |
| 17. Add interest link to sponsor messaging | `web/lower-third.js` | Low |

### Phase 5: Documentation & Launch

| Task | Files | Priority |
|------|-------|----------|
| 18. Update WhitePaper with funding model | `docs/WhitePaper.md` | Medium |
| 19. Add disclaimers to relevant pages | Multiple | High |
| 20. Test full flow end-to-end | N/A | High |

---

## Dependencies

**Must complete first:**
- Regional filtering implementation (provides location taxonomy)

**Can run in parallel:**
- GitHub Sponsors setup (already exists)
- Interest form development

---

## Config Changes

Add to `config.json`:

```json
{
  "funding": {
    "tiers": [
      {"level": 1, "name": "International", "threshold": 0, "capacity": 1},
      {"level": 2, "name": "Country", "threshold": 500, "capacity": 20},
      {"level": 3, "name": "State/Province", "threshold": 2000, "capacity": 50},
      {"level": 4, "name": "County/District", "threshold": 5000, "capacity": 200},
      {"level": 5, "name": "Metro/City", "threshold": 10000, "capacity": 500}
    ],
    "sustained_months": 3
  }
}
```

---

## Data Schemas

### interest.json

```json
{
  "updated_at": "2026-02-14T00:00:00Z",
  "total_signals": 142,
  "by_region": {
    "US": {"count": 64, "percentage": 45.1},
    "UK": {"count": 26, "percentage": 18.3},
    "US-CA": {"count": 17, "percentage": 12.0}
  }
}
```

### funding.json

```json
{
  "updated_at": "2026-02-14T10:00:00Z",
  "monthly_total": 365,
  "months_at_current": 2,
  "current_tier": 1,
  "tier_progress": {
    "2": {"threshold": 500, "current": 365, "percentage": 73}
  }
}
```

---

## How to Continue

Start a new Claude Code session and say:

```
Read docs/donation_tier_implementation.md and implement the funding tier system using the executing-plans skill.
```

Or for specific phases:

```
Read docs/donation_tier_implementation.md and implement Phase 2 (Interest Capture).
```

---

## Files to Reference

| File | Purpose |
|------|---------|
| `docs/plans/2026-02-14-funding-regional-prioritization-design.md` | Full design rationale |
| `docs/donation_tiers.md` | Public-facing tier documentation |
| `docs/plans/2026-02-13-regional-filtering-design.md` | Location taxonomy (dependency) |
| `docs/index.html` | Existing website structure |
| `config.json` | Add funding section |

---

## Quick Context

JTF News is expanding from a single global stream to regional coverage. This funding system:

1. **Tiers unlock granularity** — Total funding determines if we can do country/state/county/city level
2. **Interest determines order** — Within each tier, highest interest % launches first
3. **No earmarking** — Donations support operations, interest is separate
4. **Transparent** — Public dashboard shows progress and prioritization logic

The goal is sustainable expansion without compromising editorial neutrality.

---

## Important Constraints

- **No pay-to-play perception** — Interest signals are democratic (non-donors can indicate)
- **Legal clarity** — Required disclaimers on all pages
- **Privacy** — Store hashed identifiers, not raw emails
- **Gaming resistance** — Daily updates, percentage display, identity verification
