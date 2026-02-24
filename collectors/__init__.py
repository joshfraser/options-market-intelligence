"""
Data collectors for crypto derivatives market intelligence dashboard.
"""

import time
import requests

DEFAULT_TIMEOUT = 30
MAX_RETRIES = 4
RETRY_DELAY = 2  # seconds, doubles each retry
REQUEST_INTERVAL = 0.5  # seconds between requests to avoid 429s

# Track last request time for throttling
_last_request_time = 0


def _throttle():
    """Wait if needed to stay under rate limits."""
    global _last_request_time
    now = time.monotonic()
    elapsed = now - _last_request_time
    if elapsed < REQUEST_INTERVAL:
        time.sleep(REQUEST_INTERVAL - elapsed)
    _last_request_time = time.monotonic()


def api_get(url, params=None, timeout=DEFAULT_TIMEOUT):
    """Make a GET request with retries, rate limiting, and exponential backoff."""
    for attempt in range(MAX_RETRIES):
        _throttle()
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            if resp.status_code == 400:
                print(f"  HTTP 400 Bad Request: {url}")
                if resp.text:
                    print(f"  Response: {resp.text[:200]}")
                return None
            if resp.status_code == 429:
                # Rate limited — use Retry-After header if available
                retry_after = int(resp.headers.get("Retry-After", 0))
                wait = max(retry_after, RETRY_DELAY * (2 ** attempt))
                print(f"  HTTP 429 Rate Limited: {url} (waiting {wait}s)")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except requests.HTTPError as e:
            print(f"  HTTP {resp.status_code}: {url} - {e}")
            if resp.status_code in (400, 404, 405):
                return None  # Don't retry client errors
            if attempt == MAX_RETRIES - 1:
                print(f"  FAILED after {MAX_RETRIES} attempts: {url}")
                return None
            wait = RETRY_DELAY * (2 ** attempt)
            print(f"  Retry {attempt + 1}/{MAX_RETRIES} for {url} (waiting {wait}s)")
            time.sleep(wait)
        except (requests.RequestException, ValueError) as e:
            if attempt == MAX_RETRIES - 1:
                print(f"  FAILED after {MAX_RETRIES} attempts: {url} - {e}")
                return None
            wait = RETRY_DELAY * (2 ** attempt)
            print(f"  Retry {attempt + 1}/{MAX_RETRIES} for {url} (waiting {wait}s)")
            time.sleep(wait)
    return None


def api_get_with_fallback(*urls, params=None, timeout=DEFAULT_TIMEOUT):
    """Try multiple URLs in order, returning the first successful response."""
    for url in urls:
        result = api_get(url, params=params, timeout=timeout)
        if result is not None:
            return result
        print(f"  Trying next fallback URL...")
    print(f"  All URLs failed for this request")
    return None


def api_post(url, json_body, timeout=DEFAULT_TIMEOUT):
    """Make a POST request with retries and exponential backoff."""
    for attempt in range(MAX_RETRIES):
        _throttle()
        try:
            resp = requests.post(url, json=json_body, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError) as e:
            if attempt == MAX_RETRIES - 1:
                print(f"  FAILED after {MAX_RETRIES} attempts: {url} - {e}")
                return None
            wait = RETRY_DELAY * (2 ** attempt)
            print(f"  Retry {attempt + 1}/{MAX_RETRIES} for {url} (waiting {wait}s)")
            time.sleep(wait)
    return None


def ts_to_date(ts):
    """Convert unix timestamp (seconds) to YYYY-MM-DD string."""
    return time.strftime("%Y-%m-%d", time.gmtime(ts))
