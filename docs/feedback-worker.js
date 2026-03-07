// JTF News Feedback Worker
// Deployed as a Cloudflare Worker (separate from OAuth worker)
// Accepts community feedback submissions with 4-layer spam prevention
// Pushes feedback records to GitHub — stores ZERO personal data
//
// Setup:
// 1. Create a Cloudflare Worker at dash.cloudflare.com
// 2. Set environment variables: GITHUB_TOKEN, POW_DIFFICULTY (optional, defaults to 4)
// 3. Deploy this script
// 4. Update FEEDBACK_WORKER_URL in feedback.html

// --- Rate limit state (in-memory, resets on worker restart) ---
const rateLimitMap = new Map();

const VALID_CATEGORIES = ['factual_error', 'bias_distortion', 'suggestion', 'other'];
const MAX_DETAILS_LENGTH = 2000;
const MAX_URL_LENGTH = 500;
const RATE_LIMIT_MAX = 5;
const RATE_LIMIT_WINDOW_MS = 60 * 60 * 1000; // 1 hour
const TIME_GATE_MS = 5000;

addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request));
});

// --- CORS headers ---

function corsHeaders() {
  return {
    'Access-Control-Allow-Origin': 'https://jtfnews.org',
    'Access-Control-Allow-Methods': 'POST',
    'Access-Control-Allow-Headers': 'Content-Type',
  };
}

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json',
      ...corsHeaders(),
    },
  });
}

// --- Rate limit cleanup ---

function cleanupRateLimits() {
  const now = Date.now();
  for (const [ip, entry] of rateLimitMap) {
    if (now - entry.windowStart > RATE_LIMIT_WINDOW_MS) {
      rateLimitMap.delete(ip);
    }
  }
}

// --- Reference number generation ---

function generateRef() {
  const now = new Date();
  const yyyy = now.getUTCFullYear();
  const mm = String(now.getUTCMonth() + 1).padStart(2, '0');
  const dd = String(now.getUTCDate()).padStart(2, '0');
  const hex = Math.floor(Math.random() * 0xFFFFFFFF).toString(16).padStart(8, '0');
  return `JTF-${yyyy}${mm}${dd}-${hex}`;
}

// --- Proof of work verification ---

async function verifyProofOfWork(nonce, hash, difficulty) {
  const encoder = new TextEncoder();
  const data = encoder.encode(String(nonce));
  const digestBuffer = await crypto.subtle.digest('SHA-256', data);
  const digestArray = Array.from(new Uint8Array(digestBuffer));
  const computedHash = digestArray.map(b => b.toString(16).padStart(2, '0')).join('');

  if (computedHash !== hash) {
    return false;
  }

  const prefix = '0'.repeat(difficulty);
  if (!hash.startsWith(prefix)) {
    return false;
  }

  return true;
}

// --- Main handler ---

async function handleRequest(request) {
  // Handle CORS preflight
  if (request.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders() });
  }

  // POST only
  if (request.method !== 'POST') {
    return jsonResponse({ error: 'Method not allowed' }, 405);
  }

  // Clean up stale rate limit entries on every request
  cleanupRateLimits();

  let body;
  try {
    body = await request.json();
  } catch (e) {
    return jsonResponse({ error: 'Invalid JSON body' }, 400);
  }

  // --- Layer 1: Honeypot ---
  if (body.website) {
    return jsonResponse({ ref: 'JTF-00000000-0000' });
  }

  // --- Layer 2: Time gate ---
  const loadedAt = Number(body.loaded_at);
  const elapsed = Date.now() - loadedAt;
  if (!loadedAt || isNaN(loadedAt) || elapsed < TIME_GATE_MS || elapsed > 86400000) {
    return jsonResponse({ error: 'Please wait a moment before submitting' }, 429);
  }

  // --- Layer 3: Rate limit ---
  const clientIP = request.headers.get('CF-Connecting-IP') || 'unknown';
  const now = Date.now();
  let entry = rateLimitMap.get(clientIP);

  if (!entry || (now - entry.windowStart > RATE_LIMIT_WINDOW_MS)) {
    entry = { windowStart: now, count: 0 };
    rateLimitMap.set(clientIP, entry);
  }

  entry.count++;
  if (entry.count > RATE_LIMIT_MAX) {
    return jsonResponse({ error: 'Rate limit exceeded. Maximum 5 submissions per hour.' }, 429);
  }

  // --- Layer 4: Proof of work ---
  const powDifficulty = typeof POW_DIFFICULTY !== 'undefined' ? Number(POW_DIFFICULTY) : 4;
  const powNonce = body.pow_nonce;
  const powHash = body.pow_hash;

  if (!powNonce || !powHash) {
    return jsonResponse({ error: 'Proof of work required' }, 400);
  }

  const powValid = await verifyProofOfWork(powNonce, powHash, powDifficulty);
  if (!powValid) {
    return jsonResponse({ error: 'Invalid proof of work' }, 400);
  }

  // --- Validate required fields ---
  if (!body.category || !VALID_CATEGORIES.includes(body.category)) {
    return jsonResponse({ error: `Category must be one of: ${VALID_CATEGORIES.join(', ')}` }, 400);
  }

  const details = typeof body.details === 'string' ? body.details.trim() : '';
  if (details.length < 20) {
    return jsonResponse({ error: 'Details must be at least 20 characters' }, 400);
  }

  // --- Build feedback record ---
  const ref = generateRef();
  const record = {
    ref: ref,
    timestamp: new Date().toISOString(),
    category: body.category,
    story_id: (typeof body.story_id === 'string' && body.story_id.trim()) ? body.story_id.trim() : null,
    details: details.substring(0, MAX_DETAILS_LENGTH),
    evidence_url: (typeof body.evidence_url === 'string' && body.evidence_url.trim())
      ? body.evidence_url.trim().substring(0, MAX_URL_LENGTH)
      : null,
    status: 'pending',
  };

  // --- Push to GitHub ---
  const fileContent = JSON.stringify(record, null, 2);
  const encoded = btoa(unescape(encodeURIComponent(fileContent)));
  const path = `data/feedback/${ref}.json`;

  try {
    const ghResponse = await fetch(`https://api.github.com/repos/JTFNews/jtfnews/contents/${path}`, {
      method: 'PUT',
      headers: {
        'Authorization': `token ${GITHUB_TOKEN}`,
        'Content-Type': 'application/json',
        'User-Agent': 'JTFNews-Feedback-Worker',
      },
      body: JSON.stringify({
        message: `feedback: ${ref}`,
        content: encoded,
        branch: 'main',
      }),
    });

    if (!ghResponse.ok) {
      console.error('GitHub API error:', ghResponse.status, await ghResponse.text());
      return jsonResponse({ error: 'Failed to save feedback. Please try again later.' }, 500);
    }
  } catch (e) {
    console.error('GitHub API request failed:', e);
    return jsonResponse({ error: 'Failed to save feedback. Please try again later.' }, 500);
  }

  // --- Success ---
  return jsonResponse({ ref: ref });
}
