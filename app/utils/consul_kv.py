"""Consul KV reader — loads User service configuration from Consul Key-Value store.

Keys live under the prefix ``notebookum/user/``.  Every call is synchronous
and blocking: it is meant to be called once at startup (inside Config),
not on every request.

Fall-back chain for each key:
  1. Consul KV  →  ``GET /v1/kv/notebookum/user/{key}?raw``
  2. Caller-supplied default (usually an env-var or hard-coded safe value)
"""

import json
import logging
import os

import requests

logger = logging.getLogger(__name__)

_CONSUL_URL = os.environ.get("CONSUL_URL", "http://consul:8500")
_PREFIX = "notebookum/user"
_TIMEOUT = 3  # seconds — short so startup isn't blocked on a missing Consul


def get(key: str, default: str = "") -> str:
    """Return the raw string value for *key* from Consul KV.

    Uses the ``?raw`` query parameter so the response body is the plain value
    (no JSON wrapping, no base64 decoding needed).
    """
    url = f"{_CONSUL_URL}/v1/kv/{_PREFIX}/{key}?raw"
    try:
        resp = requests.get(url, timeout=_TIMEOUT)
        if resp.status_code == 200:
            value = resp.text.strip()
            logger.debug("consul_kv[user]: loaded %s/%s", _PREFIX, key)
            return value
        if resp.status_code == 404:
            logger.warning("consul_kv[user]: key not found — %s/%s (using default)", _PREFIX, key)
        else:
            logger.warning("consul_kv[user]: GET %s returned HTTP %s (using default)", key, resp.status_code)
    except requests.exceptions.ConnectionError:
        logger.warning("consul_kv[user]: Consul unreachable at %s (using default for %s)", _CONSUL_URL, key)
    except Exception as exc:
        logger.warning("consul_kv[user]: unexpected error reading %s: %s (using default)", key, exc)
    return default


def get_int(key: str, default: int) -> int:
    """Convenience wrapper — converts the KV value to int."""
    raw = get(key, str(default))
    try:
        return int(raw)
    except ValueError:
        logger.warning("consul_kv[user]: key %s value %r is not an integer, using default %d", key, raw, default)
        return default


def get_list(key: str, default: list) -> list:
    """Convenience wrapper — parses a JSON array stored in Consul KV."""
    raw = get(key, "")
    if not raw:
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("consul_kv[user]: key %s is not valid JSON (using default)", key)
        return default
