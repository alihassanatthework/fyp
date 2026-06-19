"""
Safepay payment gateway client (cards: Visa/Mastercard/PayPak + Easypaisa + JazzCash).

All Safepay HTTP calls live here so the exact API contract is in ONE place.
Reads keys from settings (SAFEPAY_*). When keys are absent, is_configured()
returns False and the caller falls back to the built-in demo checkout.

Flow (hosted checkout):
  1. create_session(amount) → ask Safepay for a payment "tracker" token (uses secret key)
  2. checkout_url(tracker, ...) → build the hosted-checkout URL the user is redirected to
  3. Safepay redirects back to FRONTEND with ?tracker=...&sig=... and ALSO calls our webhook
  4. verify_webhook(payload, signature) → confirm the signed event before granting premium

NOTE: Safepay periodically revises endpoint paths/versions. The two functions that
touch their REST API (create_session, _verify) are the only places to adjust if their
dashboard shows a newer version — everything else is provider-agnostic.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import urllib.request
import urllib.error

from django.conf import settings


def is_configured() -> bool:
    return bool(getattr(settings, 'SAFEPAY_API_KEY', '') and
                getattr(settings, 'SAFEPAY_SECRET_KEY', ''))


def _post(url: str, body: dict, headers: dict) -> dict | None:
    data = json.dumps(body).encode('utf-8')
    req = urllib.request.Request(url, data=data, method='POST')
    req.add_header('Content-Type', 'application/json')
    req.add_header('Accept', 'application/json')
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        try:
            err = e.read().decode('utf-8')
        except Exception:
            err = str(e)
        print(f"⚠️ Safepay HTTP {e.code}: {err}")
        return None
    except Exception as e:
        print(f"⚠️ Safepay request failed: {e}")
        return None


def create_session(amount: float, currency: str = 'PKR') -> str | None:
    """Create a payment session and return the tracker token, or None on failure.
    Safepay expects the amount in the major unit (PKR), as a number."""
    if not is_configured():
        return None
    url = f"{settings.SAFEPAY_API_BASE}/order/v1/init"
    body = {
        'client': settings.SAFEPAY_API_KEY,
        'amount': round(float(amount), 2),
        'currency': currency,
        'environment': settings.SAFEPAY_ENVIRONMENT,
    }
    res = _post(url, body, headers={'X-SFPY-MERCHANT-SECRET': settings.SAFEPAY_SECRET_KEY})
    if not res:
        return None
    # Safepay returns the tracker under data.token (a.k.a. tracker).
    data = res.get('data') or {}
    return data.get('token') or data.get('tracker')


def checkout_url(tracker: str, redirect_url: str, cancel_url: str,
                 order_id: str = '') -> str:
    """Build the hosted-checkout URL the browser is redirected to. The hosted page
    is where the user picks Card / Easypaisa / JazzCash."""
    from urllib.parse import urlencode
    params = {
        'env': settings.SAFEPAY_ENVIRONMENT,
        'beacon': tracker,
        'source': 'custom',
        'redirect_url': redirect_url,
        'cancel_url': cancel_url,
    }
    if order_id:
        params['order_id'] = order_id
    return f"{settings.SAFEPAY_CHECKOUT_BASE}/embedded/?{urlencode(params)}"


def verify_webhook(raw_body: bytes, signature: str) -> bool:
    """Verify a Safepay webhook signature (HMAC-SHA256 of the raw body with the
    webhook secret). Returns False if no secret is configured."""
    secret = getattr(settings, 'SAFEPAY_WEBHOOK_SECRET', '')
    if not secret or not signature:
        return False
    expected = hmac.new(secret.encode('utf-8'), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def _get(url: str, headers: dict) -> dict | None:
    req = urllib.request.Request(url, method='GET')
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"⚠️ Safepay status request failed: {e}")
        return None


def get_order(tracker: str) -> dict | None:
    """Fetch the order/tracker record from Safepay. Returns the `data` dict
    (with `state` and `transaction`) or None."""
    if not is_configured() or not tracker:
        return None
    url = f"{settings.SAFEPAY_API_BASE}/order/v1/{tracker}"
    res = _get(url, headers={'X-SFPY-MERCHANT-SECRET': settings.SAFEPAY_SECRET_KEY})
    return (res or {}).get('data')


def is_order_paid(tracker: str) -> bool:
    """True if Safepay reports the tracker as successfully paid. Authoritative
    confirmation by querying Safepay directly (used on redirect-back)."""
    data = get_order(tracker)
    if not data:
        return False
    state = str(data.get('state', '')).upper()
    txn = data.get('transaction')
    paid_states = {'TRACKER_ENDED', 'PAID', 'COMPLETED', 'CAPTURED', 'SUCCEEDED'}
    # Either a terminal "paid" state, or a populated transaction with a paid status.
    if state in paid_states:
        return True
    if isinstance(txn, dict):
        tstate = str(txn.get('state') or txn.get('status') or '').upper()
        if tstate in {'PAID', 'TRACKER_ENDED', 'COMPLETED', 'CAPTURED', 'SUCCEEDED', 'APPROVED'}:
            return True
    return False
