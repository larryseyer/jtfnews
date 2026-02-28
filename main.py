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
import calendar
from datetime import datetime, timezone, timedelta
from functools import wraps
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


def clean_duplicate_namespaces(file_path):
    """Remove duplicate namespace declarations from XML file.

    ElementTree sometimes adds duplicate xmlns declarations when multiple
    namespaces are used. This post-processes the file to remove duplicates.
    """
    import re
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the rss opening tag and clean up duplicates
    def remove_dupe_attrs(match):
        tag = match.group(0)
        # Extract all attributes
        attrs = re.findall(r'(\S+)="([^"]*)"', tag)
        seen = set()
        unique_attrs = []
        for name, value in attrs:
            if name not in seen:
                seen.add(name)
                unique_attrs.append(f'{name}="{value}"')
        return f'<rss {" ".join(unique_attrs)}>'

    content = re.sub(r'<rss[^>]+>', remove_dupe_attrs, content)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)


# =============================================================================
# RETRY LOGIC WITH EXPONENTIAL BACKOFF
# =============================================================================

def retry_with_backoff(max_retries=3, base_delay=1.0, retryable_exceptions=None):
    """Retry failed API calls with exponential backoff.

    Args:
        max_retries: Number of retry attempts (default 3)
        base_delay: Initial delay in seconds (default 1.0)
        retryable_exceptions: Tuple of exception types to retry on
    """
    if retryable_exceptions is None:
        retryable_exceptions = (ConnectionError, TimeoutError, OSError)

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt)  # 1s, 2s, 4s
                        log.warning(f"{func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}. Retrying in {delay}s...")
                        time.sleep(delay)
                    else:
                        log.error(f"{func.__name__} failed after {max_retries + 1} attempts: {e}")
            raise last_exception
        return wrapper
    return decorator


# =============================================================================
# CONFIGURATION
# =============================================================================

# Load environment variables
load_dotenv()

# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DIGEST_STATUS_FILE = DATA_DIR / "digest-status.json"
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

# Logging - with explicit flush for network mount compatibility
class FlushingFileHandler(logging.FileHandler):
    """FileHandler that flushes after every write for network mount sync."""
    def emit(self, record):
        super().emit(record)
        self.flush()


class ErrorCapturingHandler(logging.Handler):
    """Captures recent warnings and errors for dashboard display."""

    def __init__(self, max_records=50):
        super().__init__(level=logging.WARNING)
        self.max_records = max_records
        self.records = []

    def emit(self, record):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage()
        }
        self.records.append(entry)
        # Keep only last N records
        if len(self.records) > self.max_records:
            self.records = self.records[-self.max_records:]

    def get_recent(self, count=10, max_age_hours=1):
        """Get recent errors, filtering out those older than max_age_hours."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        recent = [r for r in self.records if datetime.fromisoformat(r['timestamp'].replace('Z', '+00:00')) > cutoff]
        return recent[-count:]


# Global error handler for dashboard
error_handler = ErrorCapturingHandler(max_records=50)

log = logging.getLogger("jtf")
log.setLevel(logging.INFO)
log.propagate = False  # Prevent duplicate logging to root logger
log_format = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_format)
log.addHandler(console_handler)

# File handler with flush
file_handler = FlushingFileHandler(BASE_DIR / "jtf.log")
file_handler.setFormatter(log_format)
log.addHandler(file_handler)

# Error capturing handler for dashboard
log.addHandler(error_handler)

# Kill switch file
KILL_SWITCH = Path("/tmp/jtf-stop")

# =============================================================================
# API COST TRACKING
# =============================================================================

# API costs per unit (updated February 2025)
API_COSTS = {
    "claude": {"input_per_1k": 0.00025, "output_per_1k": 0.00125},  # Haiku 4.5
    "elevenlabs": {"per_character": 0.00003},  # ~$0.03 per 1k chars
    "twilio": {"per_sms": 0.0079}
}

# Track when the app started
STARTUP_TIME = datetime.now(timezone.utc)

# In-memory cycle stats (reset each cycle)
_cycle_stats = {
    "headlines_scraped": 0,
    "headlines_processed": 0,
    "stories_published": 0,
    "stories_queued": 0,
    "cycle_number": 0,
    "cycle_start": None
}

# =============================================================================
# RESILIENCE SYSTEM
# =============================================================================

# Alert throttling - prevent SMS spam
_alert_cooldowns = {}  # {alert_type: last_sent_timestamp}
ALERT_COOLDOWNS = {
    "api_failure": 3600,      # 1 hour between API failure alerts
    "credits_low": 86400,     # 24 hours between budget alerts
    "queue_backup": 21600,    # 6 hours between queue backup alerts
    "offline": 0,             # No cooldown - handled by _offline_alert_sent flag
    "contradiction": 0,       # No cooldown for contradictions
    "general": 3600           # 1 hour for generic alerts
}

# Budget monitoring
MONTHLY_BUDGET = 50.00  # $50/month donation goal


def get_daily_budget() -> float:
    """Calculate daily budget based on days in current month.

    February: $50/28 = $1.79/day
    March: $50/31 = $1.61/day
    """
    today = datetime.now(timezone.utc)
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    return MONTHLY_BUDGET / days_in_month

# Degraded service tracking
_degraded_services = set()  # {"elevenlabs", "twilio"} when degraded

# Consecutive failure tracking for alerting
_consecutive_failures = {"claude": 0, "elevenlabs": 0, "twilio": 0}


def safe_parse_claude_json(text: str, default: dict) -> dict:
    """Parse Claude response with fallback for malformed JSON.

    Tries multiple strategies:
    1. Standard JSON parsing (with brace extraction)
    2. Extract from markdown code blocks
    3. Regex extraction of key fields
    4. Return default if all fail
    """
    if not text:
        return default

    # Strategy 1: Extract JSON object from text
    try:
        start = text.find('{')
        end = text.rfind('}') + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract from markdown code blocks
    try:
        import re
        code_match = re.search(r'```(?:json)?\s*(\{[^`]+\})\s*```', text, re.DOTALL)
        if code_match:
            return json.loads(code_match.group(1))
    except json.JSONDecodeError:
        pass

    # Strategy 3: Regex extraction of common fields
    result = dict(default)  # Copy default

    # Try to extract "contradiction" field
    contradiction_match = re.search(r'"contradiction"\s*:\s*(true|false)', text, re.IGNORECASE)
    if contradiction_match:
        result["contradiction"] = contradiction_match.group(1).lower() == "true"

    # Try to extract "new_detail" field
    detail_match = re.search(r'"new_detail"\s*:\s*"([^"]*(?:\\.[^"]*)*)"', text)
    if detail_match:
        result["new_detail"] = detail_match.group(1).replace('\\"', '"')

    # Try to extract "reason" field
    reason_match = re.search(r'"reason"\s*:\s*"([^"]*(?:\\.[^"]*)*)"', text)
    if reason_match:
        result["reason"] = reason_match.group(1).replace('\\"', '"')

    return result


def should_send_alert(alert_type: str) -> bool:
    """Check if alert should be sent based on cooldown."""
    cooldown = ALERT_COOLDOWNS.get(alert_type, ALERT_COOLDOWNS["general"])

    if cooldown == 0:
        return True  # No throttling for this type

    last_sent = _alert_cooldowns.get(alert_type, 0)
    now = time.time()

    if now - last_sent >= cooldown:
        _alert_cooldowns[alert_type] = now
        return True

    return False


def validate_services() -> bool:
    """Validate all required services at startup.

    Returns:
        True if critical services (Claude) are working
        Sets _degraded_services for non-critical services that fail
    """
    global _degraded_services
    _degraded_services = set()

    log.info("Validating services...")

    # Check required environment variables
    required_vars = ["ANTHROPIC_API_KEY"]
    optional_vars = {
        "ELEVENLABS_API_KEY": "elevenlabs",
        "TWILIO_ACCOUNT_SID": "twilio",
        "TWILIO_AUTH_TOKEN": "twilio"
    }

    for var in required_vars:
        if not os.getenv(var):
            log.critical(f"Missing required environment variable: {var}")
            return False

    for var, service in optional_vars.items():
        if not os.getenv(var):
            log.warning(f"Missing {var} - {service} will be unavailable")
            _degraded_services.add(service)

    # Test Claude API with minimal call
    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=CONFIG["claude"]["model"],
            max_tokens=10,
            messages=[{"role": "user", "content": "Reply with: OK"}]
        )
        log_api_usage("claude", {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens
        })
        log.info("Claude API: OK")
    except anthropic.AuthenticationError as e:
        log.critical(f"Claude API authentication failed: {e}")
        return False
    except Exception as e:
        log.critical(f"Claude API test failed: {e}")
        return False

    # Test ElevenLabs if not already degraded
    if "elevenlabs" not in _degraded_services:
        try:
            eleven_client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
            # Just verify the key works - don't generate audio
            # The client will raise if key is invalid on first use
            log.info("ElevenLabs API: OK (key present)")
        except Exception as e:
            log.warning(f"ElevenLabs validation failed: {e} - continuing without TTS")
            _degraded_services.add("elevenlabs")

    # Report degraded services
    if _degraded_services:
        log.warning(f"Running in degraded mode - unavailable services: {_degraded_services}")
    else:
        log.info("All services validated successfully")

    return True


def track_api_failure(service: str, success: bool):
    """Track consecutive API failures for alerting.

    Sends alert after 3 consecutive failures.
    """
    global _consecutive_failures

    if success:
        _consecutive_failures[service] = 0
        return

    _consecutive_failures[service] = _consecutive_failures.get(service, 0) + 1

    if _consecutive_failures[service] >= 3:
        if should_send_alert("api_failure"):
            send_alert(f"{service} API failed {_consecutive_failures[service]} times", "api_failure")
        _consecutive_failures[service] = 0  # Reset after alert


def check_budget_alert(total_cost: float):
    """Send alert if costs exceed 80% of daily budget."""
    daily_budget = get_daily_budget()
    if total_cost > daily_budget * 0.8:
        if should_send_alert("credits_low"):
            pct = (total_cost / daily_budget) * 100
            send_alert(f"API costs at ${total_cost:.2f} ({pct:.0f}% of ${daily_budget:.2f} budget)", "credits_low")


def log_api_usage(service: str, usage: dict):
    """Log API usage and costs to daily file.

    Args:
        service: "claude", "elevenlabs", or "twilio"
        usage: Dict with service-specific usage data:
            - claude: {"input_tokens": N, "output_tokens": N}
            - elevenlabs: {"characters": N}
            - twilio: {"sms_count": N}
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    usage_file = DATA_DIR / f"api_usage_{today}.json"

    # Load existing usage
    data = {"date": today, "services": {}, "total_cost_usd": 0.0}
    if usage_file.exists():
        try:
            with open(usage_file) as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass

    # Initialize service if not present
    if service not in data["services"]:
        data["services"][service] = {"calls": 0, "cost_usd": 0.0, "details": {}}

    svc = data["services"][service]
    svc["calls"] += 1

    # Calculate cost based on service type
    cost = 0.0
    if service == "claude":
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        cost = (input_tokens / 1000 * API_COSTS["claude"]["input_per_1k"] +
                output_tokens / 1000 * API_COSTS["claude"]["output_per_1k"])
        svc["details"]["input_tokens"] = svc["details"].get("input_tokens", 0) + input_tokens
        svc["details"]["output_tokens"] = svc["details"].get("output_tokens", 0) + output_tokens

    elif service == "elevenlabs":
        chars = usage.get("characters", 0)
        cost = chars * API_COSTS["elevenlabs"]["per_character"]
        svc["details"]["characters"] = svc["details"].get("characters", 0) + chars

    elif service == "twilio":
        count = usage.get("sms_count", 1)
        cost = count * API_COSTS["twilio"]["per_sms"]
        svc["details"]["sms_count"] = svc["details"].get("sms_count", 0) + count

    svc["cost_usd"] += cost

    # Update total
    data["total_cost_usd"] = sum(s["cost_usd"] for s in data["services"].values())

    # Save back
    try:
        with open(usage_file, 'w') as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        log.warning(f"Could not save API usage: {e}")


def get_api_costs_today() -> dict:
    """Get today's API costs summary."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    usage_file = DATA_DIR / f"api_usage_{today}.json"

    if usage_file.exists():
        try:
            with open(usage_file) as f:
                return json.load(f)
        except:
            pass

    return {"date": today, "services": {}, "total_cost_usd": 0.0}


# =============================================================================
# ROLLING COST & UPTIME TRACKING
# =============================================================================

DAILY_COSTS_FILE = DATA_DIR / "daily_costs.json"
UPTIME_STATS_FILE = DATA_DIR / "uptime_stats.json"


def load_daily_costs() -> dict:
    """Load rolling 30-day cost history."""
    if DAILY_COSTS_FILE.exists():
        try:
            with open(DAILY_COSTS_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"days": [], "last_updated": None}


def save_daily_costs(data: dict):
    """Save rolling cost history, keeping only last 30 days."""
    # Prune to 30 days
    if len(data["days"]) > 30:
        data["days"] = data["days"][-30:]

    data["last_updated"] = datetime.now(timezone.utc).isoformat()

    try:
        with open(DAILY_COSTS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        log.warning(f"Could not save daily costs: {e}")


def archive_yesterday_cost():
    """Archive yesterday's cost to rolling history.

    Called on startup or at midnight to record completed day's cost.
    """
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    yesterday_file = DATA_DIR / f"api_usage_{yesterday}.json"

    if not yesterday_file.exists():
        return  # No data for yesterday

    # Load yesterday's total
    try:
        with open(yesterday_file) as f:
            yesterday_data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return

    cost = yesterday_data.get("total_cost_usd", 0)

    # Load existing history
    history = load_daily_costs()

    # Check if already recorded
    for day in history["days"]:
        if day["date"] == yesterday:
            return  # Already archived

    # Add yesterday's cost
    history["days"].append({
        "date": yesterday,
        "cost_usd": round(cost, 4)
    })

    save_daily_costs(history)
    log.info(f"Archived {yesterday} cost: ${cost:.4f}")


def get_month_estimate() -> float:
    """Calculate monthly cost estimate from rolling 30-day history.

    Uses average daily cost from history, falls back to today's cost if
    no history available.
    """
    history = load_daily_costs()

    # Get today's cost
    today_data = get_api_costs_today()
    today_cost = today_data.get("total_cost_usd", 0)

    # Calculate days in current month
    now = datetime.now(timezone.utc)
    days_in_month = calendar.monthrange(now.year, now.month)[1]

    if not history["days"]:
        # No history - use today's cost as floor
        return today_cost

    # Calculate average daily cost from history
    total_cost = sum(day["cost_usd"] for day in history["days"])
    avg_daily = total_cost / len(history["days"])

    # Weight recent days more heavily (optional: could add exponential decay)
    # For now, simple average * days in month
    return avg_daily * days_in_month


def load_uptime_stats() -> dict:
    """Load monthly uptime tracking stats."""
    if UPTIME_STATS_FILE.exists():
        try:
            with open(UPTIME_STATS_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {
        "month": None,
        "total_running_seconds": 0,
        "total_elapsed_seconds": 0,
        "availability_pct": 0,
        "last_heartbeat": None,
        "session_start": None
    }


def save_uptime_stats(stats: dict):
    """Save uptime stats to file."""
    try:
        with open(UPTIME_STATS_FILE, 'w') as f:
            json.dump(stats, f, indent=2)
    except IOError as e:
        log.warning(f"Could not save uptime stats: {e}")


def init_uptime_tracking():
    """Initialize uptime tracking on startup.

    - If same month: add downtime since last_heartbeat
    - If new month: reset all counters
    """
    now = datetime.now(timezone.utc)
    current_month = now.strftime("%Y-%m")

    stats = load_uptime_stats()

    if stats["month"] != current_month:
        # New month - reset counters
        log.info(f"New month {current_month} - resetting uptime stats")
        stats = {
            "month": current_month,
            "total_running_seconds": 0,
            "total_elapsed_seconds": 0,
            "availability_pct": 0,
            "last_heartbeat": now.isoformat(),
            "session_start": now.isoformat()
        }
    else:
        # Same month - account for downtime
        if stats["last_heartbeat"]:
            try:
                last_hb = datetime.fromisoformat(stats["last_heartbeat"].replace('Z', '+00:00'))
                downtime = (now - last_hb).total_seconds()
                stats["total_elapsed_seconds"] += downtime
                log.info(f"Resuming uptime tracking - {downtime:.0f}s downtime recorded")
            except (ValueError, TypeError):
                pass

        stats["session_start"] = now.isoformat()
        stats["last_heartbeat"] = now.isoformat()

    save_uptime_stats(stats)
    return stats


def update_uptime_tracking() -> dict:
    """Update uptime tracking on each heartbeat.

    Adds time since last heartbeat to running totals.
    Returns current stats for display.
    """
    now = datetime.now(timezone.utc)
    current_month = now.strftime("%Y-%m")

    stats = load_uptime_stats()

    # Check for month rollover
    if stats["month"] != current_month:
        stats = init_uptime_tracking()
        return stats

    # Calculate time since last heartbeat
    if stats["last_heartbeat"]:
        try:
            last_hb = datetime.fromisoformat(stats["last_heartbeat"].replace('Z', '+00:00'))
            elapsed = (now - last_hb).total_seconds()

            # Cap at 5 minutes - anything longer suggests a restart (handled by init)
            if elapsed <= 300:
                stats["total_running_seconds"] += elapsed
                stats["total_elapsed_seconds"] += elapsed
        except (ValueError, TypeError):
            pass

    stats["last_heartbeat"] = now.isoformat()

    # Calculate availability
    if stats["total_elapsed_seconds"] > 0:
        stats["availability_pct"] = round(
            (stats["total_running_seconds"] / stats["total_elapsed_seconds"]) * 100, 1
        )

    save_uptime_stats(stats)
    return stats


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
9. OFFICIAL TITLES REQUIRED - Titles are facts. Omitting them is editorial.
   - Never bare last names. Always include official titles for government officials.
   - HEADS OF STATE/GOVERNMENT: "President Trump", "President Biden", "Prime Minister Starmer" - NEVER just "Trump" or "Biden" alone
   - MEMBERS OF CONGRESS: "Senator Cruz", "Representative Crockett" - NEVER just last name alone
   - CABINET/EXECUTIVES: "Secretary Rubio", "Director Smith" - include their role
   - Format: "[Official Title] [Last Name]" for well-known figures, "[Official Title] [Full Name]" for lesser-known
   - WRONG: "Trump stated...", "Biden announced...", "Cruz said..."
   - CORRECT: "President Trump stated...", "President Biden announced...", "Senator Cruz said..."
   - Media-invented nicknames are editorialization, not titles. "Border czar" is journalistic shorthand that carries implicit judgment - use official title instead
   - If you don't know the official title, describe the role: "the official responsible for border policy"
   - NEVER use first name alone unless disambiguating two people with same last name
   - Former officials: "former President Obama", "former Secretary Clinton" (lowercase "former")
10. JUDGES: Always include full name AND court jurisdiction - both are facts.
   - Format: "Judge [Full Name] of the [Court Name]"
   - Example: "Judge Aileen Cannon of the U.S. District Court for the Southern District of Florida ruled..."
   - Example: "Chief Justice John Roberts of the U.S. Supreme Court ruled..."
   - The judge's NAME is a fact. The court is a fact. Omitting either is editorial.
   - Extract ALL judge information from the headline (name, court level, location, district)
   - If headline has judge's name → ALWAYS include it with proper title and court
   - If headline lacks the name but has court info → Flag for lookup, use court info available
   - ONLY use "A federal judge" if the name is truly unavailable after lookup
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
- Major natural disaster, pandemic, or public health emergency
If the story does NOT meet any threshold, set newsworthy to false.

OUTPUT FORMAT:
Return a JSON object with:
- "fact": The clean, factual sentence (or "SKIP" if no verifiable facts)
- "confidence": Your confidence percentage (0-100) that this is purely factual
- "newsworthy": true or false based on the threshold criteria above
- "threshold_met": Which threshold it meets (e.g., "death/violence", "500+ affected", "$1M+ cost/investment", "law change", "border change", "scientific achievement", "humanitarian milestone", "head of state", "economic indicator", "international diplomacy", "disaster/pandemic/health emergency") or "none"

Headline to process:
"""


@retry_with_backoff(max_retries=3, base_delay=1.0, retryable_exceptions=(
    ConnectionError, TimeoutError, OSError,
    anthropic.APITimeoutError, anthropic.APIConnectionError,
    anthropic.RateLimitError, anthropic.InternalServerError
))
def extract_fact(headline: str, use_cache: bool = True) -> dict:
    """Send headline to Claude for fact extraction.

    Uses cached result if available to reduce API costs.
    """
    headline_hash = get_story_hash(headline)

    # Check cache first (saves ~$0.001 per cached hit)
    if use_cache:
        cached = _fact_extraction_cache.get(headline_hash)
        if cached:
            log.debug(f"Cache hit for headline: {headline[:50]}...")
            return cached

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

        # Log API usage for cost tracking
        log_api_usage("claude", {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens
        })

        text = response.content[0].text

        # Try standard JSON parsing first
        try:
            start = text.find('{')
            end = text.rfind('}') + 1
            if start >= 0 and end > start:
                result = json.loads(text[start:end])
                save_fact_extraction(headline_hash, result)
                return result
        except json.JSONDecodeError:
            pass

        # Fallback: Extract fields using regex (handles malformed JSON)
        fact_match = re.search(r'"fact"\s*:\s*"([^"]*(?:\\.[^"]*)*)"', text)
        conf_match = re.search(r'"confidence"\s*:\s*(\d+)', text)

        if fact_match:
            fact = fact_match.group(1).replace('\\"', '"')
            confidence = int(conf_match.group(1)) if conf_match else 85
            result = {"fact": fact, "confidence": confidence, "removed": []}
            save_fact_extraction(headline_hash, result)
            return result

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

        # Log API usage for cost tracking
        log_api_usage("claude", {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens
        })

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
                        "source_url": source["url"],
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
        # Use browser-like headers for sites with aggressive bot detection
        # This is ethical as we verify robots.txt allows access first
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }

        response = requests.get(source["url"], headers=headers, timeout=15, allow_redirects=True)
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
                    "source_url": source["url"],
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


def get_ordinal_suffix(n: int) -> str:
    """Return ordinal suffix for a number (1st, 2nd, 3rd, 4th...).

    Handles special cases: 11th, 12th, 13th.

    Args:
        n: The number to get the suffix for

    Returns:
        Ordinal suffix string ('st', 'nd', 'rd', or 'th')
    """
    if 11 <= n <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


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

        # Log API usage for cost tracking
        log_api_usage("claude", {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens
        })

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

        # Log API usage for cost tracking
        log_api_usage("claude", {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens
        })

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


def get_reliability_score(source_id: str, confidence: int) -> float:
    """Calculate reliability score for conflict resolution.

    Formula: source_rating × (confidence / 100)

    When two sources verify the same event but report different details,
    the higher reliability score determines which version to publish.

    Example:
        Reuters (9.8 rating) at 95% confidence = 9.31 reliability
        TOI (7.4 rating) at 90% confidence = 6.66 reliability
        → Reuters' version wins
    """
    rating = get_learned_rating(source_id)
    return rating * (confidence / 100)


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


def get_compact_scores(source_id: str) -> str:
    """Get compact Accuracy|Bias display for lower-third.

    Format: "9.8|9.5" or "9.8*|9.5" (asterisk if accuracy has limited data)
    Accuracy is learned/blended, Bias is from config baseline.
    """
    # Get accuracy part (learned or baseline)
    accuracy_display = get_display_rating(source_id)

    # Extract just the number and asterisk (strip evidence counts)
    # e.g., "9.4 (47/50)" -> "9.4", "8.5* (3/10)" -> "8.5*", "9.6*" -> "9.6*"
    accuracy_part = accuracy_display.split()[0]  # Gets "9.4" or "8.5*" or "9.6*"

    # Get bias from config (always baseline, not learned)
    # Config stores bias on -2 to +2 scale (political leaning)
    # Convert to 0-10 scale where 10 = neutral, 0 = heavily biased
    raw_bias = 0.0
    for source in CONFIG["sources"]:
        if source["id"] == source_id:
            raw_bias = source["ratings"].get("bias", 0.0)
            break

    # Convert: 0 → 10, ±2 → 0
    # Formula: 10 - (abs(bias) * 5), clamped to 0-10
    bias_score = max(0.0, min(10.0, 10.0 - (abs(raw_bias) * 5)))

    return f"{accuracy_part}|{bias_score:.1f}"


def get_source_id_by_name(source_name: str) -> str:
    """Look up source ID from source name. Returns empty string if not found."""
    name_lower = source_name.lower().strip()
    for source in CONFIG["sources"]:
        if source["name"].lower() == name_lower:
            return source["id"]
    return ""


def get_source_for_rss(source_id: str) -> dict:
    """Build rich source data for RSS feed per SPECIFICATION.md Section 5.3.3.

    Returns dict with name, all 4 scores, control_type, and top 3 owners.
    Format matches spec: accuracy, bias, speed, consensus as attributes,
    owners as nested elements with name and percent.
    """
    # Find source in config
    source_config = None
    for source in CONFIG["sources"]:
        if source["id"] == source_id:
            source_config = source
            break

    if not source_config:
        return {"name": source_id, "url": "", "accuracy": "0.0", "bias": "0.0",
                "speed": "0.0", "consensus": "0.0", "control_type": "unknown", "owners": []}

    # Get learned accuracy (or baseline with asterisk indicator)
    accuracy_display = get_display_rating(source_id)
    accuracy_part = accuracy_display.split()[0]  # "9.4" or "8.5*"

    # Get bias score (convert from -2/+2 scale to 0-10 where 10 = neutral)
    raw_bias = source_config["ratings"].get("bias", 0.0)
    bias_score = max(0.0, min(10.0, 10.0 - (abs(raw_bias) * 5)))

    # Get speed and consensus from config
    speed = source_config["ratings"].get("speed", 5.0)
    consensus = source_config["ratings"].get("consensus", 5.0)

    # Get ownership data (top 3)
    owners = []
    for holder in source_config.get("institutional_holders", [])[:3]:
        owners.append({
            "name": holder["name"],
            "percent": f"{holder['percent']:.1f}"
        })

    # If no institutional holders, use owner field
    if not owners and source_config.get("owner"):
        owners.append({
            "name": source_config["owner"],
            "percent": "100.0"
        })

    return {
        "name": source_config["name"],
        "url": source_config.get("url", ""),
        "accuracy": accuracy_part,
        "bias": f"{bias_score:.1f}",
        "speed": f"{speed:.1f}",
        "consensus": f"{consensus:.1f}",
        "control_type": source_config.get("control_type", "unknown"),
        "owners": owners
    }


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
# FACT EXTRACTION CACHE (Cache Claude responses to avoid redundant API calls)
# =============================================================================

# In-memory cache for fact extractions (headline_hash -> extraction result)
_fact_extraction_cache: dict = {}


def load_fact_extraction_cache() -> dict:
    """Load cached fact extractions from disk."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cache_file = DATA_DIR / f"fact_cache_{today}.json"

    if cache_file.exists():
        try:
            with open(cache_file) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_fact_extraction(headline_hash: str, result: dict):
    """Save a fact extraction result to cache."""
    global _fact_extraction_cache
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cache_file = DATA_DIR / f"fact_cache_{today}.json"

    _fact_extraction_cache[headline_hash] = result

    try:
        with open(cache_file, 'w') as f:
            json.dump(_fact_extraction_cache, f)
    except IOError as e:
        log.warning(f"Could not save fact cache: {e}")


def get_cached_fact_extraction(headline_text: str) -> dict | None:
    """Get cached extraction result if available."""
    headline_hash = get_story_hash(headline_text)
    return _fact_extraction_cache.get(headline_hash)


# =============================================================================
# TEXT-TO-SPEECH
# =============================================================================

def get_next_audio_index() -> int:
    """Get the next audio file index based on today's stories.

    DEPRECATED: Use get_story_audio_id() for new code.
    """
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


def get_story_audio_id(fact: str) -> str:
    """Generate a unique audio ID from the story fact.

    Uses the story hash to create a consistent ID that links
    the story text to its audio file, regardless of processing order.

    Args:
        fact: The story fact text

    Returns:
        Audio ID like 'a3f2b1c9d4e5' (12 chars)
    """
    return get_story_hash(fact)


@retry_with_backoff(max_retries=2, base_delay=1.0)
def generate_tts(text: str, audio_index: int = None, story_id: str = None, archive_date: str = None) -> str:
    """Generate TTS audio using ElevenLabs. Returns audio filename.

    Writes audio directly to day-specific archive folder to prevent overwrites
    at day boundaries. Also copies to current.mp3 for live playback.

    Args:
        text: Text to convert to speech
        audio_index: DEPRECATED - legacy index-based naming (writes to audio/)
        story_id: Unique story ID for the audio filename (writes to archive)
        archive_date: Optional YYYY-MM-DD date for archive folder (defaults to today UTC)

    Returns:
        Audio filename on success, False on failure
    """
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

        # Log API usage for cost tracking
        log_api_usage("elevenlabs", {"characters": len(text)})

        # Determine filename and save location
        # story_id (hash-based): Write directly to today's archive folder (SAFE)
        # audio_index (legacy): Write to audio/ folder (can be overwritten - DEPRECATED)
        # neither: Write to current.mp3 only
        if story_id:
            # NEW: Write directly to archive folder to prevent overwrites
            # Use provided date or default to today UTC
            folder_date = archive_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
            archive_dir = AUDIO_DIR / "archive" / folder_date
            archive_dir.mkdir(parents=True, exist_ok=True)

            audio_filename = f"{story_id}.mp3"
            audio_path = archive_dir / audio_filename

            with open(audio_path, 'wb') as f:
                f.write(audio_data)

            log.info(f"Generated TTS (archive/{folder_date}/{audio_filename}): {text[:50]}...")

        elif audio_index is not None:
            # LEGACY: Write to audio/ folder (can still be overwritten)
            audio_filename = f"audio_{audio_index}.mp3"
            audio_path = AUDIO_DIR / audio_filename

            with open(audio_path, 'wb') as f:
                f.write(audio_data)

            log.info(f"Generated TTS ({audio_filename}): {text[:50]}...")

        else:
            audio_filename = "current.mp3"
            log.info(f"Generated TTS (current.mp3): {text[:50]}...")

        # Always save to current.mp3 for immediate playback
        current_path = AUDIO_DIR / "current.mp3"
        with open(current_path, 'wb') as f:
            f.write(audio_data)

        return audio_filename

    except Exception as e:
        log.error(f"TTS error: {e}")
        return False


def generate_intro_audio(date: datetime) -> str:
    """Generate intro TTS audio for the daily digest.

    Creates a spoken intro like:
    "The following is the JTF News Daily Digest for Monday, the 24th of February, 2026."

    Args:
        date: datetime object for the digest date

    Returns:
        Audio filename on success, False on failure
    """
    day_name = date.strftime("%A")  # "Monday"
    day_num = date.day
    suffix = get_ordinal_suffix(day_num)  # "st", "nd", "rd", "th"
    month = date.strftime("%B")  # "February"
    year = date.year

    text = f"The following is the JTF News Daily Digest for {day_name}, the {day_num}{suffix} of {month}, {year}.  Every story you're about to hear was verified by two or more independent sources."

    # Use the digest date for the archive folder, not current UTC date
    archive_date = date.strftime("%Y-%m-%d")
    log.info(f"Generating intro audio for {archive_date}: {text}")
    return generate_tts(text, story_id="intro", archive_date=archive_date)


def generate_outro_audio(date: datetime) -> str:
    """Generate outro TTS audio for the daily digest.

    Creates a spoken outro like:
    "You have been listening to the JTF News Daily Digest for Monday, the 24th of February, 2026."

    Args:
        date: datetime object for the digest date

    Returns:
        Audio filename on success, False on failure
    """
    day_name = date.strftime("%A")  # "Monday"
    day_num = date.day
    suffix = get_ordinal_suffix(day_num)  # "st", "nd", "rd", "th"
    month = date.strftime("%B")  # "February"
    year = date.year

    text = f"You have been listening to the JTF News Daily Digest for {day_name}, the {day_num}{suffix} of {month}, {year}.  Facts without opinion. We do not interpret."

    # Use the digest date for the archive folder, not current UTC date
    archive_date = date.strftime("%Y-%m-%d")
    log.info(f"Generating outro audio for {archive_date}: {text}")
    return generate_tts(text, story_id="outro", archive_date=archive_date)


def format_source_names_with_ratings(source_names_str: str) -> str:
    """Format source names string with ratings for digest display.

    Takes comma-separated source names from daily log and adds ratings.

    Args:
        source_names_str: e.g., "NPR,CBC News" or "NPR,CBC News (+1 more)"

    Returns:
        Formatted string like "NPR 4.7|8.5 · CBC News 3.6|9.0"
    """
    # Handle "(+N more)" suffix
    extra_text = ""
    if " (+" in source_names_str:
        parts = source_names_str.split(" (+")
        source_names_str = parts[0]
        extra_text = f" (+{parts[1]}"

    # Split and look up each source
    names = [n.strip() for n in source_names_str.split(",")]
    formatted_parts = []

    for name in names[:2]:  # Only show first 2
        # Look up source ID by name
        source_id = None
        for src in CONFIG["sources"]:
            if src["name"] == name:
                source_id = src["id"]
                break

        if source_id:
            formatted_parts.append(f"{name} {get_compact_scores(source_id)}")
        else:
            formatted_parts.append(name)

    result = " · ".join(formatted_parts)
    if extra_text:
        result += extra_text

    return result


# =============================================================================
# OUTPUT FILES
# =============================================================================

def format_source_attribution(sources: list) -> str:
    """Format source attribution showing 2 sources + count if more verified.

    Shows first 2 sources with ratings. If 3+ sources verified the fact,
    appends "(+N more)" to indicate additional verification strength.
    """
    # Build text for first 2 sources
    source_text = " · ".join([
        f"{s['source_name']} {get_compact_scores(s['source_id'])}"
        for s in sources[:2]
    ])

    # Add "+N more" indicator if additional sources verified
    if len(sources) > 2:
        extra_count = len(sources) - 2
        source_text += f" (+{extra_count} more)"

    return source_text


def write_current_story(fact: str, sources: list):
    """Write the current story to output files."""
    # Format source attribution with evidence-based ratings
    source_text = format_source_attribution(sources)

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
    if len(sources) > 2:
        source_names += f" (+{len(sources) - 2} more)"
    source_scores = ",".join([get_display_rating(s["source_id"]) for s in sources[:2]])
    source_urls = ",".join([s.get("source_url", "") for s in sources[:2]])

    # Extract audio filename (e.g., "audio_0.mp3" from "../audio/audio_0.mp3")
    audio_name = ""
    if audio_file:
        audio_name = audio_file.split("/")[-1] if "/" in audio_file else audio_file

    # Format: timestamp|names|scores|urls|audio|fact (6 fields)
    line = f"{timestamp}|{source_names}|{source_scores}|{source_urls}|{audio_name}|{fact}\n"

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


def generate_story_id(date: str, index: int) -> str:
    """Generate a unique story ID like '2026-02-15-001'."""
    return f"{date}-{index:03d}"


def update_stories_json(fact: str, sources: list, audio_file: str = None):
    """Update stories.json for the JS loop display."""
    stories_file = DATA_DIR / "stories.json"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    now_iso = datetime.now(timezone.utc).isoformat()

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

    # Format source info with evidence-based ratings (shows "+N more" if 3+ sources)
    source_text = format_source_attribution(sources)

    # Generate story ID and hash
    story_index = len(stories["stories"])
    story_id = generate_story_id(today, story_index)
    story_hash = hashlib.md5(fact.encode()).hexdigest()[:12]

    # Build source_urls map for clickable links in archive
    source_urls = {s["source_name"]: s.get("source_url", "") for s in sources[:2]}

    # Determine audio path - hash-based files are in archive folder
    if audio_file:
        # Check if this is a hash-based filename (12 hex chars + .mp3)
        audio_stem = audio_file.replace(".mp3", "")
        if len(audio_stem) == 12 and all(c in '0123456789abcdef' for c in audio_stem):
            # Hash-based: points to today's archive folder
            audio_path = f"../audio/archive/{today}/{audio_file}"
        else:
            # Legacy index-based: points to audio/ folder
            audio_path = f"../audio/{audio_file}"
    else:
        audio_path = "../audio/current.mp3"

    # Add new story with expanded structure for corrections support
    stories["stories"].append({
        "id": story_id,
        "hash": story_hash,
        "fact": fact,
        "source": source_text,
        "source_urls": source_urls,
        "audio": audio_path,
        "published_at": now_iso,
        "status": "published"
    })

    # Write back
    with open(stories_file, 'w') as f:
        json.dump(stories, f, indent=2)

    # Also copy to docs for screensaver
    docs_dir = BASE_DIR / "docs"
    if docs_dir.exists():
        import shutil
        shutil.copy(stories_file, docs_dir / "stories.json")

    # Update RSS feed
    update_rss_feed(fact, sources)

    # Update Alexa Flash Briefing feed
    update_alexa_feed(fact, sources)


def update_rss_feed(fact: str, sources: list):
    """Update RSS feed with new story and push to GitHub.

    Per SPECIFICATION.md Section 5.3.3, each source element includes:
    - name, accuracy, bias, speed, consensus as attributes
    - owner elements with name and percent

    Uses jtf: namespace for custom elements to comply with RSS 2.0.
    """
    import subprocess

    # Namespace URIs
    JTF_NS = "https://jtfnews.com/rss"
    ATOM_NS = "http://www.w3.org/2005/Atom"

    # Register namespaces for clean XML output
    ET.register_namespace("jtf", JTF_NS)
    ET.register_namespace("atom", ATOM_NS)

    docs_dir = BASE_DIR / "docs"
    feed_file = docs_dir / "feed.xml"
    max_items = 100  # Keep last 100 stories in feed

    # Check if docs folder exists
    if not docs_dir.exists():
        log.warning("docs worktree not found, skipping RSS update")
        return

    # Build rich source data for each source (top 2)
    rich_sources = []
    for s in sources[:2]:
        source_data = get_source_for_rss(s['source_id'])
        rich_sources.append(source_data)

    # Create new item
    pub_date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    guid = hashlib.md5(f"{fact}{pub_date}".encode()).hexdigest()[:12]

    # Truncate fact for title (first 80 chars)
    title = fact[:80] + "..." if len(fact) > 80 else fact

    new_item = {
        "title": title,
        "description": fact,
        "sources": rich_sources,
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
                # Parse rich source structure (check both namespaced and non-namespaced)
                item_sources = []
                # Try namespaced version first
                for source_el in item.findall(f"{{{JTF_NS}}}source"):
                    source_data = {
                        "name": source_el.get("name", ""),
                        "url": source_el.get("url", ""),
                        "accuracy": source_el.get("accuracy", "0.0"),
                        "bias": source_el.get("bias", "0.0"),
                        "speed": source_el.get("speed", "0.0"),
                        "consensus": source_el.get("consensus", "0.0"),
                        "control_type": source_el.get("control_type", "unknown"),
                        "owners": []
                    }
                    for owner_el in source_el.findall(f"{{{JTF_NS}}}owner"):
                        source_data["owners"].append({
                            "name": owner_el.get("name", ""),
                            "percent": owner_el.get("percent", "0.0")
                        })
                    item_sources.append(source_data)

                # Fall back to non-namespaced (legacy migration)
                if not item_sources:
                    for source_el in item.findall("source"):
                        if source_el.get("name"):
                            source_data = {
                                "name": source_el.get("name", ""),
                                "url": source_el.get("url", ""),
                                "accuracy": source_el.get("accuracy", "0.0"),
                                "bias": source_el.get("bias", "0.0"),
                                "speed": source_el.get("speed", "0.0"),
                                "consensus": source_el.get("consensus", "0.0"),
                                "control_type": source_el.get("control_type", "unknown"),
                                "owners": []
                            }
                            for owner_el in source_el.findall("owner"):
                                source_data["owners"].append({
                                    "name": owner_el.get("name", ""),
                                    "percent": owner_el.get("percent", "0.0")
                                })
                            item_sources.append(source_data)
                        elif source_el.text:
                            # Very old format: plain text
                            for name in source_el.text.split(", "):
                                item_sources.append({
                                    "name": name.strip(),
                                    "url": "",
                                    "accuracy": "0.0", "bias": "0.0",
                                    "speed": "0.0", "consensus": "0.0",
                                    "control_type": "unknown", "owners": []
                                })

                items.append({
                    "title": item.find("title").text or "",
                    "description": item.find("description").text or "",
                    "sources": item_sources,
                    "pubDate": item.find("pubDate").text or "",
                    "guid": item.find("guid").text or ""
                })
        except Exception as e:
            log.warning(f"Error parsing existing RSS feed: {e}")

    # Add new item at beginning
    items.insert(0, new_item)

    # Trim to max items
    items = items[:max_items]

    # Build RSS XML (namespaces added via register_namespace above)
    rss = ET.Element("rss", {"version": "2.0"})
    # Manually set namespace attributes to ensure they appear on root element
    rss.set(f"xmlns:jtf", JTF_NS)
    rss.set(f"xmlns:atom", ATOM_NS)

    channel = ET.SubElement(rss, "channel")

    ET.SubElement(channel, "title").text = "JTF News - Just The Facts"
    ET.SubElement(channel, "link").text = "https://jtfnews.org/"
    ET.SubElement(channel, "description").text = "Verified facts from multiple sources. No opinions. No adjectives. No interpretation. Viewer-supported at github.com/sponsors/larryseyer"
    ET.SubElement(channel, "language").text = "en-us"
    ET.SubElement(channel, "lastBuildDate").text = pub_date

    # Add atom:link for RSS compliance
    ET.SubElement(channel, f"{{{ATOM_NS}}}link", {
        "href": "https://jtfnews.org/feed.xml",
        "rel": "self",
        "type": "application/rss+xml"
    })

    for item_data in items:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = item_data["title"]
        ET.SubElement(item, "description").text = item_data["description"]

        # Write namespaced source elements per SPECIFICATION.md
        for source_data in item_data.get("sources", []):
            source_el = ET.SubElement(item, f"{{{JTF_NS}}}source", {
                "name": source_data["name"],
                "url": source_data.get("url", ""),
                "accuracy": source_data["accuracy"],
                "bias": source_data["bias"],
                "speed": source_data["speed"],
                "consensus": source_data["consensus"],
                "control_type": source_data["control_type"]
            })
            for owner in source_data.get("owners", []):
                ET.SubElement(source_el, f"{{{JTF_NS}}}owner", {
                    "name": owner["name"],
                    "percent": owner["percent"]
                })

        ET.SubElement(item, "pubDate").text = item_data["pubDate"]
        ET.SubElement(item, "guid", isPermaLink="false").text = item_data["guid"]

    # Write with XML declaration (use custom indent for Python 3.8 compatibility)
    indent_xml(rss, space="  ")
    tree = ET.ElementTree(rss)
    with open(feed_file, 'wb') as f:
        tree.write(f, encoding="utf-8", xml_declaration=True)

    # Clean up duplicate namespace declarations (ElementTree quirk)
    clean_duplicate_namespaces(feed_file)

    log.info(f"RSS feed updated: {len(items)} items")

    # Push to GitHub via API
    stories_file = DATA_DIR / "stories.json"
    push_to_ghpages([
        (feed_file, "feed.xml"),
        (stories_file, "stories.json")
    ], f"Update feed: {title[:50]}")


def add_correction_to_rss(correction_type: str, original_fact: str,
                          corrected_fact: str, sources: list, story_id: str):
    """Add a correction/retraction item to the RSS feed.

    Uses same rich source format as update_rss_feed for consistency.
    Corrections only have source names (not IDs), so ratings are omitted.
    Uses jtf: namespace for custom elements to comply with RSS 2.0.
    """
    import subprocess

    # Namespace URIs
    JTF_NS = "https://jtfnews.com/rss"
    ATOM_NS = "http://www.w3.org/2005/Atom"

    # Register namespaces for clean XML output
    ET.register_namespace("jtf", JTF_NS)
    ET.register_namespace("atom", ATOM_NS)

    docs_dir = BASE_DIR / "docs"
    feed_file = docs_dir / "feed.xml"
    max_items = 100

    if not docs_dir.exists():
        log.warning("docs worktree not found, skipping RSS correction")
        return

    # Format source text for description
    source_text = ", ".join(sources[:2]) if sources else "verified sources"

    # Create title with correction prefix
    if correction_type == "retraction":
        title = f"[RETRACTION] {original_fact[:60]}..."
        description = f"RETRACTION: Earlier we reported that {original_fact}. This report was incorrect and has been retracted."
    else:
        title = f"[CORRECTION] {original_fact[:60]}..."
        description = f"CORRECTION: Earlier we reported that {original_fact}. {source_text} now report that {corrected_fact}."

    pub_date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    guid = hashlib.md5(f"correction-{story_id}-{pub_date}".encode()).hexdigest()[:12]

    # Build source data (corrections only have names, not full ratings)
    rich_sources = []
    for name in sources[:2]:
        rich_sources.append({
            "name": name,
            "url": "",
            "accuracy": "—", "bias": "—", "speed": "—", "consensus": "—",
            "control_type": "correction", "owners": []
        })

    new_item = {
        "title": title,
        "description": description,
        "sources": rich_sources,
        "pubDate": pub_date,
        "guid": guid
    }

    # Load existing items (same parsing logic as update_rss_feed)
    items = []
    if feed_file.exists():
        try:
            tree = ET.parse(feed_file)
            root = tree.getroot()
            channel = root.find("channel")
            for item in channel.findall("item"):
                item_sources = []
                # Try namespaced version first
                for source_el in item.findall(f"{{{JTF_NS}}}source"):
                    source_data = {
                        "name": source_el.get("name", ""),
                        "url": source_el.get("url", ""),
                        "accuracy": source_el.get("accuracy", "0.0"),
                        "bias": source_el.get("bias", "0.0"),
                        "speed": source_el.get("speed", "0.0"),
                        "consensus": source_el.get("consensus", "0.0"),
                        "control_type": source_el.get("control_type", "unknown"),
                        "owners": []
                    }
                    for owner_el in source_el.findall(f"{{{JTF_NS}}}owner"):
                        source_data["owners"].append({
                            "name": owner_el.get("name", ""),
                            "percent": owner_el.get("percent", "0.0")
                        })
                    item_sources.append(source_data)

                # Fall back to non-namespaced (legacy migration)
                if not item_sources:
                    for source_el in item.findall("source"):
                        if source_el.get("name"):
                            source_data = {
                                "name": source_el.get("name", ""),
                                "url": source_el.get("url", ""),
                                "accuracy": source_el.get("accuracy", "0.0"),
                                "bias": source_el.get("bias", "0.0"),
                                "speed": source_el.get("speed", "0.0"),
                                "consensus": source_el.get("consensus", "0.0"),
                                "control_type": source_el.get("control_type", "unknown"),
                                "owners": []
                            }
                            for owner_el in source_el.findall("owner"):
                                source_data["owners"].append({
                                    "name": owner_el.get("name", ""),
                                    "percent": owner_el.get("percent", "0.0")
                                })
                            item_sources.append(source_data)
                        elif source_el.text:
                            for name in source_el.text.split(", "):
                                item_sources.append({
                                    "name": name.strip(),
                                    "url": "",
                                    "accuracy": "0.0", "bias": "0.0",
                                    "speed": "0.0", "consensus": "0.0",
                                    "control_type": "unknown", "owners": []
                                })

                items.append({
                    "title": item.find("title").text or "",
                    "description": item.find("description").text or "",
                    "sources": item_sources,
                    "pubDate": item.find("pubDate").text or "",
                    "guid": item.find("guid").text or ""
                })
        except Exception as e:
            log.warning(f"Error parsing existing RSS feed: {e}")

    # Add correction at beginning (same prominence as regular stories)
    items.insert(0, new_item)
    items = items[:max_items]

    # Build RSS XML (register_namespace handles namespace declarations)
    rss = ET.Element("rss", {"version": "2.0"})

    channel = ET.SubElement(rss, "channel")

    ET.SubElement(channel, "title").text = "JTF News - Just The Facts"
    ET.SubElement(channel, "link").text = "https://jtfnews.org/"
    ET.SubElement(channel, "description").text = "Verified facts from multiple sources. No opinions. No adjectives. No interpretation. Viewer-supported at github.com/sponsors/larryseyer"
    ET.SubElement(channel, "language").text = "en-us"
    ET.SubElement(channel, "lastBuildDate").text = pub_date

    # Add atom:link for RSS compliance
    ET.SubElement(channel, f"{{{ATOM_NS}}}link", {
        "href": "https://jtfnews.org/feed.xml",
        "rel": "self",
        "type": "application/rss+xml"
    })

    for item_data in items:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = item_data["title"]
        ET.SubElement(item, "description").text = item_data["description"]

        # Write namespaced source elements
        for source_data in item_data.get("sources", []):
            source_el = ET.SubElement(item, f"{{{JTF_NS}}}source", {
                "name": source_data["name"],
                "accuracy": source_data["accuracy"],
                "bias": source_data["bias"],
                "speed": source_data["speed"],
                "consensus": source_data["consensus"],
                "control_type": source_data["control_type"]
            })
            for owner in source_data.get("owners", []):
                ET.SubElement(source_el, f"{{{JTF_NS}}}owner", {
                    "name": owner["name"],
                    "percent": owner["percent"]
                })

        ET.SubElement(item, "pubDate").text = item_data["pubDate"]
        ET.SubElement(item, "guid", isPermaLink="false").text = item_data["guid"]

    # Write with XML declaration
    indent_xml(rss, space="  ")
    tree = ET.ElementTree(rss)
    with open(feed_file, 'wb') as f:
        tree.write(f, encoding="utf-8", xml_declaration=True)

    # Clean up duplicate namespace declarations (ElementTree quirk)
    clean_duplicate_namespaces(feed_file)

    log.info(f"RSS feed updated with {correction_type}: {title[:50]}")

    # Push to GitHub via API
    push_to_ghpages([
        (feed_file, "feed.xml"),
        (CORRECTIONS_FILE, "corrections.json")
    ], f"{correction_type.upper()}: {story_id}")


def regenerate_rss_feed():
    """Regenerate RSS feed with rich source data from existing stories.json.

    Parses source names from stories.json, looks up full source data,
    and rebuilds the feed in the new format per SPECIFICATION.md Section 5.3.3.
    Uses jtf: namespace for custom elements to comply with RSS 2.0.
    """
    # Namespace URIs
    JTF_NS = "https://jtfnews.com/rss"
    ATOM_NS = "http://www.w3.org/2005/Atom"

    # Register namespaces for clean XML output
    ET.register_namespace("jtf", JTF_NS)
    ET.register_namespace("atom", ATOM_NS)

    docs_dir = BASE_DIR / "docs"
    feed_file = docs_dir / "feed.xml"
    stories_file = docs_dir / "stories.json"

    if not stories_file.exists():
        log.error("stories.json not found in docs")
        return False

    # Load stories
    with open(stories_file) as f:
        data = json.load(f)

    stories = data.get("stories", [])
    if not stories:
        log.warning("No stories found in stories.json")
        return False

    # Build items from stories
    items = []
    for story in stories:
        fact = story.get("fact", "")
        source_str = story.get("source", "")

        # Parse source string: "BBC News 9.5*|9.0 · Reuters 9.9*|9.5"
        rich_sources = []
        for part in source_str.split(" · "):
            # Extract source name (everything before the first digit or asterisk)
            import re
            match = re.match(r'^([A-Za-z\s\-\.]+)', part.strip())
            if match:
                source_name = match.group(1).strip()
                source_id = get_source_id_by_name(source_name)
                if source_id:
                    rich_sources.append(get_source_for_rss(source_id))
                else:
                    # Source not in config, use minimal data
                    rich_sources.append({
                        "name": source_name,
                        "accuracy": "—", "bias": "—", "speed": "—", "consensus": "—",
                        "control_type": "unknown", "owners": []
                    })

        # Use published_at if available, otherwise generate from story order
        pub_date = story.get("published_at", "")
        if pub_date:
            try:
                dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                pub_date = dt.strftime("%a, %d %b %Y %H:%M:%S +0000")
            except:
                pub_date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
        else:
            pub_date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")

        guid = story.get("hash", hashlib.md5(f"{fact}{pub_date}".encode()).hexdigest()[:12])
        title = fact[:80] + "..." if len(fact) > 80 else fact

        items.append({
            "title": title,
            "description": fact,
            "sources": rich_sources[:2],  # Top 2 sources
            "pubDate": pub_date,
            "guid": guid
        })

    # Reverse so newest is first
    items = items[::-1]

    # Also preserve any existing items not in stories.json (e.g., from previous days)
    if feed_file.exists():
        try:
            tree = ET.parse(feed_file)
            root = tree.getroot()
            channel = root.find("channel")
            existing_guids = {item["guid"] for item in items}
            for item in channel.findall("item"):
                guid = item.find("guid").text or ""
                if guid not in existing_guids:
                    # Parse and preserve existing items (check namespaced first)
                    item_sources = []
                    for source_el in item.findall(f"{{{JTF_NS}}}source"):
                        source_data = {
                            "name": source_el.get("name", ""),
                            "accuracy": source_el.get("accuracy", "0.0"),
                            "bias": source_el.get("bias", "0.0"),
                            "speed": source_el.get("speed", "0.0"),
                            "consensus": source_el.get("consensus", "0.0"),
                            "control_type": source_el.get("control_type", "unknown"),
                            "owners": []
                        }
                        for owner_el in source_el.findall(f"{{{JTF_NS}}}owner"):
                            source_data["owners"].append({
                                "name": owner_el.get("name", ""),
                                "percent": owner_el.get("percent", "0.0")
                            })
                        item_sources.append(source_data)

                    # Fall back to non-namespaced (legacy)
                    if not item_sources:
                        for source_el in item.findall("source"):
                            if source_el.get("name"):
                                source_data = {
                                    "name": source_el.get("name", ""),
                                    "url": source_el.get("url", ""),
                                    "accuracy": source_el.get("accuracy", "0.0"),
                                    "bias": source_el.get("bias", "0.0"),
                                    "speed": source_el.get("speed", "0.0"),
                                    "consensus": source_el.get("consensus", "0.0"),
                                    "control_type": source_el.get("control_type", "unknown"),
                                    "owners": []
                                }
                                for owner_el in source_el.findall("owner"):
                                    source_data["owners"].append({
                                        "name": owner_el.get("name", ""),
                                        "percent": owner_el.get("percent", "0.0")
                                    })
                                item_sources.append(source_data)
                            elif source_el.text:
                                # Very old format - try to convert
                                for name in source_el.text.split(", "):
                                    name = name.strip()
                                    source_id = get_source_id_by_name(name)
                                    if source_id:
                                        item_sources.append(get_source_for_rss(source_id))
                                    else:
                                        item_sources.append({
                                            "name": name,
                                            "url": "",
                                            "accuracy": "—", "bias": "—", "speed": "—", "consensus": "—",
                                            "control_type": "unknown", "owners": []
                                        })

                    items.append({
                        "title": item.find("title").text or "",
                        "description": item.find("description").text or "",
                        "sources": item_sources,
                        "pubDate": item.find("pubDate").text or "",
                        "guid": guid
                    })
        except Exception as e:
            log.warning(f"Error parsing existing feed during regeneration: {e}")

    # Trim to max 100 items
    items = items[:100]

    # Build RSS XML (namespaces added via register_namespace above)
    pub_date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    rss = ET.Element("rss", {"version": "2.0"})
    rss.set(f"xmlns:jtf", JTF_NS)
    rss.set(f"xmlns:atom", ATOM_NS)

    channel = ET.SubElement(rss, "channel")

    ET.SubElement(channel, "title").text = "JTF News - Just The Facts"
    ET.SubElement(channel, "link").text = "https://jtfnews.org/"
    ET.SubElement(channel, "description").text = "Verified facts from multiple sources. No opinions. No adjectives. No interpretation. Viewer-supported at github.com/sponsors/larryseyer"
    ET.SubElement(channel, "language").text = "en-us"
    ET.SubElement(channel, "lastBuildDate").text = pub_date

    # Add atom:link for RSS compliance
    ET.SubElement(channel, f"{{{ATOM_NS}}}link", {
        "href": "https://jtfnews.org/feed.xml",
        "rel": "self",
        "type": "application/rss+xml"
    })

    for item_data in items:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = item_data["title"]
        ET.SubElement(item, "description").text = item_data["description"]

        # Write namespaced source elements
        for source_data in item_data.get("sources", []):
            source_el = ET.SubElement(item, f"{{{JTF_NS}}}source", {
                "name": source_data["name"],
                "accuracy": source_data["accuracy"],
                "bias": source_data["bias"],
                "speed": source_data["speed"],
                "consensus": source_data["consensus"],
                "control_type": source_data["control_type"]
            })
            for owner in source_data.get("owners", []):
                ET.SubElement(source_el, f"{{{JTF_NS}}}owner", {
                    "name": owner["name"],
                    "percent": owner["percent"]
                })

        ET.SubElement(item, "pubDate").text = item_data["pubDate"]
        ET.SubElement(item, "guid", isPermaLink="false").text = item_data["guid"]

    # Write with XML declaration
    indent_xml(rss, space="  ")
    tree = ET.ElementTree(rss)
    with open(feed_file, 'wb') as f:
        tree.write(f, encoding="utf-8", xml_declaration=True)

    # Clean up duplicate namespace declarations (ElementTree quirk)
    clean_duplicate_namespaces(feed_file)

    log.info(f"RSS feed regenerated: {len(items)} items with rich source data")
    return True


def add_digest_to_feed(date: str, story_count: int, youtube_id: str):
    """Add daily digest entry to RSS feed with YouTube and archive links.

    Creates a special item with jtf:type="digest" attribute.
    """
    import subprocess

    # Namespace URIs
    JTF_NS = "https://jtfnews.com/rss"
    ATOM_NS = "http://www.w3.org/2005/Atom"

    # Register namespaces for clean XML output
    ET.register_namespace("jtf", JTF_NS)
    ET.register_namespace("atom", ATOM_NS)

    docs_dir = BASE_DIR / "docs"
    feed_file = docs_dir / "feed.xml"

    if not docs_dir.exists():
        log.warning("docs worktree not found, skipping digest feed entry")
        return

    # Create pub date
    pub_date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")

    # Create digest item
    youtube_url = f"https://youtube.com/watch?v={youtube_id}"
    archive_url = f"https://jtfnews.org/archive/{date}.html"

    digest_item = {
        "title": f"[DAILY DIGEST] {date} - {story_count} verified facts",
        "description": f"Daily summary of {story_count} verified facts from {date}.",
        "youtube_url": youtube_url,
        "archive_url": archive_url,
        "pubDate": pub_date,
        "guid": f"digest-{date}"
    }

    # Load existing feed
    if not feed_file.exists():
        log.error("feed.xml not found")
        return

    try:
        tree = ET.parse(feed_file)
        root = tree.getroot()
        channel = root.find("channel")

        # Check if digest for this date already exists — update YouTube link if so
        for item in channel.findall("item"):
            guid_el = item.find("guid")
            if guid_el is not None and guid_el.text == f"digest-{date}":
                link_el = item.find("link")
                if link_el is not None and link_el.text != youtube_url:
                    old_url = link_el.text
                    link_el.text = youtube_url
                    tree.write(feed_file, xml_declaration=True, encoding="UTF-8")
                    log.info(f"Updated digest feed entry for {date}: {old_url} → {youtube_url}")
                    push_to_ghpages([(feed_file, "feed.xml")], f"Update digest YouTube link for {date}")
                else:
                    log.info(f"Digest entry for {date} already exists with correct link")
                return

        # Create new item element with jtf:type attribute
        new_item = ET.Element("item")
        new_item.set(f"{{{JTF_NS}}}type", "digest")

        title_el = ET.SubElement(new_item, "title")
        title_el.text = digest_item["title"]

        desc_el = ET.SubElement(new_item, "description")
        desc_el.text = digest_item["description"]

        # Main link goes to YouTube video
        link_el = ET.SubElement(new_item, "link")
        link_el.text = digest_item["youtube_url"]

        # Archive link as custom element
        archive_el = ET.SubElement(new_item, f"{{{JTF_NS}}}archive")
        archive_el.text = digest_item["archive_url"]

        pubdate_el = ET.SubElement(new_item, "pubDate")
        pubdate_el.text = digest_item["pubDate"]

        guid_el = ET.SubElement(new_item, "guid")
        guid_el.set("isPermaLink", "false")
        guid_el.text = digest_item["guid"]

        # Insert at top of items (after channel metadata)
        # Find position after lastBuildDate
        insert_pos = 0
        for i, child in enumerate(channel):
            if child.tag in ("title", "link", "description", "language", "lastBuildDate", "ttl", "atom:link"):
                insert_pos = i + 1
            elif child.tag.endswith("}link"):  # atom:link with namespace
                insert_pos = i + 1
        channel.insert(insert_pos, new_item)

        # Update lastBuildDate
        last_build = channel.find("lastBuildDate")
        if last_build is not None:
            last_build.text = pub_date

        # Pretty print
        indent_xml(root)

        # Write file
        with open(feed_file, 'wb') as f:
            tree.write(f, encoding="utf-8", xml_declaration=True)

        clean_duplicate_namespaces(feed_file)

        log.info(f"Added digest entry for {date} to RSS feed")

        # Push to GitHub
        try:
            subprocess.run(
                ["git", "-C", str(docs_dir), "add", "feed.xml"],
                capture_output=True, check=True
            )
            subprocess.run(
                ["git", "-C", str(docs_dir), "commit", "-m", f"Add digest entry for {date}"],
                capture_output=True, check=True
            )
            subprocess.run(
                ["git", "-C", str(docs_dir), "push"],
                capture_output=True, check=True
            )
            log.info("Pushed digest feed entry to GitHub")
        except subprocess.CalledProcessError as e:
            log.warning(f"Could not push digest entry to GitHub: {e}")

    except Exception as e:
        log.error(f"Failed to add digest to feed: {e}")


def update_alexa_feed(fact: str, sources: list):
    """Update Alexa Flash Briefing JSON feed and push to GitHub."""
    import subprocess

    docs_dir = BASE_DIR / "docs"
    alexa_file = docs_dir / "alexa.json"
    max_items = 5  # Alexa typically reads top few items

    # Check if docs folder exists
    if not docs_dir.exists():
        log.warning("docs worktree not found, skipping Alexa feed update")
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
        "redirectionUrl": "https://jtfnews.org/"
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

    # Push to GitHub via API
    push_to_ghpages([(alexa_file, "alexa.json")], "Update Alexa feed")


# =============================================================================
# ALERTS
# =============================================================================

@retry_with_backoff(max_retries=2, base_delay=0.5)
def send_alert(message: str, alert_type: str = "general"):
    """Send SMS alert via Twilio with throttling.

    Args:
        message: Alert message to send
        alert_type: Type for throttling (api_failure, credits_low, queue_backup, offline, contradiction, general)
    """
    # Check throttling (unless this is a call from track_api_failure which already checked)
    if alert_type != "api_failure" and not should_send_alert(alert_type):
        log.info(f"Alert throttled ({alert_type}): {message}")
        return

    # Check if Twilio is in degraded mode
    if "twilio" in _degraded_services:
        log.warning(f"Alert (Twilio unavailable): {message}")
        return

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

        # Log API usage for cost tracking
        log_api_usage("twilio", {"sms_count": 1})

        log.warning(f"Alert sent: {message}")
        track_api_failure("twilio", True)

    except Exception as e:
        log.error(f"Failed to send alert: {e}")
        track_api_failure("twilio", False)


# =============================================================================
# STREAM MONITORING
# =============================================================================

HEARTBEAT_FILE = DATA_DIR / "heartbeat.txt"
STREAM_OFFLINE_THRESHOLD = 300  # 5 minutes in seconds
_offline_alert_sent = False  # Only ONE alert per offline event
_midnight_archive_done_for = None  # Idempotency guard: prevents multiple runs in 00:00-00:05 window


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

        # Log API usage for cost tracking
        log_api_usage("claude", {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens
        })

        # Safe JSON parsing with fallback
        result = safe_parse_claude_json(
            response.content[0].text,
            {"contradiction": False, "reason": ""}
        )

        if result.get("contradiction"):
            log.warning(f"Contradiction detected: {result.get('reason', 'unknown')}")
            return True

        track_api_failure("claude", True)
        return False

    except Exception as e:
        log.error(f"Contradiction check failed: {e}")
        track_api_failure("claude", False)
        return False  # Don't block on error


# =============================================================================
# CORRECTIONS SYSTEM
# =============================================================================

CORRECTIONS_FILE = DATA_DIR / "corrections.json"


def load_corrections() -> dict:
    """Load corrections log from disk."""
    if CORRECTIONS_FILE.exists():
        try:
            with open(CORRECTIONS_FILE) as f:
                return json.load(f)
        except:
            pass
    return {"last_updated": None, "corrections": []}


def save_corrections(corrections: dict):
    """Save corrections log to disk and sync to GitHub."""
    corrections["last_updated"] = datetime.now(timezone.utc).isoformat()

    with open(CORRECTIONS_FILE, 'w') as f:
        json.dump(corrections, f, indent=2)

    # Sync to docs for public access
    docs_dir = BASE_DIR / "docs"
    if docs_dir.exists():
        import shutil
        shutil.copy(CORRECTIONS_FILE, docs_dir / "corrections.json")
        log.info("Corrections synced to docs")


def get_recent_stories_for_correction(days: int = 7) -> list:
    """Get recent stories with full metadata for correction checking."""
    stories_file = DATA_DIR / "stories.json"
    all_stories = []

    # Get today's stories
    if stories_file.exists():
        try:
            with open(stories_file) as f:
                data = json.load(f)
                for i, story in enumerate(data.get("stories", [])):
                    # Add index for reference
                    story["_index"] = i
                    story["_date"] = data.get("date", "")
                    all_stories.append(story)
        except:
            pass

    # Also check archived daily logs for recent days
    today = datetime.now(timezone.utc)
    for day_offset in range(1, days):
        check_date = (today - timedelta(days=day_offset)).strftime("%Y-%m-%d")
        log_file = DATA_DIR / f"{check_date}.txt"
        if log_file.exists():
            try:
                with open(log_file) as f:
                    for line_num, line in enumerate(f):
                        if line.startswith("#") or not line.strip():
                            continue
                        parts = line.strip().split("|")
                        if len(parts) >= 4:
                            fact = parts[3].strip()
                            story_id = generate_story_id(check_date, line_num)
                            all_stories.append({
                                "id": story_id,
                                "hash": hashlib.md5(fact.encode()).hexdigest()[:12],
                                "fact": fact,
                                "source": parts[1] if len(parts) > 1 else "",
                                "published_at": f"{check_date}T{parts[0]}:00Z",
                                "status": "published",
                                "_date": check_date,
                                "_from_archive": True
                            })
            except:
                pass

    return all_stories


def detect_correction_needed(new_fact: str, new_sources: list, recent_stories: list) -> dict | None:
    """
    Check if a newly verified fact contradicts a previously published story.

    Unlike check_contradiction() which BLOCKS new facts, this DETECTS when we need
    to issue a correction for an OLD story based on NEW verified information.

    Returns: dict with correction details or None if no correction needed.
    """
    if not recent_stories:
        return None

    # Only check recent published stories (last 20 max)
    check_stories = [s for s in recent_stories if s.get("status") == "published"][-20:]

    if not check_stories:
        return None

    # Build facts list for Claude prompt
    stories_text = "\n".join([
        f"[{s.get('id', 'unknown')}] {s.get('fact', '')}"
        for s in check_stories
    ])

    source_names = ", ".join([s.get("source_name", "") for s in new_sources[:2]])

    prompt = f"""You are checking if NEW VERIFIED INFORMATION contradicts any previously published story.

NEW VERIFIED FACT (confirmed by 2+ unrelated sources: {source_names}):
{new_fact}

PREVIOUSLY PUBLISHED STORIES:
{stories_text}

Check if the new verified fact CONTRADICTS any published story. A correction is needed when:
- The new fact directly contradicts a specific claim in a published story
- The new information makes a published story factually incorrect
- Numbers, names, or key details in the new fact conflict with what was published

A correction is NOT needed for:
- Additional details that supplement but don't contradict
- Updates that extend a story with new developments
- Related but separate events

If a correction IS needed, return JSON:
{{"needs_correction": true, "story_id": "ID of story to correct", "original_fact": "the incorrect fact", "reason": "brief explanation of contradiction", "correction_type": "correction" or "retraction"}}

If NO correction needed, return:
{{"needs_correction": false}}"""

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=CONFIG["claude"]["model"],
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )

        log_api_usage("claude", {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens
        })

        result = safe_parse_claude_json(
            response.content[0].text,
            {"needs_correction": False}
        )

        if result.get("needs_correction"):
            return result

        return None

    except Exception as e:
        log.error(f"Correction detection failed: {e}")
        return None


def issue_correction(story_id: str, original_fact: str, corrected_fact: str,
                     reason: str, correcting_sources: list, correction_type: str = "correction"):
    """
    Issue a correction for a previously published story.

    - Marks the original story as "corrected" in stories.json
    - Preserves original_fact for transparency
    - Logs to corrections.json
    - Generates correction audio announcement
    """
    stories_file = DATA_DIR / "stories.json"
    now_iso = datetime.now(timezone.utc).isoformat()

    # Load current stories
    stories = {"date": "", "stories": []}
    if stories_file.exists():
        try:
            with open(stories_file) as f:
                stories = json.load(f)
        except:
            pass

    # Find and update the story
    story_updated = False
    for story in stories.get("stories", []):
        if story.get("id") == story_id:
            story["status"] = "corrected"
            story["original_fact"] = original_fact
            story["fact"] = corrected_fact
            story["correction"] = {
                "corrected_at": now_iso,
                "type": correction_type,
                "reason": reason,
                "correcting_sources": [s.get("source_name", "") for s in correcting_sources[:2]]
            }
            story_updated = True
            break

    if story_updated:
        with open(stories_file, 'w') as f:
            json.dump(stories, f, indent=2)
        log.info(f"Story {story_id} marked as corrected")

    # Add to corrections log
    corrections = load_corrections()
    source_names = [s.get("source_name", "") for s in correcting_sources[:2]]

    corrections["corrections"].append({
        "story_id": story_id,
        "corrected_at": now_iso,
        "type": correction_type,
        "original_fact": original_fact,
        "corrected_fact": corrected_fact,
        "reason": reason,
        "correcting_sources": source_names
    })

    save_corrections(corrections)
    log.info(f"Correction logged: {story_id} ({correction_type})")

    # Generate correction audio announcement
    generate_correction_audio(
        correction_type=correction_type,
        original_fact=original_fact,
        corrected_fact=corrected_fact,
        sources=source_names
    )

    # Send alert about correction
    send_alert(f"CORRECTION issued for {story_id}: {reason[:50]}")

    # Add to RSS feed with same prominence as regular stories
    add_correction_to_rss(
        correction_type=correction_type,
        original_fact=original_fact,
        corrected_fact=corrected_fact,
        sources=source_names,
        story_id=story_id
    )

    return True


def issue_retraction(story_id: str, original_fact: str, reason: str, sources: list):
    """Issue a full retraction when a story is completely false."""
    stories_file = DATA_DIR / "stories.json"
    now_iso = datetime.now(timezone.utc).isoformat()

    # Load and update story
    stories = {"date": "", "stories": []}
    if stories_file.exists():
        try:
            with open(stories_file) as f:
                stories = json.load(f)
        except:
            pass

    for story in stories.get("stories", []):
        if story.get("id") == story_id:
            story["status"] = "retracted"
            story["original_fact"] = original_fact
            story["fact"] = f"[RETRACTED] {original_fact}"
            story["retraction"] = {
                "retracted_at": now_iso,
                "reason": reason,
                "retracting_sources": [s.get("source_name", "") for s in sources[:2]]
            }
            break

    with open(stories_file, 'w') as f:
        json.dump(stories, f, indent=2)

    # Add to corrections log
    corrections = load_corrections()
    source_names = [s.get("source_name", "") for s in sources[:2]]

    corrections["corrections"].append({
        "story_id": story_id,
        "corrected_at": now_iso,
        "type": "retraction",
        "original_fact": original_fact,
        "corrected_fact": None,
        "reason": reason,
        "correcting_sources": source_names
    })

    save_corrections(corrections)
    log.info(f"Retraction issued: {story_id}")

    # Generate retraction audio
    generate_retraction_audio(original_fact, reason, source_names)

    # Send alert
    send_alert(f"RETRACTION: {story_id} - {reason[:50]}")

    # Add to RSS feed with same prominence as regular stories
    add_correction_to_rss(
        correction_type="retraction",
        original_fact=original_fact,
        corrected_fact=None,
        sources=source_names,
        story_id=story_id
    )

    return True


def generate_correction_audio(correction_type: str, original_fact: str,
                               corrected_fact: str, sources: list):
    """Generate TTS announcement for a correction."""
    source_text = " and ".join(sources) if sources else "new sources"

    # Truncate facts if too long for audio
    orig_short = original_fact[:150] + "..." if len(original_fact) > 150 else original_fact
    corr_short = corrected_fact[:150] + "..." if len(corrected_fact) > 150 else corrected_fact

    announcement = f"Correction. Earlier we reported that {orig_short}. {source_text} now report that {corr_short}."

    # Generate as a one-time announcement (not added to rotation)
    try:
        generate_tts(announcement)
        log.info(f"Correction audio generated: {announcement[:60]}...")
    except Exception as e:
        log.error(f"Failed to generate correction audio: {e}")


def generate_retraction_audio(original_fact: str, reason: str, sources: list):
    """Generate TTS announcement for a retraction."""
    source_text = " and ".join(sources) if sources else "new information"

    orig_short = original_fact[:150] + "..." if len(original_fact) > 150 else original_fact
    reason_short = reason[:100] if len(reason) > 100 else reason

    announcement = f"Retraction. Earlier we reported that {orig_short}. This report was incorrect. {reason_short}. We retract this story."

    try:
        generate_tts(announcement)
        log.info(f"Retraction audio generated: {announcement[:60]}...")
    except Exception as e:
        log.error(f"Failed to generate retraction audio: {e}")


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


# Common first names for gender detection (expanded list for news coverage)
MALE_NAMES = {
    "james", "john", "robert", "michael", "david", "william", "richard", "joseph",
    "thomas", "charles", "christopher", "daniel", "matthew", "anthony", "mark",
    "donald", "steven", "paul", "andrew", "joshua", "kenneth", "kevin", "brian",
    "george", "timothy", "ronald", "edward", "jason", "jeffrey", "ryan", "jacob",
    "gary", "nicholas", "eric", "jonathan", "stephen", "larry", "justin", "scott",
    "brandon", "benjamin", "samuel", "raymond", "gregory", "frank", "alexander",
    "patrick", "jack", "dennis", "jerry", "tyler", "aaron", "jose", "adam", "nathan",
    "henry", "douglas", "zachary", "peter", "kyle", "noah", "ethan", "jeremy",
    "walter", "christian", "keith", "roger", "terry", "austin", "sean", "gerald",
    "carl", "harold", "dylan", "arthur", "lawrence", "jordan", "jesse", "bryan",
    "billy", "bruce", "gabriel", "joe", "logan", "albert", "willie", "alan", "eugene",
    "russell", "vincent", "philip", "bobby", "johnny", "bradley", "roy", "ralph",
    "eugene", "randy", "wayne", "howard", "carlos", "russell", "louis", "harry",
    # International/political figures
    "vladimir", "xi", "emmanuel", "olaf", "justin", "benjamin", "narendra", "rishi",
    "volodymyr", "recep", "jair", "andres", "pedro", "giorgia", "viktor", "mateusz",
    "marco", "pete", "jd", "elon", "jeff", "tim", "sundar", "satya", "jensen"
}

FEMALE_NAMES = {
    "mary", "patricia", "jennifer", "linda", "elizabeth", "barbara", "susan",
    "jessica", "sarah", "karen", "lisa", "nancy", "betty", "margaret", "sandra",
    "ashley", "kimberly", "emily", "donna", "michelle", "dorothy", "carol",
    "amanda", "melissa", "deborah", "stephanie", "rebecca", "sharon", "laura",
    "cynthia", "kathleen", "amy", "angela", "shirley", "anna", "brenda", "pamela",
    "emma", "nicole", "helen", "samantha", "katherine", "christine", "debra",
    "rachel", "carolyn", "janet", "catherine", "maria", "heather", "diane", "ruth",
    "julie", "olivia", "joyce", "virginia", "victoria", "kelly", "lauren", "christina",
    "joan", "evelyn", "judith", "megan", "andrea", "cheryl", "hannah", "jacqueline",
    "martha", "gloria", "teresa", "ann", "sara", "madison", "frances", "kathryn",
    "janice", "jean", "abigail", "alice", "judy", "sophia", "grace", "denise",
    "amber", "doris", "marilyn", "danielle", "beverly", "isabella", "theresa",
    "diana", "natalie", "brittany", "charlotte", "marie", "kayla", "alexis", "lori",
    # International/political figures
    "angela", "ursula", "christine", "giorgia", "sanna", "jacinda", "kamala",
    "hillary", "nancy", "nikki", "tulsi", "karine", "janet", "gina"
}


def fix_repeated_subject(new_detail: str, existing_fact: str) -> str:
    """Replace repeated subject with pronoun for natural flow.

    If new_detail starts with the same subject as existing_fact,
    replace it with He/She/They for readability when concatenated.
    """
    if not new_detail or not existing_fact:
        return new_detail

    # Pattern to extract title + name at start of sentence
    # Matches: "Title Name Name" or just "Name Name"
    title_pattern = r'^((?:President|Secretary of State|Senator|Representative|Governor|Minister|Prime Minister|Chancellor|Director|Chief|General|Admiral|Mayor|Attorney General|Press Secretary|Spokesperson|Ambassador|Commissioner|Chairman|Chairwoman|CEO|CFO|CTO|Speaker|Leader|Deputy|Vice President|White House[^,]*?)\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)'

    # Extract subject from existing fact
    existing_match = re.match(title_pattern, existing_fact)
    if not existing_match:
        return new_detail

    existing_title = existing_match.group(1) or ""
    existing_name = existing_match.group(2)
    existing_subject = (existing_title + existing_name).strip()

    # Check if new_detail starts with the same or similar subject
    new_match = re.match(title_pattern, new_detail)
    if not new_match:
        return new_detail

    new_title = new_match.group(1) or ""
    new_name = new_match.group(2)
    new_subject = (new_title + new_name).strip()

    # Check for subject match (same name, with or without title)
    if existing_name.lower() != new_name.lower():
        return new_detail

    # Determine pronoun based on first name
    first_name = existing_name.split()[0].lower()

    if first_name in MALE_NAMES:
        pronoun = "He"
    elif first_name in FEMALE_NAMES:
        pronoun = "She"
    else:
        # Default to "They" for unknown/ambiguous names
        pronoun = "They"

    # Replace the subject with the pronoun
    fixed_detail = re.sub(f'^{re.escape(new_subject)}\\s*', f'{pronoun} ', new_detail)

    log.debug(f"Fixed repeated subject: '{new_subject}' -> '{pronoun}'")
    return fixed_detail


def extract_new_details(new_fact: str, existing_fact: str) -> str | None:
    """Use Claude to extract only NEW information from the new fact."""
    prompt = f"""Compare these two news facts about the SAME event.

EXISTING (already published): {existing_fact}

NEW SOURCE: {new_fact}

Extract ONLY genuinely new, verifiable information from NEW SOURCE that is NOT already in EXISTING.
Do NOT include anything already stated or implied in EXISTING.
Do NOT rephrase existing information.

IMPORTANT: The new detail will be APPENDED to the existing fact. Do NOT repeat the subject
(person/organization/entity) if it's already established in EXISTING. Use pronouns or start
with the new action/information directly so it reads naturally when concatenated.

Example:
- EXISTING: "Secretary of State Marco Rubio announced the alliance."
- BAD new_detail: "Secretary of State Marco Rubio will visit Europe." (repeats subject)
- GOOD new_detail: "He will visit Europe next week." (uses pronoun)

If there is genuinely new information, return it as a short factual sentence that continues naturally from EXISTING.
If there is NO new information, return exactly: NO_NEW_INFO

Return JSON: {{"new_detail": "the new sentence" or "NO_NEW_INFO"}}"""

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=CONFIG["claude"]["model"],
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}]
        )

        # Log API usage for cost tracking
        log_api_usage("claude", {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens
        })

        # Safe JSON parsing with fallback
        result = safe_parse_claude_json(
            response.content[0].text,
            {"new_detail": "NO_NEW_INFO"}
        )
        new_detail = result.get("new_detail", "NO_NEW_INFO")

        if new_detail == "NO_NEW_INFO" or not new_detail:
            track_api_failure("claude", True)
            return None

        track_api_failure("claude", True)
        # Post-process to fix repeated subjects with pronouns
        new_detail = fix_repeated_subject(new_detail, existing_fact)
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
        new_source_text = f"{new_source['source_name']} {get_compact_scores(new_source['source_id'])}"
        if new_source_text not in story.get("source", ""):
            story["source"] = f"{story['source']} · {new_source_text}"

        # Regenerate audio for updated fact using hash-based naming
        new_audio_id = get_story_audio_id(updated_fact)
        new_audio_file = generate_tts(updated_fact, story_id=new_audio_id)

        if new_audio_file:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            story["audio"] = f"../audio/archive/{today}/{new_audio_file}"

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
    """Delete raw data files and old videos older than N days."""
    import glob
    from datetime import timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_str = cutoff.strftime("%Y-%m-%d")

    deleted = 0

    # Find dated files in data directory
    for pattern in ["*.txt", "*.json"]:
        for filepath in DATA_DIR.glob(pattern):
            filename = filepath.name

            # Skip non-dated files and config files
            if not any(c.isdigit() for c in filename):
                continue
            if filename == "digest-config.json":
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

    # Clean up old daily digest videos (they're large!)
    if VIDEO_DIR.exists():
        for filepath in VIDEO_DIR.glob("*.mp4"):
            filename = filepath.name
            try:
                match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
                if match:
                    file_date = match.group(1)
                    if file_date < cutoff_str:
                        filepath.unlink()
                        deleted += 1
                        log.info(f"Deleted old video: {filename}")
            except Exception as e:
                log.error(f"Error checking video {filename}: {e}")

    # Clean up old audio archives
    audio_archive_dir = AUDIO_DIR / "archive"
    if audio_archive_dir.exists():
        for date_dir in audio_archive_dir.iterdir():
            if date_dir.is_dir() and re.match(r'\d{4}-\d{2}-\d{2}', date_dir.name):
                if date_dir.name < cutoff_str:
                    try:
                        shutil.rmtree(date_dir)
                        deleted += 1
                        log.info(f"Deleted old audio archive: {date_dir.name}")
                    except Exception as e:
                        log.error(f"Error deleting audio archive {date_dir.name}: {e}")

    if deleted > 0:
        log.info(f"Cleanup complete: {deleted} old files/folders deleted")


# =============================================================================
# DAILY VIDEO GENERATION
# =============================================================================

# Directory for daily summary videos
VIDEO_DIR = BASE_DIR / "video"
VIDEO_DIR.mkdir(exist_ok=True)


def archive_audio_files(date: str) -> list:
    """Archive legacy audio files and return all audio files for the date.

    New hash-based audio files are already written directly to archive/YYYY-MM-DD/
    by generate_tts(), so this function only needs to:
    1. Move any legacy audio_*.mp3 files from audio/ to archive/
    2. Return a list of all audio files in the archive for this date

    Args:
        date: Date string in YYYY-MM-DD format

    Returns:
        List of all archived file paths for this date
    """
    archive_dir = AUDIO_DIR / "archive" / date
    archive_dir.mkdir(parents=True, exist_ok=True)

    moved_count = 0

    # Archive legacy format (audio_*.mp3) - these are the ones that can be overwritten
    for audio_file in sorted(AUDIO_DIR.glob("audio_*.mp3"),
                             key=lambda f: int(f.stem.split('_')[1]) if f.stem.split('_')[1].isdigit() else 0):
        dest = archive_dir / audio_file.name
        try:
            shutil.move(str(audio_file), str(dest))
            moved_count += 1
            log.debug(f"Archived legacy audio: {audio_file.name} -> {archive_dir.name}/")
        except Exception as e:
            log.error(f"Failed to archive {audio_file}: {e}")

    if moved_count > 0:
        log.info(f"Archived {moved_count} legacy audio files to {archive_dir}")

    # Return ALL audio files in the archive (both legacy and hash-based)
    all_archived = [str(f) for f in archive_dir.glob("*.mp3")]
    log.info(f"Archive {date} contains {len(all_archived)} audio files")

    return all_archived


def get_audio_duration(path: str) -> float:
    """Get actual audio duration in seconds using mutagen.

    Args:
        path: Path to audio file

    Returns:
        Duration in seconds, or 15.0 as fallback
    """
    try:
        from mutagen.mp3 import MP3
        audio = MP3(path)
        duration = audio.info.length
        log.debug(f"Audio duration for {path}: {duration:.1f}s")
        return duration
    except ImportError:
        log.warning("mutagen not installed, using fallback duration")
        return 15.0
    except Exception as e:
        log.warning(f"Could not read duration for {path}: {e}")
        return 15.0


def get_current_season() -> str:
    """Determine current season based on date (Northern Hemisphere).

    Returns:
        Season name: 'winter', 'spring', 'summer', or 'fall'
    """
    month = datetime.now().month
    if month in (3, 4, 5):
        return 'spring'
    elif month in (6, 7, 8):
        return 'summer'
    elif month in (9, 10, 11):
        return 'fall'
    else:  # 12, 1, 2
        return 'winter'


def get_seasonal_backgrounds(count: int = 50) -> list:
    """Get a list of seasonal background images for video.

    Args:
        count: Number of images to return

    Returns:
        List of image paths, shuffled for variety
    """
    import random

    season = get_current_season()
    season_dir = BASE_DIR / "media" / season

    if not season_dir.exists():
        log.warning(f"Season directory not found: {season_dir}")
        return []

    # Find all PNG images in the season folder
    images = list(season_dir.glob("*.png"))

    if not images:
        log.warning(f"No images found in {season_dir}")
        return []

    # Shuffle and return requested count
    random.shuffle(images)
    return [str(img) for img in images[:count]]


def load_stories_for_date(date: str) -> list:
    """Load stories from the daily log file for a specific date.

    Tries local file first, then falls back to archived .gz file.

    Args:
        date: Date string in YYYY-MM-DD format

    Returns:
        List of story dicts with 'fact' and 'source' fields
    """
    log_file = DATA_DIR / f"{date}.txt"
    lines = []

    # Try local file first
    if log_file.exists():
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            log.error(f"Error reading local log for {date}: {e}")
            return []
    else:
        # Fall back to archived file
        year = date[:4]
        archive_file = BASE_DIR / "docs" / "archive" / year / f"{date}.txt.gz"
        if archive_file.exists():
            log.info(f"Loading from archive: {archive_file}")
            try:
                with gzip.open(archive_file, 'rt', encoding='utf-8') as f:
                    lines = f.readlines()
            except Exception as e:
                log.error(f"Error reading archive for {date}: {e}")
                return []
        else:
            log.debug(f"No daily log found for {date} (checked local and archive)")
            return []

    stories = []

    # Parse daily log format (pipe-delimited):
    # Old (5 fields): timestamp|sources|ratings|urls|fact
    # New (6 fields): timestamp|sources|ratings|urls|audio|fact
    # Example:
    # 2026-02-15T00:08:14+00:00|BBC News,Reuters|9.5*,9.9*|url1,url2|audio_0.mp3|The fact here.

    for line in lines:
        line = line.strip()

        # Skip comments and empty lines
        if not line or line.startswith('#'):
            continue

        # Parse pipe-delimited format
        parts = line.split('|')
        if len(parts) >= 6:
            # New format with audio field
            timestamp = parts[0]
            sources = parts[1]
            audio = parts[4]  # e.g., "audio_0.mp3"
            fact = parts[5]
            stories.append({
                'fact': fact,
                'source': sources,
                'timestamp': timestamp,
                'audio': audio
            })
        elif len(parts) >= 5:
            # Old format without audio - use index-based fallback
            timestamp = parts[0]
            sources = parts[1]
            fact = parts[4]
            stories.append({
                'fact': fact,
                'source': sources,
                'timestamp': timestamp,
                'audio': None
            })

    log.info(f"Loaded {len(stories)} stories from {date}")
    return stories


def get_youtube_credentials():
    """Load YouTube API credentials from environment.

    Returns:
        Tuple of (client_secrets_file, playlist_id) or (None, None) if not configured
    """
    client_secrets = os.getenv("YOUTUBE_CLIENT_SECRETS_FILE")
    playlist_id = os.getenv("YOUTUBE_PLAYLIST_ID")

    if not client_secrets or not playlist_id:
        log.warning("YouTube credentials not configured in .env")
        return None, None

    secrets_path = BASE_DIR / client_secrets
    if not secrets_path.exists():
        log.warning(f"YouTube client secrets file not found: {secrets_path}")
        return None, None

    return str(secrets_path), playlist_id


def get_authenticated_youtube_service():
    """Get authenticated YouTube API service.

    Returns:
        YouTube API service object, or None if authentication fails
    """
    client_secrets_file, _ = get_youtube_credentials()
    if not client_secrets_file:
        return None

    token_file = DATA_DIR / "youtube_tokens.json"

    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        SCOPES = ['https://www.googleapis.com/auth/youtube.upload',
                  'https://www.googleapis.com/auth/youtube']

        creds = None

        # Load existing credentials
        if token_file.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
            except Exception as e:
                log.warning(f"Failed to load YouTube tokens: {e}")

        # Refresh or get new credentials
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                log.warning(f"Failed to refresh YouTube credentials: {e}")
                creds = None

        if not creds or not creds.valid:
            log.warning("YouTube credentials need re-authentication")
            log.warning("Run: python setup_youtube.py")
            return None

        # Save refreshed credentials
        with open(token_file, 'w') as f:
            f.write(creds.to_json())

        return build('youtube', 'v3', credentials=creds)

    except ImportError:
        log.error("Google API libraries not installed. Run: pip install google-api-python-client google-auth-oauthlib")
        return None
    except Exception as e:
        log.error(f"Failed to authenticate with YouTube: {e}")
        return None


@retry_with_backoff(max_retries=3, base_delay=30.0)
def upload_to_youtube(video_path: str, date: str) -> str:
    """Upload video to YouTube and add to playlist.

    Args:
        video_path: Path to video file
        date: YYYY-MM-DD date string for title

    Returns:
        YouTube video ID on success, None on failure
    """
    youtube = get_authenticated_youtube_service()
    if not youtube:
        log.error("Could not authenticate with YouTube")
        return None

    _, playlist_id = get_youtube_credentials()

    try:
        from googleapiclient.http import MediaFileUpload

        # Video metadata
        body = {
            'snippet': {
                'title': f'JTF News Daily Digest - {date}',
                'description': f'Daily summary of verified facts from {date}.\n\n'
                              'JTF News reports only verified facts from 2+ unrelated sources.\n'
                              'No opinions. No adjectives. No interpretation.\n\n'
                              'Learn more: https://jtfnews.org/',
                'tags': ['news', 'facts', 'daily summary', 'JTF News', 'just the facts'],
                'categoryId': '25'  # News & Politics
            },
            'status': {
                'privacyStatus': 'public',
                'license': 'creativeCommon',  # CC BY license
                'selfDeclaredMadeForKids': False
            }
        }

        # Upload video
        media = MediaFileUpload(
            video_path,
            mimetype='video/mp4',
            resumable=True,
            chunksize=1024*1024  # 1MB chunks
        )

        log.info(f"Uploading video to YouTube: {video_path}")

        request = youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                log.info(f"Upload progress: {int(status.progress() * 100)}%")

        video_id = response['id']
        log.info(f"Video uploaded successfully: {video_id}")

        # Add to playlist
        if playlist_id:
            try:
                youtube.playlistItems().insert(
                    part='snippet',
                    body={
                        'snippet': {
                            'playlistId': playlist_id,
                            'resourceId': {
                                'kind': 'youtube#video',
                                'videoId': video_id
                            }
                        }
                    }
                ).execute()
                log.info(f"Added video to playlist: {playlist_id}")
            except Exception as e:
                log.warning(f"Failed to add video to playlist: {e}")
                # Non-critical - video is still uploaded

        # Set custom thumbnail
        thumbnail_path = BASE_DIR / "web" / "assets" / "png" / "thumbnail-youtube-1280x720.png"
        if thumbnail_path.exists():
            try:
                from googleapiclient.http import MediaFileUpload as ThumbnailUpload
                youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=ThumbnailUpload(str(thumbnail_path), mimetype='image/png')
                ).execute()
                log.info(f"Set custom thumbnail for video: {video_id}")
            except Exception as e:
                log.warning(f"Failed to set thumbnail: {e}")
                # Non-critical - video is still uploaded with auto-generated thumbnail
        else:
            log.debug(f"No custom thumbnail found at {thumbnail_path}")

        return video_id

    except Exception as e:
        log.error(f"YouTube upload failed: {e}")
        raise  # Let retry_with_backoff handle retries


# =============================================================================
# OBS WEBSOCKET CONTROL
# =============================================================================

def get_obs_connection():
    """Get OBS WebSocket connection.

    Returns:
        obsws object or None if connection fails
    """
    obs_host = os.getenv("OBS_WEBSOCKET_HOST", "localhost")
    obs_port = int(os.getenv("OBS_WEBSOCKET_PORT", "4449"))
    obs_password = os.getenv("OBS_WEBSOCKET_PASSWORD", "")

    try:
        from obswebsocket import obsws, requests as obs_requests
        ws = obsws(obs_host, obs_port, obs_password, legacy=True)
        ws.connect()
        log.info(f"Connected to OBS WebSocket at {obs_host}:{obs_port}")
        return ws
    except ImportError:
        log.error("obs-websocket-py not installed. Run: pip install obs-websocket-py")
        return None
    except Exception as e:
        log.error(f"Failed to connect to OBS: {e}")
        return None


def obs_switch_scene(ws, scene_name: str) -> bool:
    """Switch OBS to a specific scene.

    Args:
        ws: OBS WebSocket connection
        scene_name: Name of the scene to switch to

    Returns:
        True on success, False on failure
    """
    try:
        from obswebsocket import requests as obs_requests
        # v4 protocol: SetCurrentScene with scene-name parameter
        ws.call(obs_requests.SetCurrentScene(**{'scene-name': scene_name}))
        log.info(f"Switched to scene: {scene_name}")
        return True
    except Exception as e:
        log.error(f"Failed to switch scene to {scene_name}: {e}")
        return False


def obs_start_recording(ws) -> bool:
    """Start OBS recording.

    Returns:
        True on success, False on failure
    """
    try:
        from obswebsocket import requests as obs_requests
        # v4 protocol: StartRecording
        ws.call(obs_requests.StartRecording())
        log.info("OBS recording started")
        return True
    except Exception as e:
        log.error(f"Failed to start recording: {e}")
        return False


def obs_stop_recording(ws) -> str:
    """Stop OBS recording and get output path.

    Waits for OBS to fully finalize the file before returning.

    Returns:
        Path to recorded file, or None on failure
    """
    try:
        from obswebsocket import requests as obs_requests
        import glob
        import subprocess

        # v4 protocol: Get recording folder first
        folder_response = ws.call(obs_requests.GetRecordingFolder())
        rec_folder = folder_response.datain.get('rec-folder', '/Users/larryseyer/Downloads')

        # Stop recording
        ws.call(obs_requests.StopRecording())
        log.info("OBS recording stop requested")

        # Give OBS time to begin the stop process before polling
        time.sleep(5)

        # Wait for OBS to report recording has stopped (max 60 seconds)
        max_wait = 60
        recording_confirmed_stopped = False
        for i in range(max_wait):
            time.sleep(1)
            try:
                status = ws.call(obs_requests.GetRecordingStatus())
                is_recording = status.datain.get('isRecording', False)
                if not is_recording:
                    log.info(f"OBS confirmed recording stopped after {i+1}s")
                    recording_confirmed_stopped = True
                    break
                else:
                    if (i + 1) % 10 == 0:
                        log.info(f"OBS still finalizing recording... {i+1}s")
            except Exception as e:
                # Don't break on exceptions — OBS may be in a transitional state
                log.debug(f"GetRecordingStatus exception (may be transitional): {e}")
                continue
        else:
            log.warning("OBS still recording after 60s, proceeding anyway")

        # Extra settling time after OBS reports stopped
        if recording_confirmed_stopped:
            log.info("Waiting 5s for OBS to flush file buffers...")
            time.sleep(5)

        # Find the newest mp4 file
        mp4_files = glob.glob(f"{rec_folder}/*.mp4")
        if not mp4_files:
            log.warning(f"No mp4 files found in {rec_folder}")
            return None

        output_path = max(mp4_files, key=os.path.getmtime)
        log.info(f"Found recording: {output_path}")

        # Wait for file to stabilize (size stops changing) - max 90 seconds
        log.info("Waiting for OBS to finalize file...")
        last_size = -1
        stable_count = 0
        for i in range(90):
            time.sleep(1)
            try:
                current_size = os.path.getsize(output_path)
                if current_size == last_size:
                    stable_count += 1
                    if stable_count >= 5:  # Size stable for 5 seconds
                        log.info(f"File stabilized after {i+1}s ({current_size / 1024 / 1024:.1f}MB)")
                        break
                else:
                    stable_count = 0
                    last_size = current_size
                    if (i + 1) % 10 == 0:
                        log.info(f"File still writing... {current_size / 1024 / 1024:.1f}MB after {i+1}s")
            except OSError:
                pass  # File might be locked
        else:
            log.warning("File size still changing after 90s, proceeding anyway")

        # Verify the file is valid (has moov atom)
        try:
            result = subprocess.run(
                ['ffprobe', '-v', 'error', output_path],
                capture_output=True, text=True, timeout=30
            )
            if 'moov atom not found' in result.stderr or result.returncode != 0:
                log.error(f"Video file may be corrupt (moov atom issue): {result.stderr}")
                log.error("OBS may not have finished writing. Waiting 30s and retrying...")
                time.sleep(30)
                result = subprocess.run(
                    ['ffprobe', '-v', 'error', output_path],
                    capture_output=True, text=True, timeout=30
                )
                if 'moov atom not found' in result.stderr or result.returncode != 0:
                    log.error(f"Video file still corrupt after retry: {result.stderr}")
                    return None
                else:
                    log.info("Video file validated on retry")
            else:
                log.info("Video file validated successfully")
        except Exception as e:
            log.warning(f"Could not validate video file: {e}")

        return output_path
    except Exception as e:
        log.error(f"Failed to stop recording: {e}")
        return None


def obs_get_recording_status(ws) -> dict:
    """Get current OBS recording status.

    Returns:
        Dict with recording status info
    """
    try:
        from obswebsocket import requests as obs_requests
        # v4 protocol: GetRecordingStatus with different field names
        response = ws.call(obs_requests.GetRecordingStatus())
        is_recording = response.datain.get('isRecording', False)
        log.debug(f"Recording status: isRecording={is_recording}")
        return {
            'active': is_recording,
            'paused': response.datain.get('isRecordingPaused', False),
            'duration': response.datain.get('recordTimecode', '00:00:00'),
            'bytes': response.datain.get('recordingBytes', 0)
        }
    except Exception as e:
        log.error(f"Failed to get recording status: {e}")
        # On error, assume recording stopped to avoid infinite loop
        return {'active': False}


def obs_refresh_browser_source(ws, source_name: str, url: str = None) -> bool:
    """Refresh a browser source, optionally with a new URL.

    Args:
        ws: OBS WebSocket connection
        source_name: Name of the browser source
        url: Optional new URL to load

    Returns:
        True on success, False on failure
    """
    try:
        from obswebsocket import requests as obs_requests

        if url:
            # v4 protocol: SetSourceSettings with sourceName and sourceSettings
            ws.call(obs_requests.SetSourceSettings(
                sourceName=source_name,
                sourceSettings={'url': url}
            ))

        # v4 protocol: RefreshBrowserSource
        ws.call(obs_requests.RefreshBrowserSource(sourceName=source_name))

        log.info(f"Refreshed browser source: {source_name}")
        return True
    except Exception as e:
        log.error(f"Failed to refresh browser source {source_name}: {e}")
        return False


def estimate_digest_duration(stories: list, audio_files: list, has_intro_outro: bool = False) -> float:
    """Calculate precise duration of daily digest in seconds.

    Uses actual audio file durations for accuracy.

    Args:
        stories: List of stories
        audio_files: List of audio file paths (may include intro/outro)
        has_intro_outro: Whether intro/outro audio is included in audio_files

    Returns:
        Estimated duration in seconds
    """
    total_duration = 0.0
    gap_time = 2.0  # Gap between stories (matches HTML GAP_BETWEEN_STORIES)
    lower_third_transition = 0.8  # CSS transition for lower third show/hide
    title_card_transition = 1.0   # CSS transition for title card show/hide
    title_hold_time = 3.0         # Hold title screen after audio ends

    for audio_file in audio_files:
        duration = get_audio_duration(audio_file)
        total_duration += duration
        log.debug(f"Audio {audio_file}: {duration:.1f}s")

    # Per-story: lower third fade in + fade out
    total_duration += lower_third_transition * 2 * len(stories)

    # Gaps between stories
    if len(stories) > 1:
        total_duration += gap_time * (len(stories) - 1)

    if has_intro_outro:
        # Page startup delay
        total_duration += 5.0
        # Intro: fade in + hold after audio + fade out
        total_duration += title_card_transition + title_hold_time + title_card_transition
        # Outro: 1s pause + fade in + hold after audio + fade out
        total_duration += 1.0 + title_card_transition + title_hold_time + title_card_transition
    else:
        total_duration += 20.0

    log.info(f"Total audio: {total_duration:.1f}s ({len(audio_files)} files)")

    return total_duration


def generate_and_upload_daily_summary(date: str):
    """Orchestrate daily digest recording and upload via OBS.

    This is the main entry point called from check_midnight_archive().
    It switches OBS to the daily-digest scene, records the playback,
    then uploads to YouTube.

    Args:
        date: YYYY-MM-DD date string
    """
    log.info(f"Starting daily digest for {date}")

    # Track digest status for dashboard
    update_digest_status(date, status="in_progress", upload_status="pending", error_message=None)

    # Load stories for the date
    stories = load_stories_for_date(date)
    if not stories:
        log.info(f"No stories found for {date}, skipping digest")
        update_digest_status(date, status="no_stories", story_count=0)
        return

    # Find archived audio directory
    archive_dir = AUDIO_DIR / "archive" / date
    if not archive_dir.exists():
        log.warning(f"No audio archive found for {date}")
        return

    # Build stories list with verified audio files
    # Priority: 1) hash-based, 2) stored filename from log, 3) index fallback
    stories_data = []
    audio_files = []

    for i, story in enumerate(stories):
        fact = story.get("fact", "")
        audio_path = None

        # Priority 1: Hash-based filename (always correct if exists)
        # This takes priority because hash guarantees content match
        if fact:
            fact_hash = get_story_hash(fact)
            hash_candidate = archive_dir / f"{fact_hash}.mp3"
            if hash_candidate.exists():
                audio_path = hash_candidate
                log.debug(f"Story {i}: Using hash-based audio: {fact_hash}.mp3")

        # Priority 2: Stored audio filename from log (for new hash-based logs)
        # Only use if it's a hash-based filename, not legacy audio_*.mp3
        if not audio_path:
            stored_audio = story.get("audio")
            if stored_audio and not stored_audio.startswith("audio_"):
                candidate = archive_dir / stored_audio
                if candidate.exists():
                    audio_path = candidate
                    log.debug(f"Story {i}: Using stored hash audio: {stored_audio}")

        # Priority 3: Index-based fallback (legacy, may be wrong)
        if not audio_path:
            index_candidate = archive_dir / f"audio_{i}.mp3"
            if index_candidate.exists():
                audio_path = index_candidate
                log.debug(f"Story {i}: Using index-based fallback: audio_{i}.mp3")

        if audio_path:
            # Format source names with ratings for display
            raw_source = story.get("source", "")
            formatted_source = format_source_names_with_ratings(raw_source) if raw_source else ""

            stories_data.append({
                "fact": fact,
                "source": formatted_source,
                "timestamp": story.get("timestamp", ""),
                "audioPath": str(audio_path)
            })
            audio_files.append(str(audio_path))
        else:
            log.warning(f"Story {i}: No audio file found for: {fact[:50]}...")

    if not stories_data:
        log.warning(f"No stories with valid audio for {date}")
        return

    log.info(f"Found {len(stories_data)} stories with valid audio out of {len(stories)} total")

    # Generate intro and outro audio
    # Parse the date string to datetime for audio generation
    digest_date = datetime.strptime(date, "%Y-%m-%d")

    intro_audio = generate_intro_audio(digest_date)
    outro_audio = generate_outro_audio(digest_date)

    intro_audio_path = None
    outro_audio_path = None

    if intro_audio:
        intro_audio_path = str(archive_dir / intro_audio)
        log.info(f"Generated intro audio: {intro_audio}")
    else:
        log.warning("Failed to generate intro audio")

    if outro_audio:
        outro_audio_path = str(archive_dir / outro_audio)
        log.info(f"Generated outro audio: {outro_audio}")
    else:
        log.warning("Failed to generate outro audio")

    # Write config file for the daily-digest.html page
    config_data = {
        "date": date,
        "intro_audio": intro_audio_path,
        "outro_audio": outro_audio_path
    }
    config_file = DATA_DIR / "digest-config.json"
    with open(config_file, 'w') as f:
        json.dump(config_data, f, indent=2)

    # Write stories to JS file (avoids CORS issues with file:// URLs)
    stories_js_file = DATA_DIR / "digest-stories.js"
    with open(stories_js_file, 'w') as f:
        f.write(f"// Auto-generated digest stories for {date}\n")
        f.write(f"window.DIGEST_DATE = '{date}';\n")
        f.write(f"window.DIGEST_INTRO_AUDIO = {json.dumps(intro_audio_path)};\n")
        f.write(f"window.DIGEST_OUTRO_AUDIO = {json.dumps(outro_audio_path)};\n")
        f.write(f"window.DIGEST_STORIES = {json.dumps(stories_data, indent=2)};\n")
    log.info(f"Wrote digest config and stories for {date}")

    # Estimate duration for recording timeout (include intro/outro)
    all_audio_files = audio_files.copy()
    if intro_audio_path:
        all_audio_files.insert(0, intro_audio_path)
    if outro_audio_path:
        all_audio_files.append(outro_audio_path)
    estimated_duration = estimate_digest_duration(stories_data, all_audio_files, has_intro_outro=True)
    log.info(f"Estimated digest duration: {estimated_duration:.0f} seconds")

    # Get OBS connection
    ws = get_obs_connection()
    if not ws:
        error_msg = "Cannot connect to OBS WebSocket - skipping daily digest"
        log.error(error_msg)
        update_digest_status(date, status="skipped", error_message=error_msg)
        return

    # Get scene names from environment
    digest_scene = os.getenv("OBS_DIGEST_SCENE", "DailyDigest")
    normal_scene = os.getenv("OBS_NORMAL_SCENE", "JTF News")
    browser_source = os.getenv("OBS_DIGEST_BROWSER_SOURCE", "Daily Digest Browser")

    try:
        black_scene = os.getenv("OBS_BLACK_SCENE", "Black")
        digest_url = f"file://{BASE_DIR}/web/daily-digest.html?date={date}"

        # 1. Switch to Black
        obs_switch_scene(ws, black_scene)
        obs_refresh_browser_source(ws, browser_source, digest_url)

        # 2. Wait for scene to load
        time.sleep(1)

        # 3. Start recording
        if not obs_start_recording(ws):
            raise Exception("Failed to start OBS recording")

        # 4. Switch to DailyDigest
        if not obs_switch_scene(ws, digest_scene):
            raise Exception(f"Failed to switch to scene: {digest_scene}")

        # Wait for digest to complete
        # Using precise audio duration + buffer for older hardware
        max_wait = int(estimated_duration) + 30  # 30s safety margin for slow machines
        elapsed = 0
        poll_interval = 5  # Poll more frequently for responsiveness

        log.info(f"Recording digest for {estimated_duration:.0f}s (max wait: {max_wait}s)")

        while elapsed < max_wait:
            time.sleep(poll_interval)
            elapsed += poll_interval

            status = obs_get_recording_status(ws)
            if not status.get('active'):
                log.info("Recording stopped externally")
                break

            # Log progress every 30 seconds
            if elapsed % 30 == 0:
                remaining = max_wait - elapsed
                log.info(f"Recording... {elapsed}s elapsed, ~{remaining}s remaining")

        # 5. Switch to Black
        obs_switch_scene(ws, black_scene)

        # 6. Wait for scene to load
        time.sleep(1)

        # 7. Stop recording
        recording_path = obs_stop_recording(ws)

        # 8. Back to normal scene
        obs_switch_scene(ws, normal_scene)

        # Close OBS connection
        ws.disconnect()

        if not recording_path:
            raise Exception("Failed to get recording output path")

        log.info(f"Digest recorded: {recording_path}")

        # Copy to our video folder with standard name
        # OBS is configured to output MP4 directly (Settings → Output → Recording Format → mp4)
        video_path = VIDEO_DIR / f"{date}-daily-digest.mp4"
        shutil.copy(recording_path, video_path)

        log.info(f"Video saved to: {video_path}")

        # Trim silence from start and end of video
        if trim_video_silence(str(video_path)):
            log.info("Video silence trimmed successfully")
        else:
            log.warning("Video silence trimming failed, using original recording")

        # Update digest status with recording details
        update_digest_status(
            date,
            status="success",
            story_count=len(stories_data),
            duration_seconds=int(estimated_duration),
            video_path=str(video_path)
        )

        # Delete original OBS recording from Downloads to save space
        try:
            Path(recording_path).unlink()
            log.info(f"Deleted original recording: {recording_path}")
        except Exception as e:
            log.warning(f"Could not delete original recording: {e}")

        # Upload to YouTube
        _upload_video_to_youtube(str(video_path), date)

    except Exception as e:
        log.error(f"Daily digest recording failed: {e}")
        send_alert(f"Daily digest recording failed for {date}: {e}")
        update_digest_status(date, status="failed", error_message=str(e))

        # Try to clean up OBS state
        try:
            obs_stop_recording(ws)
            obs_switch_scene(ws, normal_scene)
            ws.disconnect()
        except:
            pass


def trim_video_silence(video_path: str) -> bool:
    """Trim trailing silence from video by cutting both audio and video together.

    Pass 1: Detects silence boundaries using ffmpeg silencedetect.
    Pass 2: Trims both streams at those timestamps so they stay in sync.

    Only trims silence at the END of the video (dead air after last story).

    Args:
        video_path: Path to the video file to trim (will be modified in place)

    Returns:
        True if trimming succeeded, False otherwise
    """
    import subprocess
    import re

    video_path = Path(video_path)
    if not video_path.exists():
        log.error(f"Video file not found for trimming: {video_path}")
        return False

    try:
        # Pass 1: Detect silence regions using silencedetect
        # -50dB threshold, minimum 0.3s silence duration
        detect_cmd = [
            'ffmpeg', '-i', str(video_path),
            '-af', 'silencedetect=noise=-50dB:d=0.3',
            '-f', 'null', '-'
        ]

        log.info(f"Detecting silence in video: {video_path}")
        result = subprocess.run(detect_cmd, capture_output=True, text=True, timeout=300)

        # silencedetect outputs to stderr
        output = result.stderr

        # Find all silence_start timestamps
        silence_starts = re.findall(r'silence_start: ([\d.]+)', output)

        if not silence_starts:
            log.info("No trailing silence detected, skipping trim")
            return True

        # Get total duration
        duration_match = re.search(r'Duration: (\d+):(\d+):(\d+\.\d+)', output)
        if not duration_match:
            log.warning("Could not determine video duration, skipping trim")
            return True

        h, m, s = duration_match.groups()
        total_duration = int(h) * 3600 + int(m) * 60 + float(s)

        # We only care about the LAST silence region — trailing dead air
        last_silence_start = float(silence_starts[-1])

        # Only trim if silence is near the end (within last 10% of video)
        if last_silence_start < total_duration * 0.9:
            log.info("No trailing silence detected near end, skipping trim")
            return True

        # Add a small buffer (0.5s) after last audio to avoid cutting off abruptly
        trim_end = last_silence_start + 0.5

        # Pass 2: Trim both audio AND video together using -to
        trimmed_path = video_path.with_suffix('.trimmed.mp4')
        trim_cmd = [
            'ffmpeg', '-y',
            '-i', str(video_path),
            '-to', str(trim_end),
            '-c', 'copy',  # Copy BOTH streams — no re-encoding, no desync
            str(trimmed_path)
        ]

        log.info(f"Trimming video to {trim_end:.1f}s (was {total_duration:.1f}s)")
        result = subprocess.run(trim_cmd, capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            log.error(f"ffmpeg trim failed: {result.stderr}")
            return False

        # Get file sizes for logging
        original_size = video_path.stat().st_size / (1024 * 1024)
        trimmed_size = trimmed_path.stat().st_size / (1024 * 1024)

        # Replace original with trimmed version
        video_path.unlink()
        trimmed_path.rename(video_path)

        trimmed_seconds = total_duration - trim_end
        log.info(f"Video trimmed: {original_size:.1f}MB -> {trimmed_size:.1f}MB (removed {trimmed_seconds:.1f}s trailing silence)")
        return True

    except subprocess.TimeoutExpired:
        log.error("ffmpeg trim timed out after 5 minutes")
        trimmed_path = video_path.with_suffix('.trimmed.mp4')
        if trimmed_path.exists():
            trimmed_path.unlink()
        return False
    except Exception as e:
        log.error(f"Video trimming failed: {e}")
        trimmed_path = video_path.with_suffix('.trimmed.mp4')
        if trimmed_path.exists():
            trimmed_path.unlink()
        return False


def _upload_video_to_youtube(video_path: str, date: str):
    """Helper to upload video to YouTube with error handling."""
    client_secrets, _ = get_youtube_credentials()
    if client_secrets:
        try:
            video_id = upload_to_youtube(video_path, date)
            if video_id:
                log.info(f"Uploaded to YouTube: https://youtube.com/watch?v={video_id}")
                update_digest_status(date, youtube_id=video_id, upload_status="success")
                # Add digest entry to RSS feed
                digest_status = load_digest_status()
                story_count = digest_status.get("story_count", 0)
                add_digest_to_feed(date, story_count, video_id)
            else:
                log.error(f"YouTube upload failed for {date}, video saved locally: {video_path}")
                send_alert(f"YouTube upload failed for {date}. Video saved at: {video_path}")
                update_digest_status(date, upload_status="failed", error_message="Upload returned no video ID")
        except Exception as e:
            log.error(f"YouTube upload failed: {e}")
            send_alert(f"YouTube upload failed for {date}: {e}. Video saved at: {video_path}")
            update_digest_status(date, upload_status="failed", error_message=str(e))
    else:
        log.info(f"YouTube not configured. Video saved locally: {video_path}")
        update_digest_status(date, upload_status="skipped")


# =============================================================================
# DAILY DIGEST STATUS
# =============================================================================

def load_digest_status() -> dict:
    """Load digest status from persistent file."""
    status = {}
    if DIGEST_STATUS_FILE.exists():
        try:
            with open(DIGEST_STATUS_FILE) as f:
                status = json.load(f)
        except Exception:
            pass

    # Always calculate next_digest_at dynamically (midnight CST = 06:00 UTC)
    now = datetime.now(timezone.utc)
    today_6am_utc = datetime(now.year, now.month, now.day, 6, tzinfo=timezone.utc)
    if now >= today_6am_utc:
        next_digest = today_6am_utc + timedelta(days=1)
    else:
        next_digest = today_6am_utc
    status["next_digest_at"] = next_digest.isoformat()

    return status


def save_digest_status(status: dict):
    """Save digest status to persistent file."""
    with open(DIGEST_STATUS_FILE, 'w') as f:
        json.dump(status, f, indent=2)


def update_digest_status(date: str, **kwargs):
    """Update digest status for dashboard monitoring.

    Fields: status, story_count, duration_seconds, video_path,
    youtube_id, upload_status, error_message
    """
    current = load_digest_status()

    # Calculate next digest (midnight CST = 06:00 UTC)
    now = datetime.now(timezone.utc)
    # Midnight CST is 06:00 UTC. Find the next 06:00 UTC.
    today_6am_utc = datetime(now.year, now.month, now.day, 6, tzinfo=timezone.utc)
    if now >= today_6am_utc:
        # Already past today's midnight CST, next one is tomorrow
        next_digest = today_6am_utc + timedelta(days=1)
    else:
        next_digest = today_6am_utc

    current["last_date"] = date
    current["next_digest_at"] = next_digest.isoformat()

    for key, value in kwargs.items():
        if value is not None:
            current[key] = value

    if kwargs.get("youtube_id"):
        current["youtube_url"] = f"https://youtube.com/watch?v={kwargs['youtube_id']}"

    if kwargs.get("status") in ("success", "failed", "no_stories"):
        current["last_completed_at"] = now.isoformat()

    save_digest_status(current)


# =============================================================================
# MONITOR DATA
# =============================================================================

def get_next_aligned_time() -> datetime:
    """Calculate next :00 or :30 aligned time for consistent scheduling."""
    now = datetime.now()
    if now.minute < 30:
        # Next slot is :30 of current hour
        next_time = now.replace(minute=30, second=0, microsecond=0)
    else:
        # Next slot is :00 of next hour
        next_time = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    return next_time


def get_source_health() -> dict:
    """Get source health status from recent scrape attempts.

    Only marks a source as failed if its most recent log entry is a failure.
    If a source has succeeded after failing, it's considered healthy.
    """
    sources = CONFIG.get("sources", [])
    total = len(sources)

    # Track last status per source: True = success, False = failure
    source_status = {}

    try:
        log_file = BASE_DIR / "jtf.log"
        if log_file.exists():
            with open(log_file) as f:
                # Check last 200 lines for recent activity
                lines = f.readlines()[-200:]
                for line in lines:
                    for source in sources:
                        name = source["name"]
                        if name in line:
                            if "Failed to fetch from" in line or "Skipping" in line:
                                source_status[name] = False
                            elif "Fetched" in line and "headlines from" in line:
                                source_status[name] = True
    except:
        pass

    # Only sources whose LAST entry was a failure are considered failed
    failed_sources = [name for name, status in source_status.items() if status is False]

    return {
        "total": total,
        "successful": total - len(failed_sources),
        "failed": failed_sources
    }


def get_queue_stats() -> dict:
    """Get queue statistics."""
    queue = load_queue()
    if not queue:
        return {"size": 0, "oldest_item_age_hours": 0}

    oldest_ts = None
    for item in queue:
        item_ts = datetime.fromisoformat(item["timestamp"])
        if oldest_ts is None or item_ts < oldest_ts:
            oldest_ts = item_ts

    age_hours = 0
    if oldest_ts:
        now = datetime.now(timezone.utc)
        age_hours = (now - oldest_ts).total_seconds() / 3600

    return {
        "size": len(queue),
        "oldest_item_age_hours": round(age_hours, 1)
    }


def get_stories_today_count() -> int:
    """Count stories published today."""
    stories_file = DATA_DIR / "stories.json"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if stories_file.exists():
        try:
            with open(stories_file) as f:
                data = json.load(f)
            if data.get("date") == today:
                return len(data.get("stories", []))
        except:
            pass
    return 0


def get_stream_health_status() -> str:
    """Get stream health status."""
    if not HEARTBEAT_FILE.exists():
        return "unknown"

    try:
        with open(HEARTBEAT_FILE) as f:
            last_beat = float(f.read().strip())

        now = time.time()
        if now - last_beat > STREAM_OFFLINE_THRESHOLD:
            return "offline"
        return "online"
    except:
        return "unknown"


def write_monitor_data(cycle_stats: dict):
    """Write monitoring data to JSON file for dashboard.

    Args:
        cycle_stats: Dict with cycle-specific stats:
            - headlines_scraped: Total headlines fetched
            - headlines_processed: Headlines sent to Claude
            - stories_published: Stories verified and published
            - stories_queued: Stories added to queue
            - duration_seconds: How long the cycle took
    """
    monitor_file = DATA_DIR / "monitor.json"

    # Calculate uptime
    now = datetime.now(timezone.utc)
    uptime_seconds = (now - STARTUP_TIME).total_seconds()

    # Get API costs
    api_costs = get_api_costs_today()
    total_cost = api_costs.get("total_cost_usd", 0)

    # Check budget alert
    check_budget_alert(total_cost)

    # Check queue backup alert
    queue_stats = get_queue_stats()
    if queue_stats.get("size", 0) > 200 or queue_stats.get("oldest_item_age_hours", 0) > 20:
        if should_send_alert("queue_backup"):
            send_alert(
                f"Queue backup: {queue_stats['size']} items, oldest {queue_stats['oldest_item_age_hours']:.1f}h",
                "queue_backup"
            )

    # Update uptime tracking and get availability
    uptime_stats = update_uptime_tracking()

    # Get monthly estimate from rolling history (persists across restarts)
    month_estimate = get_month_estimate()

    # Get dynamic daily budget based on days in month
    daily_budget = get_daily_budget()

    # Calculate minutes until next clock-aligned cycle (:00 or :30)
    next_run = get_next_aligned_time()
    next_cycle_minutes = int((next_run - datetime.now()).total_seconds() // 60)

    data = {
        "timestamp": now.isoformat(),
        "web_refresh_at": now.isoformat(),  # Signal for web pages to refresh after cycle
        "uptime_start": STARTUP_TIME.isoformat(),
        "uptime_seconds": round(uptime_seconds),
        "availability_pct": uptime_stats.get("availability_pct", 0),
        "cycle": {
            "number": _cycle_stats.get("cycle_number", 0),
            "duration_seconds": cycle_stats.get("duration_seconds", 0),
            "headlines_scraped": cycle_stats.get("headlines_scraped", 0),
            "headlines_processed": cycle_stats.get("headlines_processed", 0),
            "stories_published": cycle_stats.get("stories_published", 0),
            "stories_queued": cycle_stats.get("stories_queued", 0)
        },
        "api_costs": {
            "today": api_costs.get("services", {}),
            "total_usd": round(api_costs.get("total_cost_usd", 0), 4),
            "month_estimate_usd": round(month_estimate, 2),
            "daily_budget": round(daily_budget, 2),
            "budget_pct": round((total_cost / daily_budget) * 100, 1) if daily_budget > 0 else 0
        },
        "queue": queue_stats,
        "stories_today": get_stories_today_count(),
        "sources": get_source_health(),
        "recent_errors": error_handler.get_recent(10),
        "status": {
            "state": "running",
            "stream_health": get_stream_health_status(),
            "next_cycle_minutes": next_cycle_minutes,
            "degraded_services": list(_degraded_services)
        },
        "daily_digest": load_digest_status()
    }

    try:
        with open(monitor_file, 'w') as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        log.warning(f"Could not write monitor data: {e}")
        return

    # Push to GitHub for public dashboard
    push_monitor_to_ghpages(monitor_file)


def write_sleeping_heartbeat(minutes_remaining: int, last_cycle_stats: dict = None):
    """Write heartbeat during sleep to keep dashboard from showing stale.

    Updates monitor.json with "sleeping" status and time until next cycle.
    """
    monitor_file = DATA_DIR / "monitor.json"

    now = datetime.now(timezone.utc)
    uptime_seconds = (now - STARTUP_TIME).total_seconds()

    # Get current costs and stats (reuse from last cycle if available)
    api_costs = get_api_costs_today()
    total_cost = api_costs.get("total_cost_usd", 0)
    queue_stats = get_queue_stats()

    # Update uptime tracking and get availability
    uptime_stats = update_uptime_tracking()

    # Get monthly estimate from rolling history (persists across restarts)
    month_estimate = get_month_estimate()

    # Get dynamic daily budget based on days in month
    daily_budget = get_daily_budget()

    # Use last cycle stats or defaults
    cycle_stats = last_cycle_stats or {}

    data = {
        "timestamp": now.isoformat(),
        "uptime_start": STARTUP_TIME.isoformat(),
        "uptime_seconds": round(uptime_seconds),
        "availability_pct": uptime_stats.get("availability_pct", 0),
        "cycle": {
            "number": _cycle_stats.get("cycle_number", 0),
            "duration_seconds": cycle_stats.get("duration_seconds", 0),
            "headlines_scraped": cycle_stats.get("headlines_scraped", 0),
            "headlines_processed": cycle_stats.get("headlines_processed", 0),
            "stories_published": cycle_stats.get("stories_published", 0),
            "stories_queued": cycle_stats.get("stories_queued", 0)
        },
        "api_costs": {
            "today": api_costs.get("services", {}),
            "total_usd": round(api_costs.get("total_cost_usd", 0), 4),
            "month_estimate_usd": round(month_estimate, 2),
            "daily_budget": round(daily_budget, 2),
            "budget_pct": round((total_cost / daily_budget) * 100, 1) if daily_budget > 0 else 0
        },
        "queue": queue_stats,
        "stories_today": get_stories_today_count(),
        "sources": get_source_health(),
        "recent_errors": error_handler.get_recent(10),
        "status": {
            "state": "running",
            "stream_health": get_stream_health_status(),
            "next_cycle_minutes": minutes_remaining,
            "degraded_services": list(_degraded_services)
        },
        "daily_digest": load_digest_status()
    }

    try:
        with open(monitor_file, 'w') as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        log.warning(f"Could not write sleeping heartbeat: {e}")
        return

    # Push to GitHub
    push_monitor_to_ghpages(monitor_file)


def push_to_ghpages(files: list, commit_message: str):
    """Push files to GitHub branch via GitHub API.

    Args:
        files: List of tuples (local_path, docs_path) where:
               - local_path: Path to the local file (Path or str)
               - docs_path: Path in docs folder (e.g., "feed.xml", "archive/2026/02-15.txt.gz")
        commit_message: Commit message for the push

    Returns:
        True if successful, False otherwise
    """
    import base64

    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        log.warning("GITHUB_TOKEN not set, cannot push to GitHub")
        return False

    # Also copy to local docs if it exists (for dev machine)
    docs_dir = BASE_DIR / "docs"
    if docs_dir.exists():
        for local_path, gh_path in files:
            dest = docs_dir / gh_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            # Skip copy if source and destination are the same file
            if Path(local_path).resolve() != dest.resolve():
                shutil.copy(local_path, dest)

    owner = "JTFNews"
    repo = "jtfnews"
    branch = "main"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    success = True
    for local_path, gh_path in files:
        try:
            # Prefix path with docs/ for main branch deployment
            gh_path = f"docs/{gh_path}"

            # Read file content (binary mode for gz files)
            local_path = Path(local_path)
            if local_path.suffix == '.gz':
                with open(local_path, "rb") as f:
                    content = base64.b64encode(f.read()).decode()
            else:
                with open(local_path, "r") as f:
                    content = base64.b64encode(f.read().encode()).decode()

            api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{gh_path}"

            # Get current file SHA (required for update)
            response = requests.get(api_url, headers=headers, params={"ref": branch})
            sha = response.json().get("sha") if response.status_code == 200 else None

            # Push the update
            payload = {
                "message": commit_message,
                "content": content,
                "branch": branch
            }
            if sha:
                payload["sha"] = sha

            response = requests.put(api_url, headers=headers, json=payload)

            if response.status_code not in (200, 201):
                log.warning(f"GitHub API error for {gh_path}: {response.status_code}")
                success = False

        except Exception as e:
            log.warning(f"Error pushing {gh_path} to GitHub: {e}")
            success = False

    if success:
        log.info(f"Pushed to GitHub: {commit_message}")
    return success


def push_monitor_to_ghpages(monitor_file: Path):
    """Push monitor.json to GitHub branch via GitHub API."""
    push_to_ghpages([(monitor_file, "monitor.json")], "Update monitor data")


# =============================================================================
# ARCHIVE
# =============================================================================

def mark_corrected_stories_in_log(log_file: Path, date_str: str):
    """Mark any corrected stories in the daily log before archiving."""
    # Load corrections for this date
    corrections = load_corrections()
    corrected_ids = set()

    for c in corrections.get("corrections", []):
        story_id = c.get("story_id", "")
        # Story IDs are like "2026-02-15-001" - check if date matches
        if story_id.startswith(date_str):
            corrected_ids.add(story_id)

    if not corrected_ids:
        return  # No corrections for this day

    # Read and update log lines
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()

        updated_lines = []
        story_index = 0

        for line in lines:
            # Skip headers
            if line.startswith("#") or not line.strip():
                updated_lines.append(line)
                continue

            # Check if this story was corrected
            story_id = generate_story_id(date_str, story_index)
            if story_id in corrected_ids:
                # Prepend [CORRECTED] to the fact (4th field after |)
                parts = line.strip().split("|")
                if len(parts) >= 4:
                    parts[3] = f"[CORRECTED] {parts[3]}"
                    line = "|".join(parts) + "\n"
                    log.info(f"Marked {story_id} as corrected in archive")

            updated_lines.append(line)
            story_index += 1

        # Write back
        with open(log_file, 'w') as f:
            f.writelines(updated_lines)

    except Exception as e:
        log.error(f"Failed to mark corrected stories: {e}")


def archive_daily_log():
    """Archive yesterday's log to GitHub."""
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

    # Mark any corrected stories before archiving
    mark_corrected_stories_in_log(log_file, yesterday_str)

    # Archive to docs
    docs_dir = BASE_DIR / "docs"
    if not docs_dir.exists():
        log.warning("docs not found, skipping archive")
        return

    # Create year folder in docs archive
    archive_dir = docs_dir / "archive" / year
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

    # Clean up fact extraction cache
    fact_cache_file = DATA_DIR / f"fact_cache_{yesterday_str}.json"
    fact_cache_file.unlink(missing_ok=True)

    # Push to GitHub via API
    push_to_ghpages(
        [(archive_file, f"archive/{year}/{yesterday_str}.txt.gz")],
        f"Archive {yesterday_str}"
    )

    # Update archive index after archiving
    update_archive_index()


def update_archive_index():
    """Update archive/index.json with list of available archive dates."""
    archive_dir = BASE_DIR / "docs" / "archive"
    if not archive_dir.exists():
        log.debug("Archive directory does not exist yet")
        return

    dates = []
    for year_dir in sorted(archive_dir.iterdir(), reverse=True):
        if year_dir.is_dir() and year_dir.name.isdigit():
            for archive_file in sorted(year_dir.glob("*.txt.gz"), reverse=True):
                date_str = archive_file.stem.replace(".txt", "")
                dates.append(date_str)

    index_data = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "dates": dates
    }

    index_file = archive_dir / "index.json"
    with open(index_file, 'w') as f:
        json.dump(index_data, f, indent=2)

    log.info(f"Updated archive index: {len(dates)} dates")


# =============================================================================
# MAIN LOOP
# =============================================================================

def process_cycle():
    """Run one processing cycle."""
    cycle_start = time.time()

    # Update cycle number
    global _cycle_stats
    _cycle_stats["cycle_number"] = _cycle_stats.get("cycle_number", 0) + 1

    log.info("=" * 60)
    log.info(f"Starting cycle #{_cycle_stats['cycle_number']}")

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

    # Load caches (saves API costs by avoiding redundant calls)
    processed_cache = load_processed_headlines()
    global _fact_extraction_cache
    _fact_extraction_cache = load_fact_extraction_cache()
    skipped_count = 0
    published_count = 0
    processed_count = 0  # Headlines sent to Claude
    queued_count = 0  # Stories added to queue this cycle

    for headline in headlines:
        # Skip if already processed (saves API costs)
        if is_headline_processed(headline["text"], processed_cache):
            skipped_count += 1
            continue

        # Mark as processed before calling API
        add_processed_headline(get_story_hash(headline["text"]))

        # Extract fact
        result = extract_fact(headline["text"])
        processed_count += 1  # Count headlines sent to Claude

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

                    # Compare reliability scores to pick the best fact version
                    # Formula: source_rating × (confidence / 100)
                    new_reliability = get_reliability_score(headline["source_id"], confidence)
                    queue_confidence = match.get("confidence", 85)  # Default 85% if missing
                    queue_reliability = get_reliability_score(match["source_id"], queue_confidence)

                    # Use fact from higher-reliability source
                    if queue_reliability > new_reliability:
                        best_fact = match["fact"]
                        log.info(
                            f"Preferring queued source ({match['source_name']}: {queue_reliability:.1f}) "
                            f"over new ({headline['source_name']}: {new_reliability:.1f})"
                        )
                    else:
                        best_fact = fact
                        if queue_reliability < new_reliability:
                            log.info(
                                f"Preferring new source ({headline['source_name']}: {new_reliability:.1f}) "
                                f"over queued ({match['source_name']}: {queue_reliability:.1f})"
                            )
                        # If equal, newer (new) wins silently

                    sources = [headline, match]

                    # Check for contradictions with recent facts
                    recent_facts = get_recent_facts()
                    if check_contradiction(best_fact, recent_facts):
                        log.warning(f"Contradiction blocked: {best_fact[:40]}...")
                        send_alert(f"Contradiction: {best_fact[:50]}")
                        continue

                    # Generate unique audio ID from story content (hash-based)
                    # This ensures audio files are always linked to correct story
                    story_audio_id = get_story_audio_id(best_fact)

                    # Generate TTS first (before JS sees the new story)
                    audio_file = generate_tts(best_fact, story_id=story_audio_id)

                    # Now write output (JS will detect and play)
                    write_current_story(best_fact, sources)
                    append_daily_log(best_fact, sources, audio_file)
                    add_shown_hash(get_story_hash(best_fact))

                    # Remove from queue
                    queue = [q for q in queue if q["fact"] != match["fact"]]

                    published_count += 1
                    log.info(f"VERIFIED: {best_fact[:50]}...")

                    # Record verification success for BOTH sources (ratings learning)
                    fact_hash = get_story_hash(best_fact)
                    record_verification_success(headline["source_id"], fact_hash)
                    record_verification_success(match["source_id"], fact_hash)

                    # CORRECTIONS SYSTEM: Check if this verified fact contradicts any
                    # previously published story - if so, issue a correction
                    recent_stories = get_recent_stories_for_correction(days=7)
                    correction_info = detect_correction_needed(best_fact, sources, recent_stories)
                    if correction_info:
                        log.warning(f"Correction needed: {correction_info.get('reason', '')[:50]}")
                        correction_type = correction_info.get("correction_type", "correction")
                        story_id = correction_info.get("story_id", "")
                        original = correction_info.get("original_fact", "")
                        reason = correction_info.get("reason", "")

                        if correction_type == "retraction":
                            issue_retraction(story_id, original, reason, sources)
                        else:
                            issue_correction(
                                story_id=story_id,
                                original_fact=original,
                                corrected_fact=best_fact,
                                reason=reason,
                                correcting_sources=sources,
                                correction_type=correction_type
                            )

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
                "source_url": headline.get("source_url", ""),
                "timestamp": headline["timestamp"],
                "confidence": confidence
            })
            queued_count += 1
            log.info(f"Queued: {fact[:40]}...")

    # Save queue
    save_queue(queue)

    # Calculate cycle duration and write monitor data
    cycle_duration = time.time() - cycle_start
    write_monitor_data({
        "headlines_scraped": len(headlines),
        "headlines_processed": processed_count,
        "stories_published": published_count,
        "stories_queued": queued_count,
        "duration_seconds": round(cycle_duration, 1)
    })

    log.info(f"Cycle complete. Published: {published_count}, Queue: {len(queue)}, Skipped (cached): {skipped_count}")


# =============================================================================
# QUARTERLY OWNERSHIP AUDIT
# =============================================================================

def get_current_quarter() -> str:
    """Return current quarter string like 'Q1 2026'."""
    month = datetime.now().month
    quarter = (month - 1) // 3 + 1
    year = datetime.now().year
    return f"Q{quarter} {year}"


def check_ownership_audit_needed() -> bool:
    """Check if ownership audit is needed for current quarter."""
    current_quarter = get_current_quarter()
    audit_file = DATA_DIR / "ownership_audit.json"

    if audit_file.exists():
        try:
            with open(audit_file) as f:
                audit_data = json.load(f)
                if audit_data.get("last_quarter") == current_quarter:
                    return False  # Audit is current
        except (json.JSONDecodeError, IOError):
            pass

    return True  # Audit needed


OWNERSHIP_RESEARCH_PROMPT = """You are researching current ownership data for a news source.

Source: {source_name}
Current data in our system:
- Owner: {current_owner}
- Control type: {control_type}
- Institutional holders: {current_holders}

Research and verify the CURRENT ownership structure. Return ONLY a valid JSON object with:
{{
  "owner": "Primary owner/parent company name",
  "owner_display": "Brief display format (e.g., 'Thomson Reuters (69%)')",
  "control_type": "One of: corporate, public_broadcaster, nonprofit, trust, state, cooperative, government, private",
  "institutional_holders": [
    {{"name": "Top shareholder name", "percent": 0.0}},
    {{"name": "Second shareholder", "percent": 0.0}},
    {{"name": "Third shareholder", "percent": 0.0}}
  ],
  "changed": true or false (whether data differs from current),
  "notes": "Brief explanation of any changes or 'No changes'"
}}

IMPORTANT:
- For public broadcasters (BBC, NPR, etc.), institutional_holders should be empty
- For cooperatives (AP), institutional_holders should be empty
- For publicly traded companies, list top 3 institutional shareholders with percentages
- Use accurate, current data - do not guess
- If unsure, set changed to false and note uncertainty

Return ONLY valid JSON, no explanation or markdown."""


def research_source_ownership(source: dict) -> dict:
    """Use Claude to research current ownership for a source."""
    try:
        client = anthropic.Anthropic()

        prompt = OWNERSHIP_RESEARCH_PROMPT.format(
            source_name=source.get("name", source.get("id")),
            current_owner=source.get("owner", "unknown"),
            control_type=source.get("control_type", "unknown"),
            current_holders=json.dumps(source.get("institutional_holders", []))
        )

        response = client.messages.create(
            model="claude-sonnet-4-20250514",  # Use Sonnet for better research
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )

        # Log API usage
        log_api_usage("claude", {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens
        })

        text = response.content[0].text

        # Parse JSON response
        start = text.find('{')
        end = text.rfind('}') + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])

        return {"changed": False, "notes": "Failed to parse response"}

    except Exception as e:
        log.warning(f"Ownership research failed for {source.get('id')}: {e}")
        return {"changed": False, "notes": f"Research failed: {e}"}


def perform_ownership_audit() -> bool:
    """Perform quarterly ownership audit using Claude.

    Returns True if audit completed successfully, False if blocked.
    """
    current_quarter = get_current_quarter()

    log.info("=" * 60)
    log.info(f"QUARTERLY OWNERSHIP AUDIT - {current_quarter}")
    log.info("=" * 60)
    log.info("Researching ownership data for all sources...")
    log.info("This may take a few minutes and will use Claude API credits.")
    log.info("")

    changes = []
    verified = []

    # Skip government sources - ownership doesn't change
    skip_types = ["government"]

    for source in CONFIG["sources"]:
        source_id = source.get("id", "unknown")
        control_type = source.get("control_type", "")

        if control_type in skip_types:
            log.info(f"  [SKIP] {source_id} (government source)")
            verified.append(source_id)
            continue

        log.info(f"  [RESEARCH] {source_id}...")
        result = research_source_ownership(source)

        if result.get("changed", False):
            changes.append({
                "source_id": source_id,
                "source_name": source.get("name", source_id),
                "current": {
                    "owner": source.get("owner"),
                    "owner_display": source.get("owner_display"),
                    "institutional_holders": source.get("institutional_holders", [])
                },
                "researched": {
                    "owner": result.get("owner"),
                    "owner_display": result.get("owner_display"),
                    "institutional_holders": result.get("institutional_holders", [])
                },
                "notes": result.get("notes", "")
            })
            log.info(f"    → CHANGE DETECTED: {result.get('notes', 'See details')}")
        else:
            verified.append(source_id)
            log.info(f"    → Verified (no changes)")

        # Small delay to avoid rate limiting
        time.sleep(0.5)

    log.info("")
    log.info("=" * 60)
    log.info("AUDIT RESULTS")
    log.info("=" * 60)
    log.info(f"Sources verified unchanged: {len(verified)}")
    log.info(f"Sources with changes: {len(changes)}")

    if changes:
        log.info("")
        log.info("CHANGES DETECTED:")
        for change in changes:
            log.info(f"  {change['source_name']}:")
            log.info(f"    Current:    {change['current']['owner_display']}")
            log.info(f"    Researched: {change['researched']['owner_display']}")
            log.info(f"    Notes: {change['notes']}")

        log.info("")
        log.info("=" * 60)
        log.info("APPLYING OWNERSHIP UPDATES AUTOMATICALLY")
        log.info("=" * 60)

        # Send SMS notification (informational only)
        try:
            send_alert(f"JTF Ownership Audit: {len(changes)} changes applied automatically.")
        except Exception as e:
            log.warning(f"Could not send SMS alert: {e}")

        # Apply changes to config.json automatically (no confirmation needed)
        log.info("Applying changes...")
        apply_ownership_changes(changes)

    # Log the completed audit
    audit_file = DATA_DIR / "ownership_audit.json"
    audit_data = {
        "last_quarter": current_quarter,
        "audit_date": datetime.now().isoformat(),
        "changes_applied": len(changes),
        "sources_verified": len(verified),
        "change_details": changes
    }

    with open(audit_file, 'w') as f:
        json.dump(audit_data, f, indent=2)

    log.info(f"Audit logged to {audit_file}")
    log.info("=" * 60)
    log.info(f"OWNERSHIP AUDIT COMPLETE - {current_quarter}")
    log.info("=" * 60)

    return True


def apply_ownership_changes(changes: list):
    """Apply ownership changes to config.json."""
    config_file = BASE_DIR / "config.json"

    # Load current config
    with open(config_file) as f:
        config = json.load(f)

    # Apply changes
    for change in changes:
        source_id = change["source_id"]
        for source in config["sources"]:
            if source.get("id") == source_id:
                source["owner"] = change["researched"]["owner"]
                source["owner_display"] = change["researched"]["owner_display"]
                source["institutional_holders"] = change["researched"]["institutional_holders"]
                log.info(f"  Updated: {source_id}")
                break

    # Save config
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)

    log.info(f"Config saved to {config_file}")


def check_midnight_archive():
    """Check if it's time to archive and cleanup (midnight CST = 06:00 UTC)."""
    global _midnight_archive_done_for
    now = datetime.now(timezone.utc)
    today = now.date().isoformat()

    if now.hour == 6 and now.minute < 5:
        # Idempotency guard: only run once per day
        if _midnight_archive_done_for == today:
            return  # Already done today
        _midnight_archive_done_for = today

        # Get yesterday's date for archiving
        yesterday = (now.date() - timedelta(days=1)).strftime("%Y-%m-%d")

        # 1. Archive audio files FIRST (preserves for video generation)
        archived_audio = archive_audio_files(yesterday)

        # 2. Generate and upload daily summary video BEFORE archiving log
        # (needs data/YYYY-MM-DD.txt which archive_daily_log deletes)
        if archived_audio:
            try:
                generate_and_upload_daily_summary(yesterday)
            except Exception as e:
                log.error(f"Daily video generation failed: {e}")
                send_alert(f"Daily video generation failed for {yesterday}: {e}")

        # 3. Archive daily log AFTER digest is done (deletes the .txt file)
        archive_daily_log()

        # 4. Cleanup old data
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

    # Initialize uptime tracking (handles month rollover and downtime accounting)
    init_uptime_tracking()

    # Archive yesterday's cost to rolling history
    archive_yesterday_cost()

    # Check quarterly ownership audit
    if check_ownership_audit_needed():
        current_quarter = get_current_quarter()
        log.warning("=" * 60)
        log.warning(f"OWNERSHIP AUDIT REQUIRED - {current_quarter}")
        log.warning("=" * 60)
        log.warning("Quarterly ownership verification has not been completed.")
        log.warning("This is required by the JTF whitepaper for transparency.")
        log.warning("")

        # Send SMS alert
        try:
            send_alert(f"JTF: Ownership audit required for {current_quarter}. Starting audit...")
        except Exception as e:
            log.warning(f"Could not send SMS alert: {e}")

        # Perform the audit
        if not perform_ownership_audit():
            log.critical("Ownership audit incomplete - cannot start")
            log.critical("Run: python main.py --audit")
            sys.exit(1)

        log.info("Ownership audit complete. Continuing startup...")
        log.info("-" * 40)

    # Validate all services before starting
    if not validate_services():
        log.critical("Service validation failed - cannot start")
        sys.exit(1)

    if _degraded_services:
        log.info(f"Starting in degraded mode: {_degraded_services}")

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

            # Sleep until next :00 or :30 (clock-aligned for consistency)
            # Heartbeat every 5 minutes keeps dashboard from showing "stale"
            next_run = get_next_aligned_time()
            sleep_seconds = (next_run - datetime.now()).total_seconds()
            sleep_minutes = int(sleep_seconds // 60)
            log.info(f"Sleeping until {next_run.strftime('%H:%M')} ({sleep_minutes} minutes)...")
            heartbeat_interval = 5 * 60  # 5 minutes in seconds
            remaining = sleep_seconds
            while remaining > 0:
                sleep_time = min(heartbeat_interval, remaining)
                time.sleep(sleep_time)
                remaining -= sleep_time
                if remaining > 0:
                    # Update heartbeat and monitor during sleep
                    write_heartbeat()
                    write_sleeping_heartbeat(int(remaining // 60))

        except KeyboardInterrupt:
            log.info("Shutting down...")
            break
        except Exception as e:
            # Log errors but don't send SMS alerts for code bugs
            # Alerts are reserved for: stream offline, contradictions, major issues
            log.error(f"Cycle error: {e}")
            time.sleep(60)  # Wait 1 minute on error


# =============================================================================
# REBUILD STORIES FROM DAILY LOG
# =============================================================================

def rebuild_stories_from_log():
    """Rebuild stories.json from today's daily log, matching to existing audio files.

    Use this to recover after accidental --fresh clear.
    Supports all log formats and audio naming schemes:
    - 4-field: timestamp|names|scores|fact (legacy, no audio)
    - 5-field: timestamp|names|scores|urls|fact (legacy, no audio)
    - 6-field: timestamp|names|scores|urls|audio|fact (current)

    Audio lookup priority:
    1. Stored filename from log (e.g., "a3f2b1c9d4e5.mp3")
    2. Hash-based lookup in archive folder
    3. Legacy index-based fallback
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = DATA_DIR / f"{today}.txt"
    stories_file = DATA_DIR / "stories.json"

    if not log_file.exists():
        log.error(f"No daily log found: {log_file}")
        return False

    # Collect all available audio files
    # 1. Legacy audio_*.mp3 in audio/ folder
    legacy_audio = set()
    for f in AUDIO_DIR.glob("audio_*.mp3"):
        legacy_audio.add(f.name)

    # 2. Hash-based files in archive folder
    archive_dir = AUDIO_DIR / "archive" / today
    archived_audio = set()
    if archive_dir.exists():
        for f in archive_dir.glob("*.mp3"):
            archived_audio.add(f.name)

    log.info(f"Found {len(legacy_audio)} legacy + {len(archived_audio)} archived audio files")

    # Parse daily log
    stories = []
    with open(log_file) as f:
        for line in f:
            # Skip headers and blank lines
            if line.startswith("#") or not line.strip():
                continue

            parts = line.strip().split("|")
            if len(parts) < 4:
                continue

            # Parse all log formats
            # 4-field: timestamp|names|scores|fact
            # 5-field: timestamp|names|scores|urls|fact
            # 6-field: timestamp|names|scores|urls|audio|fact
            timestamp = parts[0]
            source_names = parts[1]
            source_scores = parts[2]
            stored_audio = ""
            fact = ""

            if len(parts) == 4:
                fact = parts[3]
                source_urls_str = ""
            elif len(parts) == 5:
                source_urls_str = parts[3]
                fact = parts[4]
            else:  # 6+ fields (fact may contain pipes)
                source_urls_str = parts[3]
                stored_audio = parts[4]
                fact = "|".join(parts[5:])

            # Split sources and look up IDs for current format
            names = source_names.split(",")
            urls = source_urls_str.split(",") if source_urls_str else []

            # Format source attribution using current get_compact_scores()
            source_parts = []
            source_urls_map = {}
            for i, name in enumerate(names):
                name = name.strip()
                source_id = None
                source_url = urls[i].strip() if i < len(urls) else ""
                for src in CONFIG["sources"]:
                    if src["name"] == name:
                        source_id = src["id"]
                        if not source_url:
                            source_url = src.get("url", "")
                        break
                if source_id:
                    source_parts.append(f"{name} {get_compact_scores(source_id)}")
                else:
                    source_parts.append(name)
                if source_url:
                    source_urls_map[name] = source_url
            source_text = " · ".join(source_parts)

            # Find audio file - priority: stored, hash-based, legacy index
            audio_filename = None
            audio_path = None
            story_index = len(stories)

            # 1. Try stored filename from log
            if stored_audio and stored_audio in archived_audio:
                audio_filename = stored_audio
                audio_path = f"../audio/archive/{today}/{audio_filename}"
                log.debug(f"Story {story_index}: Using stored audio: {audio_filename}")
            elif stored_audio and stored_audio in legacy_audio:
                audio_filename = stored_audio
                audio_path = f"../audio/{audio_filename}"
                log.debug(f"Story {story_index}: Using stored legacy audio: {audio_filename}")

            # 2. Try hash-based lookup
            if not audio_filename:
                fact_hash = get_story_hash(fact)
                hash_filename = f"{fact_hash}.mp3"
                if hash_filename in archived_audio:
                    audio_filename = hash_filename
                    audio_path = f"../audio/archive/{today}/{audio_filename}"
                    log.debug(f"Story {story_index}: Using hash-based audio: {audio_filename}")

            # 3. Legacy index-based fallback
            if not audio_filename:
                legacy_filename = f"audio_{story_index}.mp3"
                if legacy_filename in legacy_audio:
                    audio_filename = legacy_filename
                    audio_path = f"../audio/{audio_filename}"
                    log.debug(f"Story {story_index}: Using legacy index audio: {audio_filename}")

            if audio_filename:
                story_id = generate_story_id(today, story_index)
                story_hash = hashlib.md5(fact.encode()).hexdigest()[:12]
                stories.append({
                    "id": story_id,
                    "hash": story_hash,
                    "fact": fact,
                    "source": source_text,
                    "source_urls": source_urls_map,
                    "audio": audio_path,
                    "published_at": f"{today}T{timestamp}:00Z",
                    "status": "published"
                })
            else:
                log.warning(f"Skipping story {story_index}: no audio file found for: {fact[:50]}...")

    # Write rebuilt stories.json
    data = {"date": today, "stories": stories}
    with open(stories_file, 'w') as f:
        json.dump(data, f, indent=2)

    log.info(f"Rebuilt stories.json: {len(stories)} stories (from {log_file.name})")
    return True


def regenerate_audio_for_date(date: str, force: bool = False) -> dict:
    """Regenerate TTS audio for all stories on a specific date.

    Loads stories from the archived log and generates hash-based audio files.
    Use this to fix corrupted audio archives from the index-based naming bug.

    Args:
        date: Date string in YYYY-MM-DD format
        force: If True, regenerate even if hash-based audio already exists

    Returns:
        Dict with 'generated', 'skipped', 'failed' counts
    """
    import gzip

    log.info(f"=== Regenerating audio for {date} ===")

    # Find the log file (local or archived)
    log_file = DATA_DIR / f"{date}.txt"
    lines = []

    if log_file.exists():
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        log.info(f"Loading from local file: {log_file}")
    else:
        # Try archived file
        year = date[:4]
        archive_file = BASE_DIR / "docs" / "archive" / year / f"{date}.txt.gz"
        if archive_file.exists():
            with gzip.open(archive_file, 'rt', encoding='utf-8') as f:
                lines = f.readlines()
            log.info(f"Loading from archive: {archive_file}")
        else:
            log.error(f"No log file found for {date}")
            return {'generated': 0, 'skipped': 0, 'failed': 0}

    # Create archive directory for this date
    archive_dir = AUDIO_DIR / "archive" / date
    archive_dir.mkdir(parents=True, exist_ok=True)

    results = {'generated': 0, 'skipped': 0, 'failed': 0}

    # Parse stories from log
    story_index = 0
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        parts = line.split('|')
        if len(parts) < 4:
            continue

        # Extract fact from the appropriate field based on format
        if len(parts) == 4:
            fact = parts[3]
        elif len(parts) == 5:
            fact = parts[4]
        else:  # 6+ fields
            fact = "|".join(parts[5:])

        if not fact:
            continue

        # Generate hash-based filename
        fact_hash = get_story_hash(fact)
        audio_filename = f"{fact_hash}.mp3"
        audio_path = archive_dir / audio_filename

        # Check if already exists
        if audio_path.exists() and not force:
            log.info(f"  Story {story_index}: Already exists - {audio_filename}")
            results['skipped'] += 1
            story_index += 1
            continue

        # Generate TTS directly to the correct date's archive folder
        # (Don't use generate_tts() as it writes to TODAY's folder)
        log.info(f"  Story {story_index}: Generating audio for: {fact[:50]}...")
        try:
            client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

            audio_generator = client.text_to_speech.convert(
                voice_id=os.getenv("ELEVENLABS_VOICE_ID"),
                text=fact,
                model_id="eleven_multilingual_v2",
                voice_settings={
                    "stability": 0.7,
                    "similarity_boost": 0.8,
                    "style": 0.3,
                    "use_speaker_boost": True
                }
            )

            audio_data = b''.join(chunk for chunk in audio_generator)

            # Write directly to the correct date's archive folder
            with open(audio_path, 'wb') as f:
                f.write(audio_data)

            log.info(f"    -> Created {audio_filename} in {date}/")
            results['generated'] += 1

            # Log API usage
            log_api_usage("elevenlabs", {"characters": len(fact)})

        except Exception as e:
            log.error(f"    -> Error: {e}")
            results['failed'] += 1

        story_index += 1

        # Small delay to avoid rate limiting
        time.sleep(0.5)

    log.info(f"=== Regeneration complete for {date} ===")
    log.info(f"    Generated: {results['generated']}")
    log.info(f"    Skipped: {results['skipped']}")
    log.info(f"    Failed: {results['failed']}")

    return results


def get_source_url_by_name(name: str) -> str:
    """Look up source URL by name from config."""
    name = name.strip()
    # Remove "(+N more)" suffix if present
    if " (+" in name:
        name = name.split(" (+")[0]
    for src in CONFIG["sources"]:
        if src["name"] == name:
            return src.get("url", "")
    return ""


def rebuild_archives_with_urls():
    """Rebuild all archives and daily logs to include source URLs.

    Converts old format (timestamp|names|scores|fact) to
    new format (timestamp|names|scores|urls|fact).
    """
    import gzip

    docs_dir = BASE_DIR / "docs"
    archive_dir = docs_dir / "archive"

    files_updated = 0

    # Process archived .txt.gz files
    for year_dir in archive_dir.glob("*"):
        if not year_dir.is_dir():
            continue
        for gz_file in year_dir.glob("*.txt.gz"):
            try:
                # Read and decompress
                with gzip.open(gz_file, 'rt', encoding='utf-8') as f:
                    content = f.read()

                # Process lines
                new_lines = []
                needs_update = False
                for line in content.split('\n'):
                    if line.startswith('#') or not line.strip():
                        new_lines.append(line)
                        continue

                    parts = line.split('|')
                    if len(parts) == 4:
                        # Old format - add URLs
                        timestamp, names, scores, fact = parts
                        name_list = names.split(',')
                        urls = ','.join([get_source_url_by_name(n) for n in name_list])
                        new_lines.append(f"{timestamp}|{names}|{scores}|{urls}|{fact}")
                        needs_update = True
                    elif len(parts) >= 5:
                        # Already has URLs or new format
                        new_lines.append(line)
                    else:
                        new_lines.append(line)

                if needs_update:
                    # Write back compressed
                    with gzip.open(gz_file, 'wt', encoding='utf-8') as f:
                        f.write('\n'.join(new_lines))
                    files_updated += 1
                    log.info(f"Updated archive: {gz_file.name}")

            except Exception as e:
                log.warning(f"Error processing {gz_file}: {e}")

    # Process current daily log files in data/
    for log_file in DATA_DIR.glob("????-??-??.txt"):
        try:
            with open(log_file, 'r') as f:
                content = f.read()

            new_lines = []
            needs_update = False
            for line in content.split('\n'):
                if line.startswith('#') or not line.strip():
                    new_lines.append(line)
                    continue

                parts = line.split('|')
                if len(parts) == 4:
                    # Old format - add URLs
                    timestamp, names, scores, fact = parts
                    name_list = names.split(',')
                    urls = ','.join([get_source_url_by_name(n) for n in name_list])
                    new_lines.append(f"{timestamp}|{names}|{scores}|{urls}|{fact}")
                    needs_update = True
                elif len(parts) >= 5:
                    # Already has URLs
                    new_lines.append(line)
                else:
                    new_lines.append(line)

            if needs_update:
                with open(log_file, 'w') as f:
                    f.write('\n'.join(new_lines))
                files_updated += 1
                log.info(f"Updated daily log: {log_file.name}")

        except Exception as e:
            log.warning(f"Error processing {log_file}: {e}")

    return files_updated


def rebuild_feed_with_urls():
    """Rebuild feed.xml to include source URLs in all items."""
    JTF_NS = "https://jtfnews.com/rss"
    ATOM_NS = "http://www.w3.org/2005/Atom"

    docs_dir = BASE_DIR / "docs"
    feed_file = docs_dir / "feed.xml"

    if not feed_file.exists():
        log.warning("No feed.xml found")
        return False

    try:
        tree = ET.parse(feed_file)
        root = tree.getroot()
        channel = root.find("channel")

        items_updated = 0
        for item in channel.findall("item"):
            # Find source elements (try namespaced first, then non-namespaced)
            for source_el in item.findall(f"{{{JTF_NS}}}source"):
                name = source_el.get("name", "")
                if name and not source_el.get("url"):
                    url = get_source_url_by_name(name)
                    if url:
                        source_el.set("url", url)
                        items_updated += 1

            # Also check non-namespaced (legacy)
            for source_el in item.findall("source"):
                name = source_el.get("name", "")
                if name and not source_el.get("url"):
                    url = get_source_url_by_name(name)
                    if url:
                        source_el.set("url", url)
                        items_updated += 1

        # Write back
        indent_xml(root, space="  ")
        with open(feed_file, 'wb') as f:
            tree.write(f, encoding="utf-8", xml_declaration=True)
        clean_duplicate_namespaces(feed_file)

        log.info(f"Updated feed.xml: {items_updated} source elements updated")
        return True

    except Exception as e:
        log.error(f"Error rebuilding feed.xml: {e}")
        return False


def rebuild_stories_json_with_urls():
    """Rebuild stories.json to include source_urls for all stories."""
    stories_file = DATA_DIR / "stories.json"

    if not stories_file.exists():
        log.warning("No stories.json found")
        return False

    try:
        with open(stories_file) as f:
            data = json.load(f)

        stories_updated = 0
        for story in data.get("stories", []):
            if "source_urls" not in story or not story["source_urls"]:
                # Parse source names from source string
                source_str = story.get("source", "")
                source_urls = {}

                # Source format: "Name1 score1 . Name2 score2" or "Name1 score1|score2 . Name2 ..."
                for part in source_str.split(" · "):
                    part = part.strip()
                    if not part:
                        continue
                    # Extract name (everything before the first digit or score)
                    name = part
                    for i, c in enumerate(part):
                        if c.isdigit():
                            name = part[:i].strip()
                            break
                    if name:
                        url = get_source_url_by_name(name)
                        if url:
                            source_urls[name] = url

                if source_urls:
                    story["source_urls"] = source_urls
                    stories_updated += 1

        # Write back
        with open(stories_file, 'w') as f:
            json.dump(data, f, indent=2)

        # Also copy to docs
        docs_dir = BASE_DIR / "docs"
        if docs_dir.exists():
            import shutil
            shutil.copy(stories_file, docs_dir / "stories.json")

        log.info(f"Updated stories.json: {stories_updated} stories updated")
        return True

    except Exception as e:
        log.error(f"Error rebuilding stories.json: {e}")
        return False


def rebuild_all_with_urls():
    """Rebuild all archives, feed.xml, and stories.json with source URLs."""
    log.info("=== Rebuilding all data with source URLs ===")

    # 1. Rebuild archives
    log.info("1. Rebuilding archives...")
    archive_count = rebuild_archives_with_urls()
    log.info(f"   Updated {archive_count} archive files")

    # 2. Rebuild feed.xml
    log.info("2. Rebuilding feed.xml...")
    rebuild_feed_with_urls()

    # 3. Rebuild stories.json
    log.info("3. Rebuilding stories.json...")
    rebuild_stories_json_with_urls()

    log.info("=== Rebuild complete ===")
    return True


if __name__ == "__main__":
    # Handle CLI arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--rebuild":
            log.info("Rebuilding stories.json from daily log...")
            if rebuild_stories_from_log():
                log.info("Rebuild complete!")
            else:
                log.error("Rebuild failed!")
                sys.exit(1)
            sys.exit(0)

        elif sys.argv[1] == "--audit":
            log.info("Running quarterly ownership audit...")
            if perform_ownership_audit():
                log.info("Audit complete!")
            else:
                log.error("Audit incomplete or cancelled.")
                sys.exit(1)
            sys.exit(0)

        elif sys.argv[1] == "--apply-audit":
            # Apply pending audit changes (for non-interactive mode)
            pending_file = DATA_DIR / "ownership_audit_pending.json"
            if not pending_file.exists():
                log.error("No pending audit found. Run --audit first.")
                sys.exit(1)

            with open(pending_file) as f:
                pending = json.load(f)

            log.info(f"Applying pending audit from {pending['quarter']}...")
            log.info(f"Changes to apply: {len(pending['changes'])}")

            for change in pending["changes"]:
                log.info(f"  {change['source_name']}: {change['notes']}")

            response = input("Apply these changes? (yes/no): ").strip().lower()
            if response != "yes":
                log.info("Cancelled.")
                sys.exit(1)

            apply_ownership_changes(pending["changes"])

            # Log the audit
            audit_file = DATA_DIR / "ownership_audit.json"
            audit_data = {
                "last_quarter": pending["quarter"],
                "audit_date": datetime.now().isoformat(),
                "changes_applied": len(pending["changes"]),
                "sources_verified": len(pending["verified"]),
                "change_details": pending["changes"]
            }
            with open(audit_file, 'w') as f:
                json.dump(audit_data, f, indent=2)

            # Remove pending file
            pending_file.unlink()

            log.info("Audit applied successfully!")
            sys.exit(0)

        elif sys.argv[1] == "--regenerate-rss":
            log.info("Regenerating RSS feed with rich source data...")
            if regenerate_rss_feed():
                log.info("RSS feed regeneration complete!")
                print("\nFeed regenerated. Run bu.sh to commit and push.")
            else:
                log.error("RSS feed regeneration failed")
            sys.exit(0)

        elif sys.argv[1] == "--rebuild-urls":
            log.info("Rebuilding all data with source URLs...")
            if rebuild_all_with_urls():
                log.info("Rebuild complete!")
                print("\nAll data rebuilt with source URLs. Run bu.sh to commit and push.")
            else:
                log.error("Rebuild failed")
            sys.exit(0)

        elif sys.argv[1] == "--regenerate-audio":
            # Regenerate audio for a specific date or multiple dates
            if len(sys.argv) < 3:
                print("Usage: python main.py --regenerate-audio YYYY-MM-DD [YYYY-MM-DD ...]")
                print("       python main.py --regenerate-audio --force YYYY-MM-DD [...]")
                sys.exit(1)

            force = False
            dates = []
            for arg in sys.argv[2:]:
                if arg == "--force":
                    force = True
                else:
                    dates.append(arg)

            if not dates:
                print("No dates specified")
                sys.exit(1)

            total_results = {'generated': 0, 'skipped': 0, 'failed': 0}
            for date in dates:
                results = regenerate_audio_for_date(date, force=force)
                total_results['generated'] += results['generated']
                total_results['skipped'] += results['skipped']
                total_results['failed'] += results['failed']

            print(f"\n=== Total Results ===")
            print(f"Generated: {total_results['generated']}")
            print(f"Skipped: {total_results['skipped']}")
            print(f"Failed: {total_results['failed']}")
            sys.exit(0 if total_results['failed'] == 0 else 1)

        else:
            print(f"Unknown argument: {sys.argv[1]}")
            print("Usage: python main.py [--rebuild | --audit | --apply-audit | --regenerate-rss | --rebuild-urls | --regenerate-audio]")
            sys.exit(1)

    main()
