#!/usr/bin/env python3
"""JTF News Feedback Viewer - localhost-only admin tool.

Starts a web server on 127.0.0.1:8899 to view and manage community feedback.
Only accessible from this machine. Not deployed to GitHub Pages.

Usage:
    python view_feedback.py
    python view_feedback.py --port 9000
"""

import json
import os
import sys
import argparse
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

DATA_DIR = Path(__file__).parent / "data"
FEEDBACK_DIR = DATA_DIR / "feedback"
PROCESSED_DIR = FEEDBACK_DIR / "processed"

# ── Data helpers ─────────────────────────────────────────────

def load_processed():
    """Load all processed feedback files."""
    items = []
    if PROCESSED_DIR.exists():
        for f in sorted(PROCESSED_DIR.glob("JTF-*.json"), reverse=True):
            try:
                with open(f) as fh:
                    fb = json.load(fh)
                fb["_file"] = f.name
                items.append(fb)
            except Exception:
                continue
    return items


def load_pending():
    """Load pending (unprocessed) feedback files."""
    items = []
    if FEEDBACK_DIR.exists():
        for f in sorted(FEEDBACK_DIR.glob("JTF-*.json"), reverse=True):
            try:
                with open(f) as fh:
                    fb = json.load(fh)
                fb["_file"] = f.name
                items.append(fb)
            except Exception:
                continue
    return items


def load_suggestions():
    """Load suggestions log."""
    path = FEEDBACK_DIR / "suggestions.json"
    if path.exists():
        try:
            with open(path) as f:
                data = json.load(f)
            return data.get("suggestions", [])
        except Exception:
            pass
    return []


def load_bias_reports():
    """Load bias reports log."""
    path = FEEDBACK_DIR / "bias_reports.json"
    if path.exists():
        try:
            with open(path) as f:
                data = json.load(f)
            return data.get("reports", [])
        except Exception:
            pass
    return []


def load_stats():
    """Load feedback stats."""
    path = FEEDBACK_DIR / "stats.json"
    if path.exists():
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return {"daily": {}, "totals": {}}


def delete_file(filename):
    """Delete a feedback file from processed or pending."""
    for directory in [PROCESSED_DIR, FEEDBACK_DIR]:
        path = directory / filename
        if path.exists():
            path.unlink()
            return True
    return False


def delete_suggestion(ref):
    """Remove a suggestion by ref from suggestions.json."""
    path = FEEDBACK_DIR / "suggestions.json"
    if not path.exists():
        return False
    try:
        with open(path) as f:
            data = json.load(f)
        before = len(data.get("suggestions", []))
        data["suggestions"] = [s for s in data.get("suggestions", []) if s.get("ref") != ref]
        if len(data["suggestions"]) < before:
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
            return True
    except Exception:
        pass
    return False


def delete_bias_report(ref):
    """Remove a bias report by ref from bias_reports.json."""
    path = FEEDBACK_DIR / "bias_reports.json"
    if not path.exists():
        return False
    try:
        with open(path) as f:
            data = json.load(f)
        before = len(data.get("reports", []))
        data["reports"] = [r for r in data.get("reports", []) if r.get("ref") != ref]
        if len(data["reports"]) < before:
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
            return True
    except Exception:
        pass
    return False


# ── HTML Template ────────────────────────────────────────────

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JTF Feedback Viewer (Local Only)</title>
<style>
  :root {
    --bg: #0d1117; --surface: #161b22; --border: #30363d;
    --text: #e6edf3; --muted: #8b949e; --accent: #58a6ff;
    --green: #3fb950; --red: #f85149; --yellow: #d29922; --purple: #bc8cff;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: var(--bg); color: var(--text); line-height: 1.5; padding: 1.5rem; }
  h1 { font-size: 1.4rem; margin-bottom: 0.25rem; }
  .subtitle { color: var(--muted); font-size: 0.85rem; margin-bottom: 1.5rem; }
  .warning { background: #d292221a; border: 1px solid var(--yellow); border-radius: 6px;
             padding: 0.75rem 1rem; margin-bottom: 1.5rem; font-size: 0.85rem; color: var(--yellow); }

  /* Tabs */
  .tabs { display: flex; gap: 0; border-bottom: 1px solid var(--border); margin-bottom: 1.5rem; }
  .tab { padding: 0.6rem 1.2rem; cursor: pointer; color: var(--muted); border-bottom: 2px solid transparent;
         font-size: 0.9rem; transition: all 0.15s; background: none; border-top: none; border-left: none; border-right: none; }
  .tab:hover { color: var(--text); }
  .tab.active { color: var(--accent); border-bottom-color: var(--accent); }
  .tab .count { background: var(--surface); border: 1px solid var(--border); border-radius: 10px;
                padding: 0 6px; font-size: 0.75rem; margin-left: 6px; }
  .tab-content { display: none; }
  .tab-content.active { display: block; }

  /* Stats */
  .stats { display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1.5rem; }
  .stat { background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
          padding: 1rem 1.25rem; min-width: 120px; }
  .stat-value { font-size: 1.5rem; font-weight: 700; }
  .stat-label { color: var(--muted); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.5px; }

  /* Cards */
  .card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
          padding: 1rem 1.25rem; margin-bottom: 0.75rem; }
  .card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem; }
  .card-ref { font-family: monospace; font-size: 0.85rem; color: var(--accent); }
  .card-time { font-size: 0.8rem; color: var(--muted); }
  .card-meta { display: flex; gap: 0.75rem; flex-wrap: wrap; margin-bottom: 0.5rem; font-size: 0.8rem; }
  .badge { padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }
  .badge-spam { background: #f851491a; color: var(--red); }
  .badge-suggestion { background: #58a6ff1a; color: var(--accent); }
  .badge-bias { background: #d292221a; color: var(--yellow); }
  .badge-factual { background: #3fb9501a; color: var(--green); }
  .badge-other { background: #bc8cff1a; color: var(--purple); }
  .badge-pending { background: #d292221a; color: var(--yellow); }
  .card-details { font-size: 0.9rem; margin-bottom: 0.75rem; white-space: pre-wrap; word-break: break-word; }
  .card-story { font-size: 0.8rem; color: var(--muted); }
  .card-action { font-size: 0.8rem; color: var(--muted); font-style: italic; }
  .card-evidence { font-size: 0.8rem; }
  .card-evidence a { color: var(--accent); }
  .card-actions { display: flex; gap: 0.5rem; margin-top: 0.75rem; }

  /* Buttons */
  .btn { padding: 4px 12px; border-radius: 6px; border: 1px solid var(--border); cursor: pointer;
         font-size: 0.8rem; transition: all 0.15s; }
  .btn-delete { background: transparent; color: var(--red); border-color: var(--red); }
  .btn-delete:hover { background: var(--red); color: #fff; }

  .empty { text-align: center; padding: 3rem; color: var(--muted); }
  .refresh { color: var(--accent); background: none; border: 1px solid var(--accent); border-radius: 6px;
             padding: 6px 14px; cursor: pointer; font-size: 0.85rem; float: right; }
  .refresh:hover { background: var(--accent); color: var(--bg); }
</style>
</head>
<body>

<div style="display:flex;justify-content:space-between;align-items:flex-start;">
  <div>
    <h1>JTF Feedback Viewer</h1>
    <p class="subtitle">Local admin tool -- 127.0.0.1 only -- not public</p>
  </div>
  <button class="refresh" onclick="location.reload()">Refresh</button>
</div>

<div class="warning">This tool runs on localhost only. It has delete privileges. Do not expose to network.</div>

<div class="stats" id="stats"></div>

<div class="tabs">
  <button class="tab active" data-tab="pending">Pending <span class="count" id="count-pending">0</span></button>
  <button class="tab" data-tab="processed">Processed <span class="count" id="count-processed">0</span></button>
  <button class="tab" data-tab="suggestions">Suggestions <span class="count" id="count-suggestions">0</span></button>
  <button class="tab" data-tab="bias">Bias Reports <span class="count" id="count-bias">0</span></button>
</div>

<div class="tab-content active" id="tab-pending"></div>
<div class="tab-content" id="tab-processed"></div>
<div class="tab-content" id="tab-suggestions"></div>
<div class="tab-content" id="tab-bias"></div>

<script>
// Tab switching
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById('tab-' + tab.dataset.tab).classList.add('active');
  });
});

function formatTime(ts) {
  if (!ts) return '';
  try {
    const d = new Date(ts);
    return d.toLocaleString();
  } catch(e) { return ts; }
}

function badgeClass(triage) {
  const map = { spam: 'spam', suggestion: 'suggestion', bias_distortion: 'bias',
                factual_error: 'factual', other: 'other', pending: 'pending' };
  return 'badge-' + (map[triage] || 'other');
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text || '';
  return div.innerHTML;
}

function renderCard(item, type) {
  const ref = item.ref || item._file || '';
  const triage = item.triage_result || item.status || type;
  const details = item.details || '';
  const storyId = item.story_id || '';
  const evidence = item.evidence_url || '';
  const action = item.action_taken || '';
  const ts = item.timestamp || item.processed_at || '';
  const category = item.category || '';

  let deleteBtn = '';
  if (type === 'processed' || type === 'pending') {
    deleteBtn = '<button class="btn btn-delete" data-action="delete-item" data-file="' +
      escapeHtml(item._file || '') + '" data-type="' + type + '">Delete</button>';
  } else if (type === 'suggestion') {
    deleteBtn = '<button class="btn btn-delete" data-action="delete-suggestion" data-ref="' +
      escapeHtml(ref) + '">Delete</button>';
  } else if (type === 'bias') {
    deleteBtn = '<button class="btn btn-delete" data-action="delete-bias" data-ref="' +
      escapeHtml(ref) + '">Delete</button>';
  }

  let evidenceHtml = '';
  if (evidence) {
    evidenceHtml = '<div class="card-evidence">Evidence: <a href="' +
      escapeHtml(evidence) + '" target="_blank" rel="noopener">' + escapeHtml(evidence) + '</a></div>';
  }

  return '<div class="card">' +
    '<div class="card-header">' +
      '<span class="card-ref">' + escapeHtml(ref) + '</span>' +
      '<span class="card-time">' + formatTime(ts) + '</span>' +
    '</div>' +
    '<div class="card-meta">' +
      (category ? '<span class="badge ' + badgeClass(category) + '">' + escapeHtml(category) + '</span>' : '') +
      '<span class="badge ' + badgeClass(triage) + '">' + escapeHtml(triage) + '</span>' +
      (storyId ? '<span class="card-story">Story: ' + escapeHtml(storyId) + '</span>' : '') +
    '</div>' +
    '<div class="card-details">' + escapeHtml(details) + '</div>' +
    evidenceHtml +
    (action ? '<div class="card-action">Action: ' + escapeHtml(action) + '</div>' : '') +
    '<div class="card-actions">' + deleteBtn + '</div>' +
  '</div>';
}

document.addEventListener('click', async function(e) {
  const btn = e.target.closest('[data-action]');
  if (!btn) return;
  const action = btn.dataset.action;

  if (action === 'delete-item') {
    const filename = btn.dataset.file;
    if (!confirm('Delete ' + filename + '?')) return;
    const resp = await fetch('/api/delete', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({filename: filename})
    });
    if (resp.ok) loadData();
    else alert('Delete failed');

  } else if (action === 'delete-suggestion') {
    const ref = btn.dataset.ref;
    if (!confirm('Delete suggestion ' + ref + '?')) return;
    const resp = await fetch('/api/delete-suggestion', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ref: ref})
    });
    if (resp.ok) loadData();
    else alert('Delete failed');

  } else if (action === 'delete-bias') {
    const ref = btn.dataset.ref;
    if (!confirm('Delete bias report ' + ref + '?')) return;
    const resp = await fetch('/api/delete-bias', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ref: ref})
    });
    if (resp.ok) loadData();
    else alert('Delete failed');
  }
});

async function loadData() {
  try {
    const resp = await fetch('/api/data');
    const data = await resp.json();

    // Stats
    const totals = data.stats.totals || {};
    const statsHtml = Object.entries(totals).map(([k,v]) =>
      '<div class="stat"><div class="stat-value">' + v + '</div><div class="stat-label">' + k + '</div></div>'
    ).join('');
    document.getElementById('stats').innerHTML = statsHtml || '<div class="stat"><div class="stat-value">0</div><div class="stat-label">total</div></div>';

    // Pending
    document.getElementById('count-pending').textContent = data.pending.length;
    document.getElementById('tab-pending').innerHTML = data.pending.length
      ? data.pending.map(i => renderCard(i, 'pending')).join('')
      : '<div class="empty">No pending feedback</div>';

    // Processed
    document.getElementById('count-processed').textContent = data.processed.length;
    document.getElementById('tab-processed').innerHTML = data.processed.length
      ? data.processed.map(i => renderCard(i, 'processed')).join('')
      : '<div class="empty">No processed feedback</div>';

    // Suggestions
    document.getElementById('count-suggestions').textContent = data.suggestions.length;
    document.getElementById('tab-suggestions').innerHTML = data.suggestions.length
      ? data.suggestions.map(i => renderCard(i, 'suggestion')).join('')
      : '<div class="empty">No suggestions</div>';

    // Bias
    document.getElementById('count-bias').textContent = data.bias.length;
    document.getElementById('tab-bias').innerHTML = data.bias.length
      ? data.bias.map(i => renderCard(i, 'bias')).join('')
      : '<div class="empty">No bias reports</div>';

  } catch(e) {
    document.getElementById('tab-pending').innerHTML =
      '<div class="empty">Failed to load data: ' + e.message + '</div>';
  }
}

loadData();
</script>
</body>
</html>"""


# ── HTTP Server ──────────────────────────────────────────────

class FeedbackHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Quieter logging
        print(f"[{self.log_date_time_string()}] {args[0]}")

    def send_json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, html, status=200):
        body = html.encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/" or parsed.path == "/index.html":
            self.send_html(HTML_PAGE)

        elif parsed.path == "/api/data":
            data = {
                "pending": load_pending(),
                "processed": load_processed(),
                "suggestions": load_suggestions(),
                "bias": load_bias_reports(),
                "stats": load_stats(),
            }
            self.send_json(data)

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self.send_json({"error": "Invalid JSON"}, 400)
            return

        if parsed.path == "/api/delete":
            filename = data.get("filename", "")
            if not filename or not filename.startswith("JTF-") or not filename.endswith(".json"):
                self.send_json({"error": "Invalid filename"}, 400)
                return
            # Prevent path traversal
            if "/" in filename or "\\" in filename:
                self.send_json({"error": "Invalid filename"}, 400)
                return
            if delete_file(filename):
                print(f"  Deleted: {filename}")
                self.send_json({"ok": True})
            else:
                self.send_json({"error": "File not found"}, 404)

        elif parsed.path == "/api/delete-suggestion":
            ref = data.get("ref", "")
            if not ref.startswith("JTF-"):
                self.send_json({"error": "Invalid ref"}, 400)
                return
            if delete_suggestion(ref):
                print(f"  Deleted suggestion: {ref}")
                self.send_json({"ok": True})
            else:
                self.send_json({"error": "Not found"}, 404)

        elif parsed.path == "/api/delete-bias":
            ref = data.get("ref", "")
            if not ref.startswith("JTF-"):
                self.send_json({"error": "Invalid ref"}, 400)
                return
            if delete_bias_report(ref):
                print(f"  Deleted bias report: {ref}")
                self.send_json({"ok": True})
            else:
                self.send_json({"error": "Not found"}, 404)

        else:
            self.send_json({"error": "Not found"}, 404)


def main():
    parser = argparse.ArgumentParser(description="JTF News Feedback Viewer (localhost only)")
    parser.add_argument("--port", type=int, default=8899, help="Port (default: 8899)")
    args = parser.parse_args()

    server = HTTPServer(("127.0.0.1", args.port), FeedbackHandler)
    print(f"\n  JTF Feedback Viewer")
    print(f"  http://127.0.0.1:{args.port}")
    print(f"  Localhost only — not accessible from network")
    print(f"  Press Ctrl+C to stop\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopped.")
        server.server_close()


if __name__ == "__main__":
    main()
