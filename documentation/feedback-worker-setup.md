# Feedback Worker — Cloudflare Deployment Guide

## Overview

The Feedback Worker is a Cloudflare Worker that accepts community feedback submissions from `jtfnews.org/feedback`. It validates submissions through 4 spam prevention layers (honeypot, time gate, rate limiting, proof of work), then pushes feedback records as JSON files to the GitHub repository. Zero personal data is stored.

Source: `docs/feedback-worker.js`

This is a **separate worker** from the OAuth proxy (`docs/oauth-worker.js`). Each has its own deployment and environment variables.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GITHUB_TOKEN` | Yes | GitHub personal access token with `repo` scope. Used to push feedback files via the GitHub Contents API. |
| `POW_DIFFICULTY` | No | Number of leading hex zeros required in proof-of-work hash. Defaults to `4`. |

### Creating the GitHub Token

1. Go to https://github.com/settings/tokens
2. Generate a new token (classic) with `repo` scope
3. Copy the token — you will not see it again

---

## Deployment Steps (Cloudflare Dashboard)

1. Log in to https://dash.cloudflare.com
2. Go to **Workers & Pages** in the sidebar
3. Click **Create application** then **Create Worker**
4. Name the worker (e.g., `jtfnews-feedback`)
5. Click **Deploy** to create the worker with the default script
6. Click **Edit code** (or go to the worker's **Quick Edit**)
7. Replace the default script with the contents of `docs/feedback-worker.js`
8. Click **Save and Deploy**
9. Go to **Settings > Variables**
10. Add `GITHUB_TOKEN` as an **encrypted** environment variable
11. Optionally add `POW_DIFFICULTY` as a plain text variable (default: `4`)
12. Note the worker URL (e.g., `https://jtfnews-feedback.yoursubdomain.workers.dev`)
13. Update `FEEDBACK_WORKER_URL` in `docs/feedback.html` with this URL

### Custom Domain (Optional)

To use a subdomain like `feedback-api.jtfnews.org`:

1. In the worker settings, go to **Triggers > Custom Domains**
2. Add `feedback-api.jtfnews.org`
3. Cloudflare handles DNS and TLS automatically

---

## Cloudflare Rate Limiting Rule

The worker has in-memory rate limiting (5 req/hr/IP), but this resets on worker restarts. For infrastructure-level protection, add a Cloudflare Rate Limiting rule:

1. In Cloudflare Dashboard, go to **Security > WAF > Rate limiting rules**
2. Click **Create rule**
3. Configure:
   - **Rule name:** `Feedback API rate limit`
   - **If incoming requests match:** URI Path equals `/` (the worker handles its own path)
   - **With the same characteristics:** IP
   - **When rate exceeds:** 5 requests per 1 hour
   - **Then take action:** Block (with 429 response)
   - **For duration:** 1 hour
4. Deploy the rule

This provides a second layer of rate limiting that persists across worker restarts and isolate restarts.

---

## Security Notes

- **No personal data stored.** Feedback records contain only the submission content, category, and timestamp. No IP addresses, no cookies, no user agents, no identifiers.
- **CORS restricted.** Only `https://jtfnews.org` can make requests. All other origins are rejected.
- **GitHub token never leaves Cloudflare.** The token is stored as an encrypted environment variable and is only used server-side to push files.
- **Honeypot returns fake success.** Bots that fill the hidden `website` field get a 200 OK with a dummy reference number, so they never know they were caught.
- **Proof of work deters scripted abuse.** Clients must compute a valid SHA-256 hash with leading zeros before submitting.
- **Rate limits are dual-layer.** In-memory (worker) + infrastructure (Cloudflare WAF) for defense in depth.

---

## Testing

### Test with curl

**Successful submission** (requires valid proof of work):

```bash
# First generate a valid proof of work (example using Node.js):
node -e "
const crypto = require('crypto');
let nonce = 0;
while (true) {
  const hash = crypto.createHash('sha256').update(String(nonce)).digest('hex');
  if (hash.startsWith('0000')) {
    console.log(JSON.stringify({ nonce: String(nonce), hash }));
    break;
  }
  nonce++;
}
"
# Use the nonce and hash from above:

curl -X POST https://YOUR-WORKER-URL/ \
  -H 'Content-Type: application/json' \
  -H 'Origin: https://jtfnews.org' \
  -d '{
    "category": "factual_error",
    "details": "The reported figure of 500 was actually 5000 according to the official source.",
    "loaded_at": 1700000000000,
    "pow_nonce": "NONCE_FROM_ABOVE",
    "pow_hash": "HASH_FROM_ABOVE"
  }'
```

**Honeypot test** (should return fake success):

```bash
curl -X POST https://YOUR-WORKER-URL/ \
  -H 'Content-Type: application/json' \
  -H 'Origin: https://jtfnews.org' \
  -d '{
    "website": "http://spam.example.com",
    "category": "other",
    "details": "This is a bot submission that should be silently rejected."
  }'
# Expected: {"ref":"JTF-00000000-0000"}
```

**Wrong method:**

```bash
curl -X GET https://YOUR-WORKER-URL/
# Expected: 405 {"error":"Method not allowed"}
```

### Verify on GitHub

After a successful submission, check that the feedback file appeared:

```
https://github.com/JTFNews/jtfnews/tree/main/data/feedback/
```

Each file is named `JTF-YYYYMMDD-XXXX.json` and contains the feedback record.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| 500 error on submission | GitHub token invalid or expired | Regenerate token and update worker env var |
| 500 error on submission | `data/feedback/` directory does not exist in repo | Create the directory by adding a `.gitkeep` file |
| CORS error in browser console | Origin mismatch | Verify the request comes from `https://jtfnews.org` (not `www.` or `http://`) |
| 429 "Rate limit exceeded" | IP submitted more than 5 times in an hour | Wait 1 hour, or check Cloudflare WAF if the infrastructure rule is too aggressive |
| 429 "Please wait a moment" | Time gate triggered — page loaded less than 5 seconds ago | Ensure `loaded_at` is set on page load, not on form submit |
| 400 "Invalid proof of work" | Hash does not match nonce, or does not meet difficulty | Verify client-side PoW implementation computes SHA-256 of the nonce string and checks for correct number of leading zeros |
| 400 "Category must be one of..." | Invalid category value | Check that the form sends one of: `factual_error`, `bias_distortion`, `suggestion`, `other` |
| Feedback file not appearing on GitHub | Token lacks `repo` scope | Regenerate with `repo` scope checked |
