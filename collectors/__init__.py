"""
Data collectors for crypto derivatives market intelligence dashboard.
"""

import time
import requests

DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds, doubles each retry


def api_get(url, params=None, timeout=DEFAULT_TIMEOUT):
    """Make a GET request with retries and exponential backoff."""
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, params=params, timeout=timeout)
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


def api_post(url, json_body, timeout=DEFAULT_TIMEOUT):
    """Make a POST request with retries and exponential backoff."""
    for attempt in range(MAX_RETRIES):
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
