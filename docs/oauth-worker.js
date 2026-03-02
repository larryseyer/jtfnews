// JTF News GitHub OAuth Proxy
// Deployed as a Cloudflare Worker (free tier)
// Exchanges GitHub OAuth code for access token
// This is needed because GitHub Pages is static and cannot do server-side token exchange
//
// Setup:
// 1. Create a Cloudflare Worker at dash.cloudflare.com
// 2. Set environment variables: GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET
// 3. Deploy this script
// 4. Update OAUTH_PROXY_URL in register.html and submit.html

addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request));
});

async function handleRequest(request) {
  // Handle CORS preflight
  if (request.method === 'OPTIONS') {
    return new Response(null, {
      headers: {
        'Access-Control-Allow-Origin': 'https://jtfnews.org',
        'Access-Control-Allow-Methods': 'POST',
        'Access-Control-Allow-Headers': 'Content-Type',
      },
    });
  }

  if (request.method !== 'POST') {
    return new Response('Method not allowed', { status: 405 });
  }

  const { code } = await request.json();
  if (!code) {
    return new Response(JSON.stringify({ error: 'Missing code' }), { status: 400 });
  }

  // Exchange code for token
  const tokenResponse = await fetch('https://github.com/login/oauth/access_token', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify({
      client_id: GITHUB_CLIENT_ID,       // Set as Worker environment variable
      client_secret: GITHUB_CLIENT_SECRET, // Set as Worker environment variable
      code: code,
    }),
  });

  const tokenData = await tokenResponse.json();

  return new Response(JSON.stringify(tokenData), {
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': 'https://jtfnews.org',
    },
  });
}
