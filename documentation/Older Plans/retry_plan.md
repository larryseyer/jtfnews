# Retry Logic Implementation Plan

## Status: IMPLEMENTED (2025-02-13)

This is Phase 2 from the Resilience System plan (`docs/ResilienceSystem.md`).

---

## Goal

Add retry logic with exponential backoff to critical API calls in `main.py`. This prevents transient network/API failures from crashing the service.

---

## Implementation

### 1. Add the Decorator (~20 lines)

Add this decorator near the top of `main.py`, after the imports and before other function definitions (around line 50):

```python
import time
from functools import wraps

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
```

### 2. Apply to Critical Functions

**extract_fact() - Line 506** (CRITICAL)
```python
@retry_with_backoff(max_retries=3, base_delay=1.0)
def extract_fact(headline: str, use_cache: bool = True) -> dict:
```

**generate_tts() - Line 1419** (Non-critical, text still works if this fails)
```python
@retry_with_backoff(max_retries=2, base_delay=1.0)
def generate_tts(text: str, audio_index: int = None) -> str:
```

**send_alert() - Line 1741** (Non-critical, logging still works)
```python
@retry_with_backoff(max_retries=2, base_delay=0.5)
def send_alert(message: str, alert_type: str = "general"):
```

---

## What Gets Retried

| Exception Type | Retry? | Reason |
|----------------|--------|--------|
| ConnectionError | YES | Network blip |
| TimeoutError | YES | Slow response |
| OSError | YES | Socket issues |
| requests.exceptions.Timeout | YES | HTTP timeout |
| requests.exceptions.ConnectionError | YES | HTTP connection issue |
| anthropic.APIError | YES | Transient API issue |
| anthropic.RateLimitError | YES | Rate limit (back off) |
| anthropic.AuthenticationError | NO | Bad API key - won't fix itself |
| anthropic.BadRequestError | NO | Bad input - won't fix itself |

---

## Additional Consideration

The Anthropic SDK may have its own retry logic built in. Check if we're already using it:

```python
# If using anthropic library, check for existing retry config
client = anthropic.Anthropic(
    max_retries=3,  # Built-in retry support
)
```

If the Anthropic client already has retries configured, we may only need the decorator for ElevenLabs and Twilio calls.

---

## Testing

After implementation:
1. Temporarily break an API endpoint (wrong URL) and verify retries happen
2. Check logs show retry attempts with delays
3. Verify service continues after retries exhaust (graceful failure)

---

## Files to Modify

- `main.py` - Add decorator and apply to 3 functions (~25 lines total)
- `docs/SPECIFICATION.md` - Document retry behavior in Section 14 (optional)

---

## Commit Message

```
Add retry logic with exponential backoff for API calls

Phase 2 of Resilience System: Wraps extract_fact(), generate_tts(),
and send_alert() with retry decorator. Handles transient network
failures with 1s/2s/4s backoff delays.
```
