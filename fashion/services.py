"""
fashion/services.py
───────────────────
Body type detection  (from user-entered measurements; no fake math)
Skin tone detection  (reuse from makeup.services)
Fashion suggestions  (Ollama LLM with strict category schema + fallback)

The frontend collects optional bust / waist / hip measurements at upload.
If present we compute true ratios. If absent or invalid, the user is asked
to pick a body type explicitly via a UI fallback selector and we honour
that value end-to-end.
"""
import os
import hashlib
import logging
import json
import urllib.request
import urllib.error

from django.conf import settings

logger = logging.getLogger(__name__)

OLLAMA_URL    = getattr(settings, 'OLLAMA_URL', os.environ.get('OLLAMA_URL', 'http://localhost:11434'))
OLLAMA_MODEL  = getattr(settings, 'OLLAMA_MODEL', 'llama3.2')
OLLAMA_TIMEOUT = 180

VALID_BODY_TYPES = {
    'Hourglass', 'Pear', 'Apple', 'Rectangle', 'Inverted Triangle', 'Unknown',
}

# ── Event normalisation ─────────────────────────────────────────────────────
# Lossless aliasing: every frontend event maps to a distinct LLM context tag
# so nuance is preserved (Dinner is "elegant", not "party").
EVENT_ALIASES = {
    'casual':       'casual',
    'street':       'street',
    'formal':       'formal',
    'wedding':      'formal',
    'party':        'party',
    'office':       'business',
    'business':     'business',
    'dinner':       'elegant',
    'date_night':   'romantic',
    'romantic':     'romantic',
    'traditional':  'traditional',
    'outdoor':      'outdoor',
    'sports':       'sports',
    'other':        'casual',
}

REQUIRED_FASHION_KEYS = {
    'tops', 'bottoms', 'dresses', 'footwear', 'accessories',
    'colors', 'aesthetics', 'palette',
}
CATEGORY_KEYS = ('tops', 'bottoms', 'dresses', 'footwear', 'accessories')


# ── Body type from measurements (the only honest path) ─────────────────────

def classify_body_type(bust_cm=None, waist_cm=None, hip_cm=None) -> str:
    """
    Standard body-type classification used in styling guides.
    All three measurements required; otherwise returns Unknown so the
    UI can prompt the user to pick a type explicitly.
    """
    try:
        bust  = float(bust_cm)  if bust_cm  not in (None, '') else None
        waist = float(waist_cm) if waist_cm not in (None, '') else None
        hip   = float(hip_cm)   if hip_cm   not in (None, '') else None
    except (TypeError, ValueError):
        return 'Unknown'

    if not (bust and waist and hip) or bust <= 0 or waist <= 0 or hip <= 0:
        return 'Unknown'

    bust_to_hip   = bust / hip
    waist_to_bust = waist / bust
    waist_to_hip  = waist / hip

    # Hourglass: balanced bust/hip with defined waist
    if 0.92 <= bust_to_hip <= 1.08 and waist_to_hip <= 0.78:
        return 'Hourglass'
    # Pear: hips meaningfully wider than bust
    if bust_to_hip <= 0.88:
        return 'Pear'
    # Inverted Triangle: bust/shoulder wider than hips
    if bust_to_hip >= 1.12:
        return 'Inverted Triangle'
    # Apple: waist not defined relative to bust/hip
    if waist_to_bust >= 0.85 or waist_to_hip >= 0.85:
        return 'Apple'
    # Default: balanced, less defined waist
    return 'Rectangle'


def detect_body_type(image_path_or_user_choice, bust=None, waist=None, hip=None):
    """
    Public entry point — accepts either measurements OR an explicit user
    choice. The legacy MediaPipe Pose math was mathematically degenerate
    (always returned the same ratio) and has been removed.
    """
    # Direct user selection wins.
    if isinstance(image_path_or_user_choice, str) and image_path_or_user_choice in VALID_BODY_TYPES:
        return image_path_or_user_choice
    # Otherwise try measurements.
    return classify_body_type(bust, waist, hip)


def detect_body_type_from_pose(image_path: str) -> str:
    """Estimate body type from a full-body photo using MediaPipe Pose.

    Uses the shoulder-width vs hip-width ratio (both horizontal distances, so
    the ratio is scale- and distance-invariant — this is what made the old
    implementation degenerate: it didn't normalise correctly).

    Pose gives shoulders + hips reliably but NOT the waist, so it can place:
        shoulders wider  → Inverted Triangle
        hips wider        → Pear
        balanced          → Rectangle
    (Hourglass/Apple need a waist measurement, so we don't guess those here.)
    Returns 'Unknown' if a confident pose can't be found.
    """
    try:
        import cv2
        import mediapipe as mp
        img = cv2.imread(image_path)
        if img is None:
            return 'Unknown'
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        with mp.solutions.pose.Pose(static_image_mode=True, model_complexity=1,
                                    min_detection_confidence=0.5) as pose:
            res = pose.process(rgb)
        if not res.pose_landmarks:
            return 'Unknown'
        lm = res.pose_landmarks.landmark
        # 11/12 shoulders, 23/24 hips
        for idx in (11, 12, 23, 24):
            if lm[idx].visibility < 0.5:
                return 'Unknown'
        shoulder_w = abs(lm[11].x - lm[12].x)
        hip_w      = abs(lm[23].x - lm[24].x)
        if hip_w <= 1e-6:
            return 'Unknown'
        ratio = shoulder_w / hip_w
        if ratio >= 1.10:
            return 'Inverted Triangle'
        if ratio <= 0.90:
            return 'Pear'
        return 'Rectangle'
    except Exception:
        return 'Unknown'


# ── Ollama Fashion Suggestions ───────────────────────────────────────────────

def _stable_seed(*parts) -> int:
    h = hashlib.sha256('|'.join(str(p) for p in parts).encode()).hexdigest()
    return int(h[:8], 16)


def _build_fashion_prompt(body_type, skin_tone, event, measurements=None, season='all-season',
                          gender='female', undertone='neutral'):
    import random
    g = 'men' if str(gender).lower() == 'male' else 'women'
    gender_line = (f"- Audience: {g}'s fashion ONLY. Every item (tops, bottoms, "
                   f"dresses/outerwear, footwear, accessories, jewellery) must be "
                   f"appropriate for {g}. Do not suggest items for the other gender.\n")

    # Fix 2 — controlled variety: rotate a styling angle so repeat runs differ.
    style_angle = random.choice([
        'modern minimalist', 'timeless classic', 'bold statement', 'soft romantic',
        'editorial high-fashion', 'relaxed elevated', 'sleek monochrome', 'eclectic mix',
    ])

    # Fix 1 — palette MUST be derived from skin tone + undertone + season + event,
    # NOT a generic event palette. This is what makes each person's colours differ.
    color_directive = (
        "COLOUR DIRECTIVE — derive the 5-colour palette from ALL of:\n"
        f"  • Undertone '{undertone}': warm → earthy/golden (terracotta, olive, camel, rust, gold); "
        "cool → jewel tones (sapphire, emerald, plum, burgundy, icy grey); "
        "neutral → balanced (taupe, soft white, slate, dusty rose).\n"
        f"  • Skin tone '{skin_tone}': deeper skin → richer, more saturated colours; "
        "fairer skin → softer, lighter values.\n"
        f"  • Season '{season}': spring/summer → lighter & brighter; autumn/winter → deeper & warmer.\n"
        f"  • Event '{event}': adjust formality/contrast to suit.\n"
        "  • Make the palette DISTINCT to this exact combination — avoid defaulting to "
        "the same neutrals every time.\n"
        f"  • Styling angle for this look: '{style_angle}'.\n"
    )
    measurement_line = ''
    if measurements:
        m = measurements
        if m.get('bust') or m.get('waist') or m.get('hip'):
            measurement_line = (
                f"- Measurements (cm): bust={m.get('bust') or '?'}, "
                f"waist={m.get('waist') or '?'}, hip={m.get('hip') or '?'}\n"
            )

    example1 = (
        'EXAMPLE — (Hourglass, Medium, formal, autumn):\n'
        '{"tops": {"title": "Tops", "items": ["Silk wrap blouse", "Tailored shell", '
        '"V-neck cashmere", "Cowl-neck satin top"], "tip": "Define the waist with wrap '
        'cuts and tucked-in lines."},'
        ' "bottoms": {"title": "Bottoms", "items": ["High-waist wide-leg trousers", '
        '"Pencil skirt", "A-line midi skirt", "Tailored cigarette pants"], "tip": "High '
        'rises elongate; avoid drop waists."},'
        ' "dresses": {"title": "Dresses", "items": ["Wrap dress", "Sheath dress", '
        '"Fit-and-flare midi", "Belted column"], "tip": "Belt at the natural waist."},'
        ' "footwear": {"title": "Footwear", "items": ["Pointed-toe pumps", "Block-heel '
        'mules", "Ankle boots", "Strappy sandals"], "tip": "Pointed toes elongate the leg."},'
        ' "accessories": {"title": "Accessories", "items": ["Structured clutch", "Pearl '
        'studs", "Leather belt", "Silk scarf"], "tip": "One statement piece — let the '
        'silhouette speak."},'
        ' "colors": [{"name": "Burgundy", "hex": "#7B1E3E"}, {"name": "Cream", "hex": '
        '"#F5EFE6"}, {"name": "Olive", "hex": "#556B2F"}, {"name": "Navy", "hex": '
        '"#1A2456"}, {"name": "Camel", "hex": "#C19A6B"}],'
        ' "aesthetics": ["Timeless", "Polished", "Sophisticated", "Understated luxury"],'
        ' "palette": "Autumn Luxe"}\n'
    )
    example2 = (
        'EXAMPLE — (Pear, Light, casual, summer):\n'
        '{"tops": {"title": "Tops", "items": ["Boat-neck tee", "Off-shoulder blouse", '
        '"Embellished cami", "Statement-sleeve top"], "tip": "Volume on top balances '
        'the hip."},'
        ' "bottoms": {"title": "Bottoms", "items": ["Straight-leg jeans", "A-line '
        'denim skirt", "Wide-leg linen pants", "Dark bootcut jeans"], "tip": "Dark '
        'bottoms streamline the lower half."},'
        ' "dresses": {"title": "Dresses", "items": ["A-line sundress", "Empire-waist '
        'midi", "Fit-and-flare cotton", "Halter-neck maxi"], "tip": "Draw the eye up '
        'with detail on top."},'
        ' "footwear": {"title": "Footwear", "items": ["White sneakers", "Espadrille '
        'wedges", "Flat sandals", "Loafers"], "tip": "Nude shoes elongate the leg."},'
        ' "accessories": {"title": "Accessories", "items": ["Statement earrings", '
        '"Straw tote", "Layered necklace", "Wide-brim hat"], "tip": "Eye-level '
        'accessories balance the proportions."},'
        ' "colors": [{"name": "Coral", "hex": "#FF7F60"}, {"name": "Ivory", "hex": '
        '"#FFFFF0"}, {"name": "Denim", "hex": "#1560BD"}, {"name": "Sage", "hex": '
        '"#9CAF88"}, {"name": "Blush", "hex": "#F4A7A7"}],'
        ' "aesthetics": ["Effortless", "Soft casual", "Sun-kissed", "Coastal"],'
        ' "palette": "Coastal Cool"}\n'
    )

    return (
        "You are a professional fashion stylist with 15 years of experience in "
        "personal styling and editorial work.\n"
        "Reason about silhouette and proportion internally, then OUTPUT ONLY JSON.\n\n"
        "STEP 1 — Identify the visual goal for the body type (where to add/draw, "
        "where to streamline).\n"
        "STEP 2 — Choose ONE hero silhouette that meets that goal for the event.\n"
        "STEP 3 — Fill every category with pieces that work with the hero.\n\n"
        "SCHEMA — every key REQUIRED, exact shape:\n"
        '{\n'
        '  "tops":        {"title": "Tops",        "items": ["", "", "", ""], "tip": ""},\n'
        '  "bottoms":     {"title": "Bottoms",     "items": ["", "", "", ""], "tip": ""},\n'
        '  "dresses":     {"title": "Dresses",     "items": ["", "", "", ""], "tip": ""},\n'
        '  "footwear":    {"title": "Footwear",    "items": ["", "", "", ""], "tip": ""},\n'
        '  "accessories": {"title": "Accessories", "items": ["", "", "", ""], "tip": ""},\n'
        '  "colors":      [{"name": "", "hex": "#RRGGBB"}, ...×5],\n'
        '  "aesthetics":  ["", "", "", ""],\n'
        '  "palette":     "Short evocative palette name"\n'
        '}\n\n'
        "HARD RULES:\n"
        "- EXACTLY 4 items per category (tops, bottoms, dresses, footwear, accessories)\n"
        "- EXACTLY 5 colors, each with a real 6-char hex (#RRGGBB)\n"
        "- EXACTLY 4 aesthetics — short evocative single words or two-word phrases\n"
        "- Tip strings under 130 characters each\n"
        "- No brand names; describe pieces by silhouette and fabric\n\n"
        f"{color_directive}\n"
        f"{example1}\n{example2}\n"
        "NOW GENERATE FOR:\n"
        f"{gender_line}"
        f"- Body type : {body_type}\n"
        f"- Skin tone : {skin_tone}\n"
        f"- Undertone : {undertone}\n"
        f"- Event     : {event}\n"
        f"{measurement_line}"
        f"- Season    : {season}\n\n"
        "Output JSON only matching schema above. No preamble. No explanation."
    )


def _is_hex(s):
    return isinstance(s, str) and len(s) == 7 and s.startswith('#') and all(
        c in '0123456789abcdefABCDEF' for c in s[1:]
    )


def _validate_fashion_json(parsed):
    if not isinstance(parsed, dict):
        return False
    missing = REQUIRED_FASHION_KEYS - set(parsed.keys())
    if missing:
        logger.warning("Fashion LLM missing keys: %s", missing)
        return False
    for cat in CATEGORY_KEYS:
        obj = parsed.get(cat)
        if not isinstance(obj, dict) or not isinstance(obj.get('items'), list):
            logger.warning("Fashion LLM: %s shape wrong", cat); return False
        if len(obj['items']) != 4 or not all(isinstance(x, str) and x.strip() for x in obj['items']):
            logger.warning("Fashion LLM: %s needs 4 string items, got %s", cat, obj['items']); return False
        if not isinstance(obj.get('tip'), str) or not obj['tip'].strip():
            logger.warning("Fashion LLM: %s tip missing/empty", cat); return False
        if not isinstance(obj.get('title'), str):
            obj['title'] = cat.capitalize()
    colors = parsed.get('colors')
    if not isinstance(colors, list) or len(colors) != 5:
        logger.warning("Fashion LLM: need exactly 5 colors, got %s", colors); return False
    for c in colors:
        if not isinstance(c, dict) or not _is_hex(c.get('hex', '')) or not isinstance(c.get('name'), str):
            logger.warning("Fashion LLM: bad color entry %s", c); return False
    aesthetics = parsed.get('aesthetics')
    if not isinstance(aesthetics, list) or len(aesthetics) != 4 \
       or not all(isinstance(a, str) and a.strip() for a in aesthetics):
        logger.warning("Fashion LLM: need 4 aesthetics strings, got %s", aesthetics); return False
    if not isinstance(parsed.get('palette'), str) or not parsed['palette'].strip():
        logger.warning("Fashion LLM: missing palette name"); return False
    return True


def get_fashion_suggestions(body_type, skin_tone, event_type,
                             measurements=None, season='all-season', gender='female',
                             undertone='neutral'):
    """
    Call Ollama with strict category schema. Validate exact shape.
    Fall back to rule-based if anything fails.
    """
    event = EVENT_ALIASES.get(str(event_type).lower().strip(), 'casual')
    prompt = _build_fashion_prompt(body_type, skin_tone, event, measurements, season, gender, undertone)
    seed = _stable_seed(body_type, skin_tone, event, season)

    # ── PRIMARY: Groq (large model, reliable JSON). Falls through to Ollama. ──
    try:
        from core.llm_groq import groq_json, groq_available
        if groq_available():
            parsed = groq_json(
                prompt,
                system=("You are a professional fashion stylist. Respond with ONLY "
                        "a valid JSON object matching the requested schema — no prose. "
                        "Include EVERY category key requested."),
                temperature=0.65,   # Fix 2 — more variety between users/runs
            )
            if parsed and _validate_fashion_json(parsed):
                logger.info("Fashion suggestions via Groq.")
                return parsed
            logger.warning("Groq fashion output invalid; trying Ollama.")
    except Exception as exc:
        logger.warning("Groq fashion path errored (%s); trying Ollama.", exc)

    try:
        payload = json.dumps({
            'model':   OLLAMA_MODEL,
            'prompt':  prompt,
            'stream':  False,
            'format':  'json',
            'options': {
                'temperature':  0.4,
                'top_p':        0.9,
                'num_predict':  600,
                'seed':         seed,
            },
        }).encode()
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/generate",
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=OLLAMA_TIMEOUT) as resp:
            result = json.loads(resp.read())
            text   = (result.get('response') or '').strip()
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError as exc:
                logger.error("Fashion LLM JSON parse failed: %s | RAW=%s", exc, text[:500])
                parsed = None

            if parsed and _validate_fashion_json(parsed):
                return parsed
            logger.warning("Fashion LLM output failed schema validation; falling back.")

    except urllib.error.URLError as exc:
        logger.error("Ollama unreachable at %s: %s — using rule-based fashion fallback.",
                     OLLAMA_URL, exc)
    except Exception as exc:
        logger.exception("Unexpected Ollama failure (fashion): %s", exc)

    return _fallback_fashion(body_type, skin_tone, event)


# ── Schema-shaped rule-based fallback ───────────────────────────────────────

def _cat(title, items, tip):
    return {'title': title, 'items': items, 'tip': tip}


def _fallback_fashion(body_type, skin_tone, event):
    """Rule-based fallback that returns the EXACT same shape the LLM does."""
    # Colour palettes per skin tone.
    palettes = {
        'Fair':   [('Blush', '#FADADD'), ('Powder', '#D6E6F2'), ('Sage', '#9CAF88'),
                   ('Cream', '#F5EFE6'), ('Slate', '#708090')],
        'Light':  [('Coral', '#FF7F60'), ('Ivory', '#FFFFF0'), ('Denim', '#1560BD'),
                   ('Sage', '#9CAF88'), ('Blush', '#F4A7A7')],
        'Medium': [('Olive', '#556B2F'), ('Camel', '#C19A6B'), ('Rust', '#B7410E'),
                   ('Mustard', '#FFDB58'), ('Stone', '#8C8579')],
        'Tan':    [('Terracotta', '#C05C35'), ('Teal', '#008080'), ('Cream', '#F5EFE6'),
                   ('Burnt Sienna', '#E97451'), ('Navy', '#1A2456')],
        'Deep':   [('Emerald', '#046307'), ('Gold', '#D4AF37'), ('Ivory', '#FFFFF0'),
                   ('Crimson', '#DC143C'), ('Plum', '#8E4585')],
    }
    aesthetics = {
        'casual':       ['Effortless', 'Minimalist', 'Soft Casual', 'Everyday Chic'],
        'street':       ['Streetwear', 'Urban Cool', 'GRWM Casual', 'Hypebeast'],
        'formal':       ['Sophisticated', 'Timeless', 'Polished', 'Understated Luxury'],
        'party':        ['Glam', 'Maximalist', 'Y2K Revival', 'Club Chic'],
        'business':     ['Clean Professional', 'Quiet Luxury', 'Modern Corporate', 'Business Chic'],
        'elegant':      ['Smart Casual', 'Evening Chic', 'Effortless Glam', 'Date Night'],
        'romantic':     ['Romantic', 'Soft Glam', 'Modern Bride', 'Cottagecore Elegance'],
        'traditional':  ['Traditional Chic', 'Ethnic Fusion', 'Cultural Elegance', 'Heritage Luxe'],
        'outdoor':      ['Adventure', 'Functional', 'Earth-toned', 'Practical Cool'],
        'sports':       ['Athleisure', 'Performance', 'Streamlined', 'Casual Cool'],
    }

    # Body-type-specific items for each category.
    bt = body_type if body_type in VALID_BODY_TYPES else 'Unknown'
    tip = {
        'Hourglass':           'Define the waist; trust your natural proportions.',
        'Pear':                'Add volume up top to balance the hip.',
        'Apple':               'Empire and A-line cuts skim the midsection.',
        'Rectangle':           'Add curves with peplum, ruching, and belt cinch.',
        'Inverted Triangle':   'Add volume below the waist to balance the shoulders.',
        'Unknown':             'Trust well-fitting pieces and clear silhouettes.',
    }[bt]

    tops_items = {
        'Hourglass':         ['Wrap top', 'Tucked silk blouse', 'V-neck shell', 'Fitted button-up'],
        'Pear':               ['Boat-neck tee', 'Off-shoulder top', 'Embellished cami', 'Puff-sleeve blouse'],
        'Apple':              ['Empire-waist top', 'Drape-front blouse', 'V-neck flow tee', 'Open cardigan'],
        'Rectangle':          ['Peplum top', 'Ruffled blouse', 'Cropped sweater', 'Belted shirt'],
        'Inverted Triangle':  ['Scoop-neck tee', 'V-neck cashmere', 'Soft draped blouse', 'Wrap top'],
        'Unknown':            ['Well-fitted tee', 'Tucked blouse', 'Soft sweater', 'Tailored shirt'],
    }[bt]

    bottoms_items = {
        'Hourglass':         ['High-waist trousers', 'Pencil skirt', 'A-line midi', 'Cigarette pants'],
        'Pear':               ['Straight-leg jeans', 'Dark bootcut', 'Wide-leg linen', 'A-line skirt'],
        'Apple':              ['Wide-leg trousers', 'A-line midi skirt', 'Bootcut jeans', 'Palazzo pants'],
        'Rectangle':          ['Pleated trousers', 'Ruffled skirt', 'Wide-leg jeans', 'Pencil skirt'],
        'Inverted Triangle':  ['Wide-leg trousers', 'Flared jeans', 'A-line skirt', 'Palazzo pants'],
        'Unknown':            ['Straight-leg jeans', 'Tailored trousers', 'Midi skirt', 'Chinos'],
    }[bt]

    return {
        'tops':        _cat('Tops',        tops_items,    tip),
        'bottoms':     _cat('Bottoms',     bottoms_items, 'Pair with the tops above; mirror the silhouette.'),
        'dresses':     _cat('Dresses',
                            ['Wrap dress', 'Sheath dress', 'A-line midi', 'Belted column'],
                            'Belt at the natural waist for definition.'),
        'footwear':    _cat('Footwear',
                            ['Pointed-toe flats', 'Block-heel sandals', 'White sneakers', 'Ankle boots'],
                            'Pointed toes elongate the leg.'),
        'accessories': _cat('Accessories',
                            ['Structured bag', 'Delicate earrings', 'Leather belt', 'Silk scarf'],
                            'One statement piece — let the silhouette speak.'),
        'colors':      [{'name': n, 'hex': h} for n, h in palettes.get(skin_tone, palettes['Medium'])],
        'aesthetics':  aesthetics.get(event, aesthetics['casual']),
        'palette':     f"{skin_tone if skin_tone != 'Unknown' else 'Classic'} {event.title()}",
    }
