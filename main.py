#!/usr/bin/env python3
"""
JTF News - Just The Facts
=========================
Automated news stream that reports only verified facts.
No opinions. No adjectives. No interpretation.

This script runs continuously:
- Scrapes headlines from 20 news sources
- Uses Claude AI to extract pure facts
- Requires 2+ unrelated sources for verification
- Generates TTS audio via ElevenLabs
- Writes output files for OBS to display
- Archives daily to GitHub at midnight GMT
"""

from __future__ import annotations

import os
import sys
import json
import time
import gzip
import shutil
import hashlib
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import anthropic
from elevenlabs import ElevenLabs
from twilio.rest import Client as TwilioClient


# =============================================================================
# PYTHON 3.8 COMPATIBILITY
# =============================================================================

def indent_xml(elem, level=0, space="  "):
    """Add pretty-print indentation to XML (Python 3.8 compatible version of ET.indent)."""
    i = "\n" + level * space
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + space
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for child in elem:
            indent_xml(child, level + 1, space)
        if not child.tail or not child.tail.strip():
            child.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


# =============================================================================
# CONFIGURATION
# =============================================================================

# Load environment variables
load_dotenv()

# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
AUDIO_DIR = BASE_DIR / "audio"
ARCHIVE_DIR = BASE_DIR / "archive"
CONFIG_FILE = BASE_DIR / "config.json"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
AUDIO_DIR.mkdir(exist_ok=True)
ARCHIVE_DIR.mkdir(exist_ok=True)

# Load config
with open(CONFIG_FILE) as f:
    CONFIG = json.load(f)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger("jtf")

# Kill switch file
KILL_SWITCH = Path("/tmp/jtf-stop")

# =============================================================================
# CLAUDE AI - FACT EXTRACTION
# =============================================================================

FACT_EXTRACTION_PROMPT = """You are a fact extraction system for JTF News. Your ONLY job is to strip ALL editorialization, bias, and opinion from news headlines and return pure facts.

RULES:
1. Extract ONLY verifiable facts: what, where, when, how many
2. Remove ALL loaded language:
   - "brutal" → remove
   - "tragic" → remove
   - "shocking" → remove
   - "controversial" → remove
   - "failed" → remove unless objectively measurable
   - "active shooter" → "shooting reported"
   - "terrified" → remove
   - "slammed" → "criticized"
   - "historic" → remove unless objectively true
   - "orders" → "ruled" (for judicial actions - "orders" implies commanding authority; "ruled" is neutral legal terminology)
3. Remove ALL speculation and attribution of motive
4. Remove ALL adjectives that convey judgment
5. Keep numbers, locations, names, and actions
6. Use present tense for ongoing events
7. Maximum ONE sentence
8. If the headline contains NO verifiable facts, return "SKIP" for fact
9. OFFICIAL TITLES ONLY - Media nicknames are editorialization:
   - NEVER use media-invented nicknames: "czar", "kingpin", "maestro", "guru", "boss", etc.
   - "Czar" is NOT an official US government title - it's journalistic shorthand and is disrespectful
   - ALWAYS use the person's OFFICIAL government title + their name
   - Example: "border czar" → "White House Homeland Security Advisor [Full Name]" (use actual official title)
   - Example: "housing czar" → "Secretary of Housing [Full Name]" or their actual position
   - If you don't know the official title, describe the role: "the official responsible for border policy"
   - Format: "[Official Title] [Full Name]" - e.g., "Deputy Secretary Tom Homan", "Director Sarah Smith"
   - For well-known positions: "President Trump", "Senator Cruz", "Representative Crockett" (last name OK)
   - For lesser-known officials: Use full name to be informative: "Deputy Director John Smith"
   - NEVER use first name alone unless disambiguating two people with same last name
10. JUDGES: Always include full name AND court jurisdiction
   - Format: "Judge [Full Name] of the [Court Name]"
   - Example: "Judge Aileen Cannon of the U.S. District Court for the Southern District of Florida ruled..."
   - Example: "Chief Justice John Roberts of the U.S. Supreme Court ruled..."
   - Extract ALL judge information from the headline (name, court level, location, district)
   - If headline says "federal judge in Texas" → "A federal judge in Texas ruled..." (use what's available)
   - If headline has judge's name → Always include it with proper title
   - NEVER reduce specificity - if the source has the name/court, YOU must include it

NEWSWORTHINESS THRESHOLD:
A story is only newsworthy if it meets AT LEAST ONE of these criteria:
- Involves death or violent crime (shootings, murders, attacks, etc.)
- Affects 500 or more people directly
- Costs or invests at least $1 million USD (or equivalent)
- Changes a law or regulation
- Redraws a political border
- Major scientific or technological achievement (space launch, medical breakthrough, new discovery)
- Humanitarian milestone (aid delivered, rescue success, disaster relief)
- Official statements or actions by heads of state/government (Presidents, Prime Ministers, etc.)
- Major economic indicators (GDP, unemployment rates, inflation data, housing market reports)
- International agreements, treaties, or diplomatic actions between nations
If the story does NOT meet any threshold, set newsworthy to false.

OUTPUT FORMAT:
Return a JSON object with:
- "fact": The clean, factual sentence (or "SKIP" if no verifiable facts)
- "confidence": Your confidence percentage (0-100) that this is purely factual
- "newsworthy": true or false based on the threshold criteria above
- "threshold_met": Which threshold it meets (e.g., "death/violence", "500+ affected", "$1M+ cost/investment", "law change", "border change", "scientific achievement", "humanitarian milestone", "head of state", "economic indicator", "international diplomacy") or "none"

Headline to process:
"""


def extract_fact(headline: str) -> dict:
    """Send headline to Claude for fact extraction."""
    try:
        client = anthropic.Anthropic()

        response = client.messages.create(
            model=CONFIG["claude"]["model"],
            max_tokens=CONFIG["claude"]["max_tokens"],
            messages=[{
                "role": "user",
                "content": FACT_EXTRACTION_PROMPT + headline
            }]
        )

        text = response.content[0].text

        # Try standard JSON parsing first
        try:
            start = text.find('{')
            end = text.rfind('}') + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass

        # Fallback: Extract fields using regex (handles malformed JSON)
        fact_match = re.search(r'"fact"\s*:\s*"([^"]*(?:\\.[^"]*)*)"', text)
        conf_match = re.search(r'"confidence"\s*:\s*(\d+)', text)

        if fact_match:
            fact = fact_match.group(1).replace('\\"', '"')
            confidence = int(conf_match.group(1)) if conf_match else 85
            return {"fact": fact, "confidence": confidence, "removed": []}

        return {"fact": "SKIP", "confidence": 0, "removed": []}

    except Exception as e:
        log.error(f"Claude API error: {e}")
        return {"fact": "SKIP", "confidence": 0, "removed": [], "error": str(e)}


# =============================================================================
# JUDGE LOOKUP - Enhance facts with full judge name and court
# =============================================================================

# Patterns that indicate incomplete judge references
INCOMPLETE_JUDGE_PATTERNS = [
    r'\b[Aa] federal judge\b',
    r'\b[Aa] judge\b',
    r'\b[Tt]he judge\b',
    r'\bJudge [A-Z][a-z]+\b(?! of)',  # "Judge Smith" without "of [Court]"
    r'\b[Ff]ederal court\b(?! for)',   # "federal court" without location
]

# Pattern to detect complete judge references (no lookup needed)
COMPLETE_JUDGE_PATTERN = r'Judge [A-Z][a-z]+ [A-Z][a-z]+ of (the |)[A-Z]'


def needs_judge_lookup(fact: str) -> bool:
    """Check if fact mentions a judge without full name/court details."""
    # First check if it has a complete reference already
    if re.search(COMPLETE_JUDGE_PATTERN, fact):
        return False

    # Check for incomplete patterns
    for pattern in INCOMPLETE_JUDGE_PATTERNS:
        if re.search(pattern, fact):
            return True

    return False


def search_judge_info(fact: str, original_headline: str) -> dict | None:
    """Search for judge information using web search.

    Returns dict with 'full_name' and 'court' if found, None otherwise.
    """
    try:
        # Build search query from the fact
        # Extract key terms that might help identify the judge
        search_terms = []

        # Look for case-related terms
        if 'immigration' in fact.lower():
            search_terms.append('immigration')
        if 'abortion' in fact.lower():
            search_terms.append('abortion')
        if 'gun' in fact.lower() or 'firearm' in fact.lower():
            search_terms.append('gun')
        if 'trump' in fact.lower():
            search_terms.append('trump')
        if 'biden' in fact.lower():
            search_terms.append('biden')

        # Look for location hints
        location_match = re.search(r'in ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', fact)
        if location_match:
            search_terms.append(location_match.group(1))

        # Build query
        query = f"federal judge {' '.join(search_terms)} ruling 2026"

        # Use DuckDuckGo HTML search (no API needed)
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }

        search_url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
        response = requests.get(search_url, headers=headers, timeout=10)

        if response.status_code != 200:
            log.debug(f"Judge search failed: HTTP {response.status_code}")
            return None

        # Parse search results
        soup = BeautifulSoup(response.text, 'html.parser')
        results_text = soup.get_text()[:3000]  # First 3000 chars of results

        # Use Claude to extract judge info from search results
        client = anthropic.Anthropic()

        prompt = f"""From these search results, extract the judge's information for this news story.

NEWS STORY: {fact}
ORIGINAL HEADLINE: {original_headline}

SEARCH RESULTS:
{results_text}

Find the specific federal judge involved in this ruling/case.

Return JSON with:
- "full_name": The judge's full name (e.g., "Aileen Cannon", "Matthew Kacsmaryk")
- "court": The full court name (e.g., "U.S. District Court for the Southern District of Florida")
- "found": true if you found a specific judge, false if not found or uncertain

Only return a judge if you're confident they are the one in this specific news story.
If you cannot determine the specific judge, return {{"found": false}}"""

        response = client.messages.create(
            model=CONFIG["claude"]["model"],
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )

        result_text = response.content[0].text

        # Parse JSON from response
        try:
            start = result_text.find('{')
            end = result_text.rfind('}') + 1
            if start >= 0 and end > start:
                result = json.loads(result_text[start:end])
                if result.get("found") and result.get("full_name") and result.get("court"):
                    log.info(f"Found judge: {result['full_name']} of {result['court']}")
                    return result
        except json.JSONDecodeError:
            pass

        return None

    except Exception as e:
        log.debug(f"Judge search error: {e}")
        return None


def enhance_fact_with_judge(fact: str, judge_info: dict) -> str:
    """Replace incomplete judge reference with full name and court."""
    full_name = judge_info["full_name"]
    court = judge_info["court"]

    # Build the replacement text
    replacement = f"Judge {full_name} of the {court}"

    # Replace various incomplete patterns
    replacements = [
        (r'\b[Aa] federal judge\b', replacement),
        (r'\b[Aa] judge\b', replacement),
        (r'\b[Tt]he judge\b', replacement),
        (r'\bJudge ([A-Z][a-z]+)\b(?! of)', f"Judge {full_name} of the {court}"),
    ]

    enhanced = fact
    for pattern, repl in replacements:
        enhanced = re.sub(pattern, repl, enhanced, count=1)
        if enhanced != fact:
            break  # Only replace first match

    return enhanced


# =============================================================================
# WEB SCRAPING
# =============================================================================

# Cache for robots.txt parsers (avoid re-fetching every cycle)
_robots_cache = {}  # domain -> (RobotFileParser, timestamp)
ROBOTS_CACHE_TTL = 3600  # 1 hour

USER_AGENT = "JTFNews/1.0"


def can_fetch_url(url: str) -> bool:
    """Check if we're allowed to fetch this URL per robots.txt."""
    try:
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        robots_url = f"{domain}/robots.txt"

        now = time.time()

        # Check cache
        if domain in _robots_cache:
            parser, cached_time = _robots_cache[domain]
            if now - cached_time < ROBOTS_CACHE_TTL:
                allowed = parser.can_fetch(USER_AGENT, url)
                if not allowed:
                    log.debug(f"robots.txt blocks: {url}")
                return allowed

        # Fetch and parse robots.txt
        parser = RobotFileParser()
        parser.set_url(robots_url)
        try:
            parser.read()
        except Exception as e:
            # If robots.txt doesn't exist or errors, assume allowed
            log.debug(f"No robots.txt for {domain}: {e}")
            # Create permissive parser
            parser = RobotFileParser()
            parser.allow_all = True

        # Cache it
        _robots_cache[domain] = (parser, now)

        allowed = parser.can_fetch(USER_AGENT, url)
        if not allowed:
            log.warning(f"robots.txt blocks: {url}")
        return allowed

    except Exception as e:
        log.debug(f"robots.txt check failed for {url}: {e}")
        return True  # Allow on error (fail open)


def fetch_rss_headlines(source: dict) -> list:
    """Fetch headlines from an RSS feed."""
    headlines = []
    rss_url = source.get("rss")

    if not rss_url:
        return []

    try:
        headers = {
            "User-Agent": f"{USER_AGENT} (Facts only, no opinions; RSS reader)"
        }

        response = requests.get(rss_url, headers=headers, timeout=15)
        response.raise_for_status()

        # Parse RSS XML
        root = ET.fromstring(response.content)

        # RSS feeds have items under channel, Atom feeds have entry elements
        items = root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry')

        for item in items[:10]:  # Limit to first 10 headlines
            # Try RSS format first, then Atom format
            title = item.find('title')
            if title is None:
                title = item.find('{http://www.w3.org/2005/Atom}title')

            if title is not None and title.text:
                text = title.text.strip()
                if len(text) > 20:  # Skip very short items
                    headlines.append({
                        "text": text,
                        "source_id": source["id"],
                        "source_name": source["name"],
                        "source_rating": source["ratings"]["accuracy"],
                        "owner": source["owner"],
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })

        if headlines:
            log.info(f"Fetched {len(headlines)} headlines from {source['name']} (RSS)")

    except Exception as e:
        log.debug(f"RSS failed for {source['name']}: {e}")

    return headlines


def fetch_html_headlines(source: dict) -> list:
    """Fetch headlines by scraping HTML (respects robots.txt)."""
    headlines = []

    # Check robots.txt before scraping
    if not can_fetch_url(source["url"]):
        log.info(f"Skipping {source['name']} - robots.txt disallows")
        return []

    try:
        headers = {
            "User-Agent": f"{USER_AGENT} (Facts only, no opinions; respects robots.txt)"
        }

        response = requests.get(source["url"], headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Find headlines using configured selector
        elements = soup.select(source["scrape_selector"])

        for el in elements[:10]:  # Limit to first 10 headlines
            text = el.get_text(strip=True)
            if text and len(text) > 20:  # Skip very short items
                headlines.append({
                    "text": text,
                    "source_id": source["id"],
                    "source_name": source["name"],
                    "source_rating": source["ratings"]["accuracy"],
                    "owner": source["owner"],
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })

        if headlines:
            log.info(f"Fetched {len(headlines)} headlines from {source['name']} (HTML)")

    except Exception as e:
        log.warning(f"Failed to fetch from {source['name']}: {e}")

    return headlines


def fetch_headlines(source: dict) -> list:
    """Fetch headlines from a news source. Tries RSS first, falls back to HTML."""
    # Try RSS first (more reliable, designed for machine consumption)
    headlines = fetch_rss_headlines(source)

    # Fall back to HTML scraping if RSS didn't work
    if not headlines:
        headlines = fetch_html_headlines(source)

    return headlines


def scrape_all_sources() -> list:
    """Scrape headlines from all configured sources."""
    all_headlines = []

    for source in CONFIG["sources"]:
        headlines = fetch_headlines(source)
        all_headlines.extend(headlines)
        time.sleep(1)  # Be polite between requests

    return all_headlines


# =============================================================================
# VERIFICATION
# =============================================================================

def get_story_hash(text: str) -> str:
    """Generate hash of story text for deduplication."""
    return hashlib.md5(text.lower().encode()).hexdigest()[:12]


def are_sources_unrelated(source1_id: str, source2_id: str) -> bool:
    """Check if two sources are unrelated (different owners)."""
    sources = {s["id"]: s for s in CONFIG["sources"]}

    s1 = sources.get(source1_id)
    s2 = sources.get(source2_id)

    if not s1 or not s2:
        return False

    # Same owner = related
    if s1["owner"] == s2["owner"]:
        return False

    # Check institutional holder overlap
    holders1 = {h["name"] for h in s1.get("institutional_holders", [])}
    holders2 = {h["name"] for h in s2.get("institutional_holders", [])}

    shared = holders1 & holders2
    if len(shared) >= CONFIG["unrelated_rules"]["max_shared_top_holders"]:
        return False

    return True


def has_word_overlap(fact1: str, fact2: str, threshold: float = 0.15) -> bool:
    """Quick check if two facts share enough words to possibly be related.

    Returns True if at least threshold% of words overlap.
    This is a cheap pre-filter before calling Claude.
    """
    # Extract meaningful words (3+ chars, lowercase)
    words1 = set(w.lower() for w in fact1.split() if len(w) >= 3)
    words2 = set(w.lower() for w in fact2.split() if len(w) >= 3)

    if not words1 or not words2:
        return False

    shared = words1 & words2
    min_len = min(len(words1), len(words2))

    return len(shared) >= min_len * threshold


def find_matching_stories(fact: str, queue: list) -> list:
    """Find stories in queue that match this fact (same core event).

    Pre-filters with word overlap, then uses single Claude call for candidates.
    """
    if not queue:
        return []

    # Pre-filter: only check items with some word overlap (saves API calls)
    candidates = [item for item in queue if has_word_overlap(fact, item["fact"])]

    if not candidates:
        return []

    log.info(f"Word overlap pre-filter: {len(candidates)}/{len(queue)} candidates")

    try:
        client = anthropic.Anthropic()

        # Build numbered list of candidate facts
        queue_list = "\n".join([f"{i+1}. {item['fact']}" for i, item in enumerate(candidates)])

        prompt = f"""Compare this new fact against the numbered list below.
Return ONLY the numbers of facts that describe the SAME EVENT as the new fact.
Same event means: same incident, same person doing same action, same announcement.
Details like death counts or exact wording may differ.

New fact: {fact}

Existing facts:
{queue_list}

Reply with ONLY comma-separated numbers (e.g., "1,3,5") or "NONE" if no matches."""

        response = client.messages.create(
            model=CONFIG["claude"]["model"],
            max_tokens=50,
            messages=[{"role": "user", "content": prompt}]
        )

        answer = response.content[0].text.strip().upper()

        if answer == "NONE" or not answer:
            return []

        # Parse the numbers (referencing candidates list)
        matches = []
        for num_str in answer.replace(" ", "").split(","):
            try:
                idx = int(num_str) - 1  # Convert to 0-indexed
                if 0 <= idx < len(candidates):
                    matches.append(candidates[idx])
            except ValueError:
                continue

        return matches

    except Exception as e:
        log.error(f"Claude batch matching error: {e}")
        return []


def is_duplicate_batch(fact: str, published: list) -> bool:
    """Check if fact matches any published story using a single Claude call."""
    if not published:
        return False

    # Pre-filter: only check stories with word overlap
    candidates = [p for p in published if has_word_overlap(fact, p)]

    if not candidates:
        return False  # No overlap = definitely not a duplicate

    try:
        client = anthropic.Anthropic()

        # Build numbered list of candidate published facts
        pub_list = "\n".join([f"{i+1}. {p}" for i, p in enumerate(candidates)])

        prompt = f"""Does this new fact describe the SAME EVENT as any fact in the list below?
Same event means: same incident, same person doing same action, same announcement.
Details like death counts or exact wording may differ.

New fact: {fact}

Published facts:
{pub_list}

Reply with ONLY "YES" or "NO"."""

        response = client.messages.create(
            model=CONFIG["claude"]["model"],
            max_tokens=10,
            messages=[{"role": "user", "content": prompt}]
        )

        answer = response.content[0].text.strip().upper()
        if answer == "YES":
            log.info(f"Duplicate (Claude batch): '{fact[:40]}...'")
            return True
        return False

    except Exception as e:
        log.error(f"Claude duplicate check error: {e}")
        return False


# =============================================================================
# LEARNED RATINGS SYSTEM
# =============================================================================

def load_learned_ratings() -> dict:
    """Load learned ratings from file. Returns dict of source_id -> stats."""
    ratings_file = DATA_DIR / "learned_ratings.json"
    if ratings_file.exists():
        with open(ratings_file) as f:
            return json.load(f)
    return {}


def save_learned_ratings(ratings: dict):
    """Save learned ratings to file."""
    ratings_file = DATA_DIR / "learned_ratings.json"
    with open(ratings_file, 'w') as f:
        json.dump(ratings, f, indent=2)


def append_audit_log(source_id: str, event: str, fact_hash: str, extra: dict = None):
    """Append audit entry to ratings audit trail. One JSON line per event.

    This creates a legally defensible record of all rating calculations.
    Each line is an independent JSON object (JSONL format).
    """
    audit_file = DATA_DIR / "ratings_audit.jsonl"
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_id": source_id,
        "event": event,
        "fact_hash": fact_hash,
        **(extra or {})
    }
    with open(audit_file, 'a') as f:
        f.write(json.dumps(entry) + '\n')


def record_verification_success(source_id: str, fact_hash: str = None):
    """Record that a source's story was successfully verified."""
    ratings = load_learned_ratings()

    if source_id not in ratings:
        ratings[source_id] = {"successes": 0, "failures": 0}

    ratings[source_id]["successes"] += 1
    save_learned_ratings(ratings)

    # Audit trail for legal defensibility
    if fact_hash:
        append_audit_log(source_id, "success", fact_hash)

    log.info(f"Rating +1 success for {source_id}: {ratings[source_id]}")


def record_verification_failure(source_id: str, fact_hash: str = None):
    """Record that a source's story expired without verification."""
    ratings = load_learned_ratings()

    if source_id not in ratings:
        ratings[source_id] = {"successes": 0, "failures": 0}

    ratings[source_id]["failures"] += 1
    save_learned_ratings(ratings)

    # Audit trail for legal defensibility
    if fact_hash:
        append_audit_log(source_id, "failure", fact_hash)

    log.info(f"Rating +1 failure for {source_id}: {ratings[source_id]}")


def get_learned_rating(source_id: str) -> float:
    """Get the learned accuracy rating for a source (0-10 scale).

    Formula: (successes / (successes + failures)) * 10
    Returns default config rating if no data yet.
    """
    ratings = load_learned_ratings()

    if source_id not in ratings:
        # Return default from config
        for source in CONFIG["sources"]:
            if source["id"] == source_id:
                return source["ratings"]["accuracy"]
        return 5.0  # Fallback

    stats = ratings[source_id]
    total = stats["successes"] + stats["failures"]

    if total < 5:
        # Not enough data yet, blend with default
        for source in CONFIG["sources"]:
            if source["id"] == source_id:
                default = source["ratings"]["accuracy"]
                learned = (stats["successes"] / total) * 10 if total > 0 else default
                # Weight: more data = more weight on learned rating
                weight = total / 5
                return default * (1 - weight) + learned * weight
        return 5.0

    # Enough data, use learned rating
    return (stats["successes"] / total) * 10


def get_display_rating(source_id: str) -> str:
    """Get rating with evidence indicator for display.

    Display format based on data points:
    - 0 data points: "9.6*" (asterisk = using editorial baseline)
    - 1-9 data points: "8.5* (3/10)" (cold start, showing evidence)
    - 10+ data points: "9.4 (47/50)" (mature, evidence-based)
    """
    ratings = load_learned_ratings()

    # Get default rating from config
    default_rating = 5.0
    for source in CONFIG["sources"]:
        if source["id"] == source_id:
            default_rating = source["ratings"]["accuracy"]
            break

    if source_id not in ratings:
        # No data - show default with asterisk
        return f"{default_rating}*"

    stats = ratings[source_id]
    successes = stats["successes"]
    failures = stats["failures"]
    total = successes + failures

    if total == 0:
        # No data - show default with asterisk
        return f"{default_rating}*"

    if total < 10:
        # Cold start - blend default with learned, show asterisk and evidence
        learned = (successes / total) * 10
        weight = total / 10  # Gradual transition to learned rating
        blended = default_rating * (1 - weight) + learned * weight
        return f"{blended:.1f}* ({successes}/{total})"

    # Mature - use pure learned rating with evidence
    rating = (successes / total) * 10
    return f"{rating:.1f} ({successes}/{total})"


# =============================================================================
# QUEUE MANAGEMENT
# =============================================================================

def load_queue() -> list:
    """Load the story queue from file."""
    queue_file = DATA_DIR / "queue.json"
    if queue_file.exists():
        with open(queue_file) as f:
            return json.load(f)
    return []


def save_queue(queue: list):
    """Save the story queue to file."""
    queue_file = DATA_DIR / "queue.json"
    with open(queue_file, 'w') as f:
        json.dump(queue, f, indent=2)


def clean_expired_queue(queue: list) -> list:
    """Remove stories older than queue_timeout_hours from queue. Records failures for ratings."""
    timeout_hours = CONFIG["thresholds"]["queue_timeout_hours"]
    cutoff = datetime.now(timezone.utc).timestamp() - (timeout_hours * 3600)

    cleaned = []
    for item in queue:
        item_time = datetime.fromisoformat(item["timestamp"]).timestamp()
        if item_time > cutoff:
            cleaned.append(item)
        else:
            log.info(f"Expired from queue: {item['fact'][:50]}...")
            # Record failure for ratings learning - story wasn't verified
            fact_hash = get_story_hash(item["fact"])
            record_verification_failure(item["source_id"], fact_hash)

    return cleaned


# =============================================================================
# DUPLICATE DETECTION
# =============================================================================

def load_shown_hashes() -> set:
    """Load hashes of stories shown today."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    hash_file = DATA_DIR / f"shown_{today}.txt"

    if hash_file.exists():
        with open(hash_file) as f:
            return set(line.strip() for line in f if line.strip())
    return set()


def add_shown_hash(story_hash: str):
    """Add a hash to today's shown list."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    hash_file = DATA_DIR / f"shown_{today}.txt"

    with open(hash_file, 'a') as f:
        f.write(story_hash + '\n')


def load_published_stories() -> list:
    """Load today's published stories from stories.json."""
    stories_file = DATA_DIR / "stories.json"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if stories_file.exists():
        try:
            with open(stories_file) as f:
                data = json.load(f)
            if data.get("date") == today:
                return [s["fact"] for s in data.get("stories", [])]
        except:
            pass
    return []


def is_duplicate(fact: str) -> bool:
    """Check if this fact matches any story already published today.

    Uses fast hash check first, then single Claude call for semantic matching.
    """
    # Fast path: exact text match via hash
    story_hash = get_story_hash(fact)
    shown = load_shown_hashes()
    if story_hash in shown:
        return True

    # Semantic check: single Claude call to check against all published stories
    published = load_published_stories()
    return is_duplicate_batch(fact, published)


# =============================================================================
# HEADLINE CACHE (Skip already-processed headlines to save API costs)
# =============================================================================

def load_processed_headlines() -> set:
    """Load hashes of headlines already sent to Claude today."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cache_file = DATA_DIR / f"processed_{today}.txt"

    if cache_file.exists():
        with open(cache_file) as f:
            return set(line.strip() for line in f if line.strip())
    return set()


def add_processed_headline(headline_hash: str):
    """Mark a headline as processed."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cache_file = DATA_DIR / f"processed_{today}.txt"

    with open(cache_file, 'a') as f:
        f.write(headline_hash + '\n')


def is_headline_processed(headline_text: str, processed_cache: set) -> bool:
    """Check if we've already sent this headline to Claude."""
    headline_hash = get_story_hash(headline_text)
    return headline_hash in processed_cache


# =============================================================================
# TEXT-TO-SPEECH
# =============================================================================

def get_next_audio_index() -> int:
    """Get the next audio file index based on today's stories."""
    stories_file = DATA_DIR / "stories.json"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if stories_file.exists():
        try:
            with open(stories_file) as f:
                stories = json.load(f)
            if stories.get("date") == today:
                return len(stories.get("stories", []))
        except:
            pass
    return 0


def generate_tts(text: str, audio_index: int = None) -> str:
    """Generate TTS audio using ElevenLabs. Returns audio filename."""
    try:
        client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

        # Generate audio using the new client API
        audio_generator = client.text_to_speech.convert(
            voice_id=os.getenv("ELEVENLABS_VOICE_ID"),
            text=text,
            model_id="eleven_multilingual_v2",
            voice_settings={
                "stability": 0.7,
                "similarity_boost": 0.8,
                "style": 0.3,
                "use_speaker_boost": True
            }
        )

        # Collect audio data
        audio_data = b''.join(chunk for chunk in audio_generator)

        # Save to indexed file for loop playback
        if audio_index is not None:
            indexed_path = AUDIO_DIR / f"audio_{audio_index}.mp3"
            with open(indexed_path, 'wb') as f:
                f.write(audio_data)

        # Also save to current.mp3 for immediate playback
        current_path = AUDIO_DIR / "current.mp3"
        with open(current_path, 'wb') as f:
            f.write(audio_data)

        log.info(f"Generated TTS: {text[:50]}...")
        return f"audio_{audio_index}.mp3" if audio_index is not None else "current.mp3"

    except Exception as e:
        log.error(f"TTS error: {e}")
        return False


# =============================================================================
# OUTPUT FILES
# =============================================================================

def write_current_story(fact: str, sources: list):
    """Write the current story to output files."""
    # Format source attribution with evidence-based ratings
    source_text = " | ".join([
        f"{s['source_name']} - {get_display_rating(s['source_id'])}"
        for s in sources[:2]
    ])

    # Write current story
    with open(DATA_DIR / "current.txt", 'w') as f:
        f.write(fact)

    # Write source attribution
    with open(DATA_DIR / "source.txt", 'w') as f:
        f.write(source_text)

    log.info(f"Published: {fact[:50]}...")


def append_daily_log(fact: str, sources: list, audio_file: str = None):
    """Append story to daily log."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = DATA_DIR / f"{today}.txt"

    timestamp = datetime.now(timezone.utc).isoformat()
    source_names = ",".join([s["source_name"] for s in sources[:2]])
    source_scores = ",".join([get_display_rating(s["source_id"]) for s in sources[:2]])

    line = f"{timestamp}|{source_names}|{source_scores}|{fact}\n"

    # Create header if new file
    if not log_file.exists():
        with open(log_file, 'w') as f:
            f.write(f"# JTF News Daily Log\n")
            f.write(f"# Date: {today}\n")
            f.write(f"# Generated: UTC\n\n")

    with open(log_file, 'a') as f:
        f.write(line)

    # Also update stories.json for JS loop
    update_stories_json(fact, sources, audio_file)


def update_stories_json(fact: str, sources: list, audio_file: str = None):
    """Update stories.json for the JS loop display."""
    stories_file = DATA_DIR / "stories.json"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Load existing stories
    stories = {"date": today, "stories": []}
    if stories_file.exists():
        try:
            with open(stories_file) as f:
                stories = json.load(f)
            # Reset if it's a new day
            if stories.get("date") != today:
                stories = {"date": today, "stories": []}
        except:
            pass

    # Format source info with evidence-based ratings
    source_text = " | ".join([
        f"{s['source_name']} - {get_display_rating(s['source_id'])}"
        for s in sources[:2]
    ])

    # Add new story with cached audio file
    stories["stories"].append({
        "fact": fact,
        "source": source_text,
        "audio": f"../audio/{audio_file}" if audio_file else "../audio/current.mp3"
    })

    # Write back
    with open(stories_file, 'w') as f:
        json.dump(stories, f, indent=2)

    # Update RSS feed
    update_rss_feed(fact, sources)

    # Update Alexa Flash Briefing feed
    update_alexa_feed(fact, sources)


def update_rss_feed(fact: str, sources: list):
    """Update RSS feed with new story and push to gh-pages."""
    import subprocess

    gh_pages_dir = BASE_DIR / "gh-pages-dist"
    feed_file = gh_pages_dir / "feed.xml"
    max_items = 50  # Keep last 50 stories in feed

    # Check if gh-pages worktree exists
    if not gh_pages_dir.exists():
        log.warning("gh-pages-dist worktree not found, skipping RSS update")
        return

    # Format source attribution
    source_text = ", ".join([s['source_name'] for s in sources[:2]])

    # Create new item
    pub_date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    guid = hashlib.md5(f"{fact}{pub_date}".encode()).hexdigest()[:12]

    # Truncate fact for title (first 80 chars)
    title = fact[:80] + "..." if len(fact) > 80 else fact

    new_item = {
        "title": title,
        "description": fact,
        "source": source_text,
        "pubDate": pub_date,
        "guid": guid
    }

    # Load existing items or create new
    items = []
    if feed_file.exists():
        try:
            tree = ET.parse(feed_file)
            root = tree.getroot()
            channel = root.find("channel")
            for item in channel.findall("item"):
                items.append({
                    "title": item.find("title").text or "",
                    "description": item.find("description").text or "",
                    "source": item.find("source").text if item.find("source") is not None else "",
                    "pubDate": item.find("pubDate").text or "",
                    "guid": item.find("guid").text or ""
                })
        except:
            pass

    # Add new item at beginning
    items.insert(0, new_item)

    # Trim to max items
    items = items[:max_items]

    # Build RSS XML
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")

    ET.SubElement(channel, "title").text = "JTF News - Just The Facts"
    ET.SubElement(channel, "link").text = "https://larryseyer.github.io/jtfnews/"
    ET.SubElement(channel, "description").text = "Verified facts from multiple sources. No opinions. No adjectives. No interpretation."
    ET.SubElement(channel, "language").text = "en-us"
    ET.SubElement(channel, "lastBuildDate").text = pub_date

    for item_data in items:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = item_data["title"]
        ET.SubElement(item, "description").text = item_data["description"]
        ET.SubElement(item, "source").text = item_data["source"]
        ET.SubElement(item, "pubDate").text = item_data["pubDate"]
        ET.SubElement(item, "guid", isPermaLink="false").text = item_data["guid"]

    # Write with XML declaration (use custom indent for Python 3.8 compatibility)
    indent_xml(rss, space="  ")
    tree = ET.ElementTree(rss)
    with open(feed_file, 'wb') as f:
        tree.write(f, encoding="utf-8", xml_declaration=True)

    log.info(f"RSS feed updated: {len(items)} items")

    # Commit and push to gh-pages
    try:
        subprocess.run(
            ["git", "add", "feed.xml"],
            cwd=gh_pages_dir,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", f"Update feed: {title[:50]}"],
            cwd=gh_pages_dir,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "push"],
            cwd=gh_pages_dir,
            check=True,
            capture_output=True
        )
        log.info("RSS feed pushed to gh-pages")
    except subprocess.CalledProcessError as e:
        log.warning(f"Failed to push RSS feed: {e}")


def update_alexa_feed(fact: str, sources: list):
    """Update Alexa Flash Briefing JSON feed and push to gh-pages."""
    import subprocess

    gh_pages_dir = BASE_DIR / "gh-pages-dist"
    alexa_file = gh_pages_dir / "alexa.json"
    max_items = 5  # Alexa typically reads top few items

    # Check if gh-pages worktree exists
    if not gh_pages_dir.exists():
        log.warning("gh-pages-dist worktree not found, skipping Alexa feed update")
        return

    # Format source attribution
    source_text = ", ".join([s['source_name'] for s in sources[:2]])

    # Create new item in Alexa Flash Briefing format
    update_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.0Z")
    uid = hashlib.md5(f"{fact}{update_date}".encode()).hexdigest()

    new_item = {
        "uid": uid,
        "updateDate": update_date,
        "titleText": f"JTF News: {source_text}",
        "mainText": fact,
        "redirectionUrl": "https://larryseyer.github.io/jtfnews/"
    }

    # Load existing items or create new list
    items = []
    if alexa_file.exists():
        try:
            with open(alexa_file) as f:
                items = json.load(f)
        except:
            pass

    # Add new item at beginning
    items.insert(0, new_item)

    # Trim to max items
    items = items[:max_items]

    # Write JSON
    with open(alexa_file, 'w') as f:
        json.dump(items, f, indent=2)

    log.info(f"Alexa feed updated: {len(items)} items")

    # Commit and push to gh-pages (batch with RSS if possible)
    try:
        subprocess.run(
            ["git", "add", "alexa.json"],
            cwd=gh_pages_dir,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", f"Update Alexa feed"],
            cwd=gh_pages_dir,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "push"],
            cwd=gh_pages_dir,
            check=True,
            capture_output=True
        )
        log.info("Alexa feed pushed to gh-pages")
    except subprocess.CalledProcessError as e:
        log.warning(f"Failed to push Alexa feed: {e}")


# =============================================================================
# ALERTS
# =============================================================================

def send_alert(message: str):
    """Send SMS alert via Twilio."""
    try:
        client = TwilioClient(
            os.getenv("TWILIO_ACCOUNT_SID"),
            os.getenv("TWILIO_AUTH_TOKEN")
        )

        client.messages.create(
            body=f"JTF: {message}",
            from_=os.getenv("TWILIO_PHONE_NUMBER"),
            to=os.getenv("ALERT_PHONE_NUMBER")
        )

        log.warning(f"Alert sent: {message}")

    except Exception as e:
        log.error(f"Failed to send alert: {e}")


# =============================================================================
# STREAM MONITORING
# =============================================================================

HEARTBEAT_FILE = DATA_DIR / "heartbeat.txt"
STREAM_OFFLINE_THRESHOLD = 300  # 5 minutes in seconds
_offline_alert_sent = False  # Only ONE alert per offline event


def write_heartbeat():
    """Write current timestamp to heartbeat file."""
    try:
        with open(HEARTBEAT_FILE, 'w') as f:
            f.write(str(time.time()))
    except Exception as e:
        log.error(f"Failed to write heartbeat: {e}")


def check_stream_health():
    """Check if stream appears offline (no heartbeat in 5 minutes).

    Sends ONE alert when stream goes offline. Resets only when stream comes back.
    """
    global _offline_alert_sent

    if not HEARTBEAT_FILE.exists():
        return  # First run, no heartbeat yet

    try:
        with open(HEARTBEAT_FILE) as f:
            last_beat = float(f.read().strip())

        now = time.time()
        offline_duration = now - last_beat

        if offline_duration > STREAM_OFFLINE_THRESHOLD:
            # Stream is offline - send ONE alert only
            if not _offline_alert_sent:
                minutes_offline = int(offline_duration / 60)
                send_alert(f"Stream offline {minutes_offline}+ min")
                _offline_alert_sent = True
                log.warning(f"Stream offline for {minutes_offline} minutes - alert sent")
        else:
            # Stream is online - reset alert flag so we can alert if it goes offline again
            if _offline_alert_sent:
                log.info("Stream back online - alert flag reset")
            _offline_alert_sent = False
    except Exception as e:
        log.debug(f"Heartbeat check failed: {e}")


# =============================================================================
# CONTRADICTION DETECTION
# =============================================================================

def get_recent_facts(hours: int = 24) -> list:
    """Get facts published in the last N hours."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = DATA_DIR / f"{today}.txt"

    facts = []
    if log_file.exists():
        with open(log_file) as f:
            for line in f:
                if line.startswith("#") or not line.strip():
                    continue
                parts = line.strip().split("|")
                if len(parts) >= 4:
                    facts.append(parts[3].strip())

    return facts[-20:]  # Last 20 facts max


def check_contradiction(new_fact: str, recent_facts: list) -> bool:
    """Use Claude to check if new fact contradicts recent facts."""
    if not recent_facts:
        return False

    # Only check against last 5 facts to save tokens
    check_facts = recent_facts[-5:]

    prompt = f"""Check if this NEW FACT contradicts any of the RECENT FACTS below.

NEW FACT: {new_fact}

RECENT FACTS:
{chr(10).join(f'- {f}' for f in check_facts)}

A contradiction means the facts cannot both be true (e.g., "5 dead" vs "3 dead" for same event).
Minor updates or additions are NOT contradictions.

Return JSON: {{"contradiction": true/false, "reason": "brief explanation if true"}}"""

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=CONFIG["claude"]["model"],
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}]
        )

        result = json.loads(response.content[0].text)

        if result.get("contradiction"):
            log.warning(f"Contradiction detected: {result.get('reason', 'unknown')}")
            return True

        return False

    except Exception as e:
        log.error(f"Contradiction check failed: {e}")
        return False  # Don't block on error


# =============================================================================
# BREAKING NEWS UPDATES (3rd+ source details)
# =============================================================================

def find_matching_published_story(new_fact: str) -> dict | None:
    """Check if new fact matches any already-published story today."""
    stories_file = DATA_DIR / "stories.json"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if not stories_file.exists():
        return None

    try:
        with open(stories_file) as f:
            data = json.load(f)

        if data.get("date") != today:
            return None

        # Use same word overlap filter as queue matching
        new_words = set(new_fact.lower().split())

        for idx, story in enumerate(data.get("stories", [])):
            existing_fact = story.get("fact", "")
            existing_words = set(existing_fact.lower().split())

            # Check for significant word overlap (same event)
            overlap = len(new_words & existing_words)
            min_len = min(len(new_words), len(existing_words))

            if min_len > 0 and overlap / min_len > 0.3:
                # Potential match - return story with index
                story["_index"] = idx
                return story

        return None

    except Exception as e:
        log.debug(f"Published story match check failed: {e}")
        return None


def extract_new_details(new_fact: str, existing_fact: str) -> str | None:
    """Use Claude to extract only NEW information from the new fact."""
    prompt = f"""Compare these two news facts about the SAME event.

EXISTING (already published): {existing_fact}

NEW SOURCE: {new_fact}

Extract ONLY genuinely new, verifiable information from NEW SOURCE that is NOT already in EXISTING.
Do NOT include anything already stated or implied in EXISTING.
Do NOT rephrase existing information.

If there is genuinely new information, return it as a short factual sentence.
If there is NO new information, return exactly: NO_NEW_INFO

Return JSON: {{"new_detail": "the new sentence" or "NO_NEW_INFO"}}"""

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=CONFIG["claude"]["model"],
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}]
        )

        result = json.loads(response.content[0].text)
        new_detail = result.get("new_detail", "NO_NEW_INFO")

        if new_detail == "NO_NEW_INFO" or not new_detail:
            return None

        return new_detail

    except Exception as e:
        log.error(f"Extract new details failed: {e}")
        return None


def update_published_story(story_index: int, additional_detail: str, new_source: dict):
    """Append new detail to an already-published story."""
    stories_file = DATA_DIR / "stories.json"

    try:
        with open(stories_file) as f:
            data = json.load(f)

        if story_index >= len(data.get("stories", [])):
            return False

        story = data["stories"][story_index]
        old_fact = story["fact"]

        # Append new detail as separate sentence
        updated_fact = f"{old_fact} {additional_detail}"
        story["fact"] = updated_fact

        # Add new source to attribution
        new_source_text = f"{new_source['source_name']} - {get_display_rating(new_source['source_id'])}"
        if new_source_text not in story.get("source", ""):
            story["source"] = f"{story['source']} | {new_source_text}"

        # Regenerate audio for updated fact
        audio_path = story.get("audio", "").replace("../audio/", "")
        if audio_path:
            audio_index = audio_path.replace("audio_", "").replace(".mp3", "")
            try:
                audio_index = int(audio_index)
                generate_tts(updated_fact, audio_index)
            except:
                pass

        # Write back
        with open(stories_file, 'w') as f:
            json.dump(data, f, indent=2)

        log.info(f"UPDATED story: +'{additional_detail}' from {new_source['source_name']}")
        return True

    except Exception as e:
        log.error(f"Failed to update published story: {e}")
        return False


# =============================================================================
# CLEANUP
# =============================================================================

def cleanup_old_data(days: int = 7):
    """Delete raw data files older than N days."""
    import glob
    from datetime import timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_str = cutoff.strftime("%Y-%m-%d")

    deleted = 0

    # Find dated files in data directory
    for pattern in ["*.txt", "*.json"]:
        for filepath in DATA_DIR.glob(pattern):
            filename = filepath.name

            # Skip non-dated files
            if not any(c.isdigit() for c in filename):
                continue

            # Extract date from filename (e.g., 2026-02-11.txt, processed_2026-02-11.txt)
            try:
                # Find date pattern in filename
                match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
                if match:
                    file_date = match.group(1)
                    if file_date < cutoff_str:
                        filepath.unlink()
                        deleted += 1
                        log.info(f"Deleted old file: {filename}")
            except Exception as e:
                log.error(f"Error checking file {filename}: {e}")

    if deleted > 0:
        log.info(f"Cleanup complete: {deleted} old files deleted")


# =============================================================================
# ARCHIVE
# =============================================================================

def archive_daily_log():
    """Archive yesterday's log to gh-pages."""
    import subprocess

    yesterday = (datetime.now(timezone.utc).date() -
                 __import__('datetime').timedelta(days=1))
    yesterday_str = yesterday.strftime("%Y-%m-%d")
    year = yesterday.strftime("%Y")

    log_file = DATA_DIR / f"{yesterday_str}.txt"
    hash_file = DATA_DIR / f"shown_{yesterday_str}.txt"

    if not log_file.exists():
        log.info("No log to archive")
        return

    # Archive to gh-pages-dist
    gh_pages_dir = BASE_DIR / "gh-pages-dist"
    if not gh_pages_dir.exists():
        log.warning("gh-pages-dist not found, skipping archive")
        return

    # Create year folder in gh-pages archive
    archive_dir = gh_pages_dir / "archive" / year
    archive_dir.mkdir(parents=True, exist_ok=True)

    # Gzip the log
    archive_file = archive_dir / f"{yesterday_str}.txt.gz"
    with open(log_file, 'rb') as f_in:
        with gzip.open(archive_file, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)

    log.info(f"Archived: {archive_file}")

    # Clean up old local files
    log_file.unlink(missing_ok=True)
    hash_file.unlink(missing_ok=True)

    # Clean up processed headlines cache
    processed_file = DATA_DIR / f"processed_{yesterday_str}.txt"
    processed_file.unlink(missing_ok=True)

    # Commit and push to gh-pages
    try:
        subprocess.run(
            ["git", "add", f"archive/{year}/{yesterday_str}.txt.gz"],
            cwd=gh_pages_dir,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", f"Archive {yesterday_str}"],
            cwd=gh_pages_dir,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "push"],
            cwd=gh_pages_dir,
            check=True,
            capture_output=True
        )
        log.info(f"Archive pushed to gh-pages: {yesterday_str}")
    except subprocess.CalledProcessError as e:
        log.warning(f"Failed to push archive: {e}")


# =============================================================================
# MAIN LOOP
# =============================================================================

def process_cycle():
    """Run one processing cycle."""
    log.info("=" * 60)
    log.info("Starting cycle")

    # Check kill switch
    if KILL_SWITCH.exists():
        log.warning("KILL SWITCH ACTIVE - Stopping")
        sys.exit(0)

    # Load queue
    queue = load_queue()
    queue = clean_expired_queue(queue)

    # Scrape headlines
    headlines = scrape_all_sources()
    log.info(f"Total headlines: {len(headlines)}")

    # Load processed headlines cache
    processed_cache = load_processed_headlines()
    skipped_count = 0
    published_count = 0

    for headline in headlines:
        # Skip if already processed (saves API costs)
        if is_headline_processed(headline["text"], processed_cache):
            skipped_count += 1
            continue

        # Mark as processed before calling API
        add_processed_headline(get_story_hash(headline["text"]))

        # Extract fact
        result = extract_fact(headline["text"])

        # Skip if not a fact
        if result["fact"] == "SKIP":
            continue

        fact = result["fact"]
        confidence = result["confidence"]

        # JUDGE LOOKUP: If fact mentions a judge without full details, try to look them up
        if needs_judge_lookup(fact):
            log.info(f"Looking up judge info for: {fact[:50]}...")
            judge_info = search_judge_info(fact, headline["text"])
            if judge_info:
                fact = enhance_fact_with_judge(fact, judge_info)
                log.info(f"Enhanced with judge: {fact[:60]}...")

        # Check confidence threshold
        if confidence < CONFIG["thresholds"]["min_confidence"]:
            log.info(f"Low confidence ({confidence}%): {fact[:40]}...")
            continue

        # Check newsworthiness threshold
        newsworthy = result.get("newsworthy", True)  # Default to True for backwards compatibility
        threshold_met = result.get("threshold_met", "unknown")
        if not newsworthy:
            log.info(f"Not newsworthy ({threshold_met}): {fact[:40]}...")
            continue

        # Check for duplicates
        if is_duplicate(fact):
            log.info(f"Duplicate: {fact[:40]}...")
            continue

        # Look for matching stories in queue
        matches = find_matching_stories(fact, queue)

        if matches:
            # Check if any match has unrelated source
            for match in matches:
                if are_sources_unrelated(headline["source_id"], match["source_id"]):
                    # VERIFIED! Two unrelated sources
                    sources = [headline, match]

                    # Check for contradictions with recent facts
                    recent_facts = get_recent_facts()
                    if check_contradiction(fact, recent_facts):
                        log.warning(f"Contradiction blocked: {fact[:40]}...")
                        send_alert(f"Contradiction: {fact[:50]}")
                        continue

                    # Get audio index for caching
                    audio_index = get_next_audio_index()

                    # Generate TTS first (before JS sees the new story)
                    audio_file = generate_tts(fact, audio_index)

                    # Now write output (JS will detect and play)
                    write_current_story(fact, sources)
                    append_daily_log(fact, sources, audio_file)
                    add_shown_hash(get_story_hash(fact))

                    # Remove from queue
                    queue = [q for q in queue if q["fact"] != match["fact"]]

                    published_count += 1
                    log.info(f"VERIFIED: {fact[:50]}...")

                    # Record verification success for BOTH sources (ratings learning)
                    fact_hash = get_story_hash(fact)
                    record_verification_success(headline["source_id"], fact_hash)
                    record_verification_success(match["source_id"], fact_hash)

                    break
        else:
            # No match in queue - check if it updates an already-published story
            published_match = find_matching_published_story(fact)
            if published_match:
                # Check if this source is unrelated to existing sources
                existing_sources = published_match.get("source", "")
                source_name = headline["source_name"]

                if source_name not in existing_sources:
                    # 3rd+ source! Try to extract new details
                    new_detail = extract_new_details(fact, published_match["fact"])
                    if new_detail:
                        # Update the published story with new detail
                        update_published_story(
                            published_match["_index"],
                            new_detail,
                            headline
                        )
                        # Record verification success for the updating source
                        fact_hash = get_story_hash(published_match["fact"])
                        record_verification_success(headline["source_id"], fact_hash)
                        continue  # Don't add to queue

            # No match anywhere - add to queue
            queue.append({
                "fact": fact,
                "source_id": headline["source_id"],
                "source_name": headline["source_name"],
                "source_rating": headline["source_rating"],
                "timestamp": headline["timestamp"],
                "confidence": confidence
            })
            log.info(f"Queued: {fact[:40]}...")

    # Save queue
    save_queue(queue)

    log.info(f"Cycle complete. Published: {published_count}, Queue: {len(queue)}, Skipped (cached): {skipped_count}")


def check_midnight_archive():
    """Check if it's time to archive and cleanup (midnight GMT)."""
    now = datetime.now(timezone.utc)
    if now.hour == 0 and now.minute < 5:
        archive_daily_log()
        cleanup_old_data(days=7)  # Delete raw data older than 7 days

        # Clear the log file for the new day
        log_file = BASE_DIR / "jtf.log"
        if log_file.exists():
            log.info("Clearing jtf.log for new day")
            with open(log_file, 'w') as f:
                f.write(f"Log cleared at {now.isoformat()}\n")


def main():
    """Main entry point."""
    global _offline_alert_sent
    _offline_alert_sent = False  # Reset on startup so we catch new offline events

    log.info("JTF News starting...")
    log.info("Facts only. No opinions.")
    log.info("-" * 40)

    interval_minutes = CONFIG["timing"]["scrape_interval_minutes"]
    interval_seconds = interval_minutes * 60

    while True:
        try:
            # Write heartbeat to indicate we're alive
            write_heartbeat()

            # Check if stream appears offline
            check_stream_health()

            # Check for midnight archive
            check_midnight_archive()

            # Run cycle
            process_cycle()

            # Sleep until next cycle
            log.info(f"Sleeping {interval_minutes} minutes...")
            time.sleep(interval_seconds)

        except KeyboardInterrupt:
            log.info("Shutting down...")
            break
        except Exception as e:
            # Log errors but don't send SMS alerts for code bugs
            # Alerts are reserved for: stream offline, contradictions, major issues
            log.error(f"Cycle error: {e}")
            time.sleep(60)  # Wait 1 minute on error


if __name__ == "__main__":
    main()
