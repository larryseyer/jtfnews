# Support Page Design

## Summary

Create a dedicated `docs/support.html` page that:
1. Explains the JTF mission and why it matters (whitepaper fundamentals)
2. Houses the Operational Costs widget (moved from index.html)
3. Links to the Get Involved Support card / GitHub Sponsors
4. Is accessible from site navigation (last item in nav)

## Page Structure: `docs/support.html`

### 1. Hero / Opening
- Title: "Support JTF News"
- Subtitle conveying core tension: facts are buried under opinion, JTF exists to fix that

### 2. The Problem
- Brief section on why this matters
- News driven by engagement, not accuracy
- Adjectives replace facts; ownership is hidden
- The audience doesn't know who funds the narrative

### 3. The JTF Methodology
- Philosophy callout blocks (`.philosophy` component, gold left-border):
  - "Two sources. Different owners. Strip the adjectives. State the facts. Stop."
  - "No ads. No tracking. No paywalls. Just the record."
  - "The methodology belongs to no one. It serves everyone."
- Brief explanation: two-source verification, AI fact extraction, ownership transparency, public corrections
- Link to full whitepaper

### 4. Full Transparency — Operational Costs (Live)
- Moved from index.html (lines 120-167)
- Real-time API costs widget showing exactly where every dollar goes
- "View Full Operations Dashboard" link to monitor.html
- JavaScript for costs widget moves here (formatCurrency, formatUptime, checkForCycleRefresh, loadCosts)

### 5. How to Support
- Call to action: GitHub Sponsors button (gold `btn--primary`)
- Message: "No ads. No tracking. Viewer-supported."
- Secondary options: sharing, contributing as a journalist, submitting stories

### 6. Standard CTA Footer
- Consistent with other pages

## Files Modified

### Navigation updates (desktop + mobile nav) — 11 files:
- `docs/index.html`
- `docs/how-it-works.html`
- `docs/whitepaper.html`
- `docs/sources.html`
- `docs/archive.html`
- `docs/corrections.html`
- `docs/screensaver-setup.html`
- `docs/journalists.html`
- `docs/submit.html`
- `docs/register.html`
- `docs/monitor.html`

Add `<li><a href="support.html">Support</a></li>` as last item in `site-nav__links`.
Add `<a href="support.html">Support</a>` as last item in `nav-overlay`.

### Footer updates — 10 files:
Change footer "Support" link from `https://github.com/sponsors/larryseyer` to `support.html` on all pages that have it.

### CTA button updates — 2 files:
- `docs/whitepaper.html` — CTA "Support JTF News" button: change href to `support.html`
- `docs/how-it-works.html` — CTA "Support JTF News" button: change href to `support.html`

### index.html specific changes:
- Remove entire Operational Costs section (lines 120-167)
- Remove costs-related JavaScript (formatCurrency, formatUptime, checkForCycleRefresh, loadCosts, setInterval) — keep live story preview JS
- Change Get Involved "Support" card href from `https://github.com/sponsors/larryseyer` to `support.html`

### New file:
- `docs/support.html` — follows standard page template with SEO meta tags, OpenGraph, favicons, shared stylesheet

### NOT modified:
- `docs/screensaver.html` — display text references to sponsors stay as-is
- `docs/style.css` — all needed CSS components already exist (.philosophy, .costs-section, .card, etc.)
