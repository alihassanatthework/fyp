"""
Groq LLM client (OpenAI-compatible chat completions, JSON mode).

Used by makeup/fashion services as the PRIMARY recommendation engine, with
the local Ollama call kept as an offline fallback. Groq hosts large models
(e.g. Llama-3.3-70B) for free and returns far more reliable, complete JSON
than the local 3B model.

No extra pip dependency — uses urllib (same as the existing Ollama calls).
Configure via .env / settings:
    GROQ_API_KEY   (required to enable; empty → disabled, falls back to Ollama)
    GROQ_MODEL     (default: llama-3.3-70b-versatile)
"""

import json
import logging
import urllib.request
import urllib.error

from django.conf import settings

logger = logging.getLogger(__name__)

GROQ_URL     = getattr(settings, 'GROQ_URL', 'https://api.groq.com/openai/v1/chat/completions')
GROQ_MODEL   = getattr(settings, 'GROQ_MODEL', 'llama-3.3-70b-versatile')
GROQ_API_KEY = getattr(settings, 'GROQ_API_KEY', '')
GROQ_TIMEOUT = 30


def groq_available() -> bool:
    return bool(GROQ_API_KEY)


def groq_json(prompt: str, system: str = None,
              temperature: float = 0.4, max_tokens: int = 900):
    """Call Groq with JSON mode. Returns a parsed dict, or None on any failure
    (so the caller can fall back to Ollama / rule-based)."""
    if not GROQ_API_KEY:
        return None

    messages = []
    if system:
        messages.append({'role': 'system', 'content': system})
    messages.append({'role': 'user', 'content': prompt})

    body = json.dumps({
        'model': GROQ_MODEL,
        'messages': messages,
        'temperature': temperature,
        'max_tokens': max_tokens,
        'response_format': {'type': 'json_object'},  # force valid JSON
    }).encode()

    req = urllib.request.Request(
        GROQ_URL, data=body, method='POST',
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {GROQ_API_KEY}',
            # Cloudflare (in front of api.groq.com) returns 403/1010 for the
            # default "Python-urllib" UA, so present a normal browser UA.
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/124.0 Safari/537.36',
            'Accept': 'application/json',
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=GROQ_TIMEOUT) as resp:
            data = json.loads(resp.read())
        text = data['choices'][0]['message']['content']
        return json.loads(text)
    except urllib.error.HTTPError as exc:
        logger.warning("Groq HTTP %s: %s", exc.code, exc.read()[:300] if hasattr(exc, 'read') else exc)
    except Exception as exc:
        logger.warning("Groq call failed: %s", exc)
    return None
