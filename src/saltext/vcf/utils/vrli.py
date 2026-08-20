"""
VMware Log Insight / VCF Operations for Logs (vRLI) REST connection helpers.

vRLI exposes an integrated REST API at ``https://<master>:9543/api/v2/...``.
Authentication is an opaque bearer session token acquired with::

    POST /api/v2/sessions
    { "username": "admin", "password": "...", "provider": "Local" }
    ->
    { "userId": "...", "sessionId": "<opaque>", "ttl": 1800 }

Subsequent requests carry ``Authorization: Bearer <sessionId>``. The TTL is
refreshed on use; an expired token returns 401 with body
``{"errorMessage": "Session expired", ...}`` — this helper invalidates the
cache and retries once on that shape.

Pillar config lives under ``saltext.vcf.vrli``::

    saltext.vcf:
      vrli:
        host: vrli-master.example.test
        port: 9543               # optional; default 9543
        username: admin
        password: secret
        provider: Local          # optional; default "Local"
        verify_ssl: false        # optional; default True
"""

import logging

import requests
import urllib3

log = logging.getLogger(__name__)

_TOKEN_CACHE: dict[str, str] = {}


def get_config(opts, profile=None):
    """Extract vRLI connection config from Salt opts / pillar."""
    pillar = opts.get("pillar", {})
    root = pillar.get("saltext.vcf", {}) or opts.get("saltext.vcf", {})
    cfg = root.get("vrli", {})
    if profile:
        cfg = root.get("profiles", {}).get(profile, {}).get("vrli", cfg)
    return {
        "host": cfg.get("host") or cfg.get("hostname"),
        "port": int(cfg.get("port", 9543)),
        "username": cfg.get("username") or cfg.get("user"),
        "password": cfg.get("password"),
        "provider": cfg.get("provider", "Local"),
        "verify_ssl": cfg.get("verify_ssl", True),
    }


def _base_url(cfg):
    return f"https://{cfg['host']}:{cfg['port']}"


def get_token(opts, profile=None):
    """Acquire and cache a vRLI session token. Returns the raw sessionId string."""
    cfg = get_config(opts, profile=profile)
    if not cfg["host"]:
        raise RuntimeError(
            "saltext.vcf.vrli.host is not configured; cannot reach vRLI master"
        )
    verify = cfg["verify_ssl"]
    if not verify:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    cache_key = f"{cfg['host']}:{cfg['port']}:{cfg['username']}"
    if cache_key in _TOKEN_CACHE:
        return _TOKEN_CACHE[cache_key]

    resp = requests.post(
        f"{_base_url(cfg)}/api/v2/sessions",
        json={
            "username": cfg["username"],
            "password": cfg["password"],
            "provider": cfg["provider"],
        },
        verify=verify,
        timeout=30,
    )
    resp.raise_for_status()
    body = resp.json() or {}
    session_id = body.get("sessionId")
    if not session_id:
        raise RuntimeError(
            f"vRLI POST /api/v2/sessions did not return sessionId: {body!r}"
        )
    _TOKEN_CACHE[cache_key] = session_id
    return session_id


def invalidate_token(opts, profile=None):
    cfg = get_config(opts, profile=profile)
    _TOKEN_CACHE.pop(f"{cfg['host']}:{cfg['port']}:{cfg['username']}", None)


def _session(opts, profile=None):
    cfg = get_config(opts, profile=profile)
    verify = cfg["verify_ssl"]
    if not verify:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    token = get_token(opts, profile=profile)
    session = requests.Session()
    session.verify = verify
    session.headers.update(
        {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }
    )
    return session, _base_url(cfg)


def _looks_like_session_expired(resp):
    """True if a 401 response body carries vRLI's 'Session expired' marker."""
    if resp is None or resp.status_code != 401:
        return False
    try:
        body = resp.json()
    except ValueError:
        return False
    if not isinstance(body, dict):
        return False
    msg = str(body.get("errorMessage") or body.get("message") or "")
    return "session expired" in msg.lower() or "session has expired" in msg.lower()


def _request(opts, method, path, *, params=None, json=None, profile=None, timeout=30):
    session, base = _session(opts, profile=profile)
    url = f"{base}{path}"
    resp = session.request(method, url, params=params, json=json, timeout=timeout)
    if resp.status_code == 401 and _looks_like_session_expired(resp):
        invalidate_token(opts, profile=profile)
        session, base = _session(opts, profile=profile)
        resp = session.request(method, f"{base}{path}", params=params, json=json, timeout=timeout)
    resp.raise_for_status()
    if resp.content:
        try:
            return resp.json()
        except ValueError:
            return {"_raw": resp.text}
    return {}


def api_get(opts, path, params=None, profile=None):
    return _request(opts, "GET", path, params=params, profile=profile)


def api_post(opts, path, body=None, params=None, profile=None):
    return _request(opts, "POST", path, params=params, json=body, profile=profile)


def api_patch(opts, path, body=None, profile=None):
    return _request(opts, "PATCH", path, json=body, profile=profile)


def api_put(opts, path, body=None, profile=None):
    return _request(opts, "PUT", path, json=body, profile=profile)


def api_delete(opts, path, params=None, profile=None):
    return _request(opts, "DELETE", path, params=params, profile=profile)
