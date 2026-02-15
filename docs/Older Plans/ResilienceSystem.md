# JTF News Resilience System

## Problem Statement
JTF News needs to run 24/7 without going down. Current gaps:
- No retry logic for API failures
- JSON parsing fails silently when Claude returns invalid responses
- Limited alerting (only stream offline and contradictions)
- No validation of API keys/credits at startup
- No rate limit handling

## Design Principles
1. **Simplicity = Stability** (from whitepaper) - minimal code additions
2. **Graceful degradation** - continue with reduced functionality rather than crash
3. **Fail-safe defaults** - when uncertain, don't block stories
4. **Alert early** - notify before complete failure

---

## Phase 1: Startup Health Check (~40 lines)

### 1.1 New function `validate_services()`
Location: After configuration section, before main loop

```
Check at startup:
- ANTHROPIC_API_KEY: Make test API call (tiny prompt)
- ELEVENLABS_API_KEY: Validate key format, test endpoint
- TWILIO credentials: Validate format (don't send test SMS)
- Required environment variables present
```

**Behavior:**
- If critical service fails (Claude): Exit with clear error message
- If non-critical fails (ElevenLabs): Log warning, continue (text-only mode)
- If alerting fails (Twilio): Log warning, continue (no SMS alerts)

### 1.2 Add to main() before loop
```python
if not validate_services():
    log.critical("Service validation failed - cannot start")
    sys.exit(1)
```

---

## Phase 2: Retry Logic with Backoff (~30 lines)

### 2.1 New decorator `@retry_with_backoff`
```python
def retry_with_backoff(max_retries=3, base_delay=1.0):
    """Retry failed API calls with exponential backoff."""
```

- Retries: 3 attempts
- Delays: 1s, 2s, 4s (exponential)
- Catches: ConnectionError, Timeout, APIError, RateLimitError
- Does NOT retry: AuthenticationError (bad key), InvalidRequestError

### 2.2 Apply to critical functions
- `extract_fact()` - Critical (affects all stories)
- `generate_tts()` - Non-critical (text still works)
- `send_alert()` - Non-critical (log still works)

---

## Phase 3: Fix JSON Parsing (~20 lines)

### 3.1 New helper `safe_parse_claude_json()`
```python
def safe_parse_claude_json(text: str, default: dict) -> dict:
    """Parse Claude response with fallback for malformed JSON."""
    # Try standard JSON parse
    # Try extracting JSON from markdown code blocks
    # Try regex extraction of key fields
    # Return default if all fail
```

### 3.2 Apply to functions with missing fallbacks
- `check_contradiction()` - Line 1682
- `extract_new_details()` - Line 1768
- Pattern already exists in `extract_fact()` - copy that approach

---

## Phase 4: Enhanced Alerting (~50 lines)

### 4.1 Alert throttling
```python
_alert_cooldowns = {}  # {alert_type: last_sent_timestamp}
ALERT_COOLDOWN = 3600  # 1 hour between same alert type
```

### 4.2 New alert types
| Alert Type | Trigger | Cooldown |
|------------|---------|----------|
| `api_failure` | 3 consecutive API failures | 1 hour |
| `credits_low` | >80% of daily budget used | 24 hours |
| `queue_backup` | Queue >200 items or oldest >20 hours | 6 hours |
| `offline` | Stream offline >5 min (existing) | Until resolved |
| `contradiction` | Fact contradicts recent (existing) | None |

### 4.3 Update `send_alert()` with throttling
```python
def send_alert(message: str, alert_type: str = "general"):
    if not should_send_alert(alert_type):
        log.info(f"Alert throttled ({alert_type}): {message}")
        return
    # existing SMS logic
```

---

## Phase 5: Credit Monitoring (~25 lines)

### 5.1 Add to `write_monitor_data()`
Check if today's costs exceed 80% of daily budget:
```python
DAILY_BUDGET = 5.00  # $5/day budget
if costs.total_usd > DAILY_BUDGET * 0.8:
    send_alert(f"API costs at ${costs.total_usd:.2f} (80% of budget)", "credits_low")
```

### 5.2 Add to dashboard
- Show budget utilization percentage
- Color indicator: green (<50%), yellow (50-80%), red (>80%)

---

## Phase 6: Graceful Degradation Modes (~15 lines)

### 6.1 Track degraded state
```python
_degraded_services = set()  # {"elevenlabs", "twilio"}
```

### 6.2 Behavior when degraded
| Service Down | Behavior |
|--------------|----------|
| Claude | STOP - cannot verify facts |
| ElevenLabs | Continue - text-only mode (no TTS) |
| Twilio | Continue - log alerts instead of SMS |
| Network | Retry with backoff, then skip cycle |

---

## Critical Files to Modify

| File | Changes |
|------|---------|
| `main.py` | Add all resilience functions (~180 lines) |
| `gh-pages-dist/index.html` | Add budget indicator to costs section |

---

## Implementation Order

1. **Phase 3 first** - Fix immediate JSON parsing bug (quick win)
2. **Phase 1** - Startup validation (prevents silent failures)
3. **Phase 2** - Retry logic (handles transient failures)
4. **Phase 4** - Enhanced alerting (operational visibility)
5. **Phase 5** - Credit monitoring (prevent budget surprise)
6. **Phase 6** - Degradation modes (last resort)

---

## Verification Steps

1. **JSON fix test**: Simulate malformed Claude response, verify no crash
2. **Retry test**: Temporarily break API endpoint, verify retries happen
3. **Startup test**: Remove API key, verify clean error message
4. **Alert test**: Trigger each alert type, verify SMS received (with throttling)
5. **Budget test**: Set low budget, verify alert at 80%
6. **Degradation test**: Disable ElevenLabs, verify text-only mode works

---

## Estimated Scope

- **Total new code**: ~180 lines in main.py
- **Risk level**: Low (additive, doesn't change core verification logic)
- **Dependencies**: None new (uses existing libraries)
