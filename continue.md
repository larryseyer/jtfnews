# Continue: Journalist Submission System

## Status: Implementation Complete, Manual Setup Remaining

All 17 tasks from `docs/plans/2026-03-02-journalist-submissions-implementation.md` have been implemented and committed to main (5 commits via `./bu.sh`).

## What's Done

- All backend functions in main.py (journalist data layer, unified source lookup, scoring, bias tracking, quota system, submission I/O, disclosure freshness, process_cycle integration, leaderboard generation, RSS support, quarterly audit extension)
- All frontend pages: register.html, submit.html, journalists.html, journalists.json
- OAuth proxy source: docs/oauth-worker.js
- Navigation updated on all 10 HTML pages
- New sections on index.html and how-it-works.html
- Documentation: documentation/oauth-setup.md, CLAUDE.md updated

## What's Left (Manual Steps)

1. **Deploy Cloudflare Worker** - Create a worker at dash.cloudflare.com, paste contents of `docs/oauth-worker.js`, set environment variables:
   - `GITHUB_CLIENT_ID` (from existing GitHub OAuth app)
   - `GITHUB_CLIENT_SECRET` (from existing GitHub OAuth app)

2. **Replace placeholders** in two files:
   - `docs/register.html` - find `PLACEHOLDER_CLIENT_ID` and `PLACEHOLDER_PROXY_URL`
   - `docs/submit.html` - find `PLACEHOLDER_CLIENT_ID` and `PLACEHOLDER_PROXY_URL`
   - Replace `PLACEHOLDER_CLIENT_ID` with GitHub OAuth Client ID
   - Replace `PLACEHOLDER_PROXY_URL` with Cloudflare Worker URL (e.g., `https://jtf-oauth.your-account.workers.dev`)

3. **Test the full OAuth flow** in browser (register, submit, verify)

4. **Visually verify** all new HTML pages render correctly

## Key Files Reference

| File | Purpose |
|------|---------|
| `docs/plans/2026-03-02-journalist-submissions-implementation.md` | Original 17-task implementation plan |
| `documentation/journalist-submissions-design.md` | Full design document (19 sections) |
| `documentation/oauth-setup.md` | Cloudflare Worker deployment guide |
| `docs/oauth-worker.js` | Cloudflare Worker source code |
| `docs/register.html` | Journalist registration page |
| `docs/submit.html` | Story submission page |
| `docs/journalists.html` | Public leaderboard page |
| `docs/journalists.json` | Leaderboard data (generated nightly) |
| `data/journalists.json` | Journalist profiles store |
| `data/submissions/` | Pending submission JSONs |
| `data/submissions/processed/` | Processed submission JSONs |
