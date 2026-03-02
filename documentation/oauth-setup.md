# GitHub OAuth Setup for Journalist Submissions

## Overview

JTF News uses GitHub OAuth to authenticate journalist contributors. Since the site is static (GitHub Pages), a Cloudflare Worker proxy handles the OAuth code-to-token exchange.

## Components

### 1. GitHub OAuth App
- **Already created** in the JTFNews GitHub organization
- Application name: `JTF News Contributor`
- Homepage URL: `https://jtfnews.org`
- Authorization callback URL: `https://jtfnews.org/submit.html`
- The **Client ID** is public and embedded in the HTML pages
- The **Client Secret** is stored only in the Cloudflare Worker environment

### 2. Cloudflare Worker Proxy
- Source: `docs/oauth-worker.js`
- Purpose: Exchanges GitHub OAuth authorization code for access token
- Endpoint: POST with `{ "code": "..." }` body

### Deployment Steps

1. Log in to [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Go to **Workers & Pages** → **Create Worker**
3. Name it (e.g., `jtf-oauth`)
4. Paste the contents of `docs/oauth-worker.js`
5. Go to **Settings** → **Variables** and add:
   - `GITHUB_CLIENT_ID` = (from GitHub OAuth app)
   - `GITHUB_CLIENT_SECRET` = (from GitHub OAuth app, encrypt this)
6. Deploy
7. Note the worker URL (e.g., `https://jtf-oauth.your-account.workers.dev`)
8. Update `OAUTH_PROXY_URL` in:
   - `docs/register.html`
   - `docs/submit.html`

### Security Notes

- The worker only accepts POST requests
- CORS is restricted to `https://jtfnews.org`
- The client secret never leaves Cloudflare's environment
- GitHub tokens are stored only in the user's browser session (sessionStorage)
- No tokens are stored server-side or in the repository

### Testing

1. Visit `https://jtfnews.org/register.html`
2. Click "Sign in with GitHub"
3. Should redirect to GitHub OAuth consent screen
4. After authorizing, should redirect back with a code
5. The code is exchanged for a token via the worker
6. Registration form should appear

### Troubleshooting

- **CORS errors**: Verify the worker's `Access-Control-Allow-Origin` matches exactly
- **Token exchange fails**: Check Cloudflare Worker logs for errors
- **"Bad credentials"**: Verify GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET in worker env
- **Redirect loop**: Verify callback URL in GitHub OAuth app settings matches exactly
