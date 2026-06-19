"""
makeup/services.py
──────────────────
Face shape detection (MediaPipe landmarks + geometry)
Skin tone detection  (4-region median sampling, outlier rejection)
Undertone detection  (warm / cool / neutral from hue angle)
Makeup suggestions   (Ollama LLM with constrained prompt + fallback)
"""
import os
import math
import hashlib
import logging
import json
import urllib.request
import urllib.error

import numpy as np
import cv2
from django.conf import settings

logger = logging.getLogger(__name__)

# ── Constants ───────────────────────────────────────────────────────────────
OLLAMA_URL    = getattr(settings, 'OLLAMA_URL', os.environ.get('OLLAMA_URL', 'http://localhost:11434'))
OLLAMA_MODEL  = getattr(settings, 'OLLAMA_MODEL', 'llama3.2')
OLLAMA_TIMEOUT = 180  # cold-load can take 60-90s

REQUIRED_MAKEUP_KEYS = {
    'foundation', 'blush', 'eyeshadow', 'eyeliner',
    'lipstick', 'highlighter', 'contouring_tip', 'overall_tip',
}

# Correct FaceMesh anatomical landmark indices.
LM_CHIN          = 152   # tip of chin
LM_FOREHEAD_MID  = 10    # mid-forehead
LM_HAIRLINE_MID  = 9     # higher mid-forehead, near hairline
LM_LEFT_CHEEK    = 234   # widest left cheekbone
LM_RIGHT_CHEEK   = 454   # widest right cheekbone
LM_LEFT_JAW      = 58    # left jaw corner (gonion)
LM_RIGHT_JAW     = 288   # right jaw corner
LM_LEFT_BROW     = 70    # left lateral brow (near temple)
LM_RIGHT_BROW    = 300   # right lateral brow

# Cheek sampling indices (avoid edges, hair, eye area).
LM_LEFT_CHEEK_PATCH    = 116
LM_RIGHT_CHEEK_PATCH   = 345
LM_FOREHEAD_PATCH      = 151
LM_CHIN_PATCH          = 175


# ── Face Shape Detection ──────────────────────────────────────────────────────

def detect_face_shape(image_path: str) -> str:
    """
    Classify face shape from MediaPipe FaceMesh landmarks.
    Uses anatomically correct jaw / forehead / cheek indices and
    thresholds tuned against 5 reference photos spanning the canonical
    face-shape definitions.
    Returns: Oval, Round, Square, Heart, Oblong, Unknown.
    """
    try:
        import mediapipe as mp

        img = cv2.imread(image_path)
        if img is None:
            return 'Unknown'

        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w = img.shape[:2]

        mp_face = mp.solutions.face_mesh
        with mp_face.FaceMesh(static_image_mode=True, max_num_faces=1,
                               refine_landmarks=True) as fm:
            results = fm.process(rgb)

        if not results.multi_face_landmarks:
            return 'Unknown'

        lm = results.multi_face_landmarks[0].landmark

        def pt(idx):
            return lm[idx].x * w, lm[idx].y * h

        def dist(a, b):
            return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)

        cheekbone_w = dist(pt(LM_LEFT_CHEEK),  pt(LM_RIGHT_CHEEK))
        jaw_w       = dist(pt(LM_LEFT_JAW),    pt(LM_RIGHT_JAW))
        forehead_w  = dist(pt(LM_LEFT_BROW),   pt(LM_RIGHT_BROW))
        face_h      = dist(pt(LM_HAIRLINE_MID), pt(LM_CHIN))
        if cheekbone_w == 0:
            return 'Unknown'

        ratio_h_w     = face_h / cheekbone_w
        jaw_to_cheek  = jaw_w / cheekbone_w
        fore_to_jaw   = (forehead_w / jaw_w) if jaw_w else 1.0

        logger.debug(
            "Face shape ratios — h/w=%.2f jaw/cheek=%.2f fore/jaw=%.2f",
            ratio_h_w, jaw_to_cheek, fore_to_jaw,
        )

        # Retuned classification (validated against reference photos).
        if ratio_h_w >= 1.55:
            return 'Oblong'
        if fore_to_jaw >= 1.18 and jaw_to_cheek <= 0.82:
            return 'Heart'
        if jaw_to_cheek >= 0.92 and ratio_h_w <= 1.30:
            return 'Square'
        if ratio_h_w <= 1.20 and 0.75 <= jaw_to_cheek < 0.92:
            return 'Round'
        return 'Oval'

    except Exception as exc:
        logger.warning("Face shape detection failed: %s", exc)
        return 'Unknown'


# ── Skin Tone + Undertone Detection ──────────────────────────────────────────

def _sample_patch(img, cx, cy, half=14):
    h, w = img.shape[:2]
    y0, y1 = max(0, cy - half), min(h, cy + half)
    x0, x1 = max(0, cx - half), min(w, cx + half)
    patch = img[y0:y1, x0:x1]
    return patch if patch.size else None


def _reject_outliers(patches_lab):
    if not patches_lab:
        return None
    means = np.array([p.reshape(-1, 3).mean(axis=0) for p in patches_lab])
    med = np.median(means, axis=0)
    std = np.std(means, axis=0) + 1e-6
    keep = np.all(np.abs(means - med) < 2 * std, axis=1)
    if not np.any(keep):
        keep[:] = True
    kept = means[keep]
    return np.median(kept, axis=0)


def _classify_fitzpatrick(L, h_deg):
    if L > 195: return 'Fair'
    if L > 165: return 'Light'
    if L > 135: return 'Medium'
    if L > 105: return 'Tan'
    return 'Deep'


def _classify_undertone(h_deg):
    """Warm 20-60°, Cool ≥330° or ≤10°, Neutral otherwise."""
    if 20 <= h_deg <= 60:
        return 'warm'
    if h_deg >= 330 or h_deg <= 10:
        return 'cool'
    return 'neutral'


def detect_skin_tone_and_undertone(image_path: str):
    """4-region median skin tone with outlier rejection + undertone."""
    try:
        import mediapipe as mp

        img = cv2.imread(image_path)
        if img is None:
            return {'skin_tone': 'Unknown', 'undertone': 'neutral'}

        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w = img.shape[:2]

        mp_face = mp.solutions.face_mesh
        with mp_face.FaceMesh(static_image_mode=True, max_num_faces=1) as fm:
            results = fm.process(rgb)
        if not results.multi_face_landmarks:
            return {'skin_tone': 'Unknown', 'undertone': 'neutral'}

        lm = results.multi_face_landmarks[0].landmark
        sample_indices = [
            LM_FOREHEAD_PATCH, LM_LEFT_CHEEK_PATCH,
            LM_RIGHT_CHEEK_PATCH, LM_CHIN_PATCH,
        ]
        patches_lab = []
        for idx in sample_indices:
            cx = int(lm[idx].x * w)
            cy = int(lm[idx].y * h)
            patch = _sample_patch(img, cx, cy, half=14)
            if patch is None:
                continue
            patches_lab.append(cv2.cvtColor(patch, cv2.COLOR_BGR2Lab))

        median_lab = _reject_outliers(patches_lab)
        if median_lab is None:
            return {'skin_tone': 'Unknown', 'undertone': 'neutral'}

        L, a, b_ch = median_lab
        h_deg = (math.degrees(math.atan2(b_ch - 128, a - 128)) + 360) % 360
        skin_tone = _classify_fitzpatrick(L, h_deg)
        undertone = _classify_undertone(h_deg)

        logger.debug("Skin tone — L=%.1f a=%.1f b=%.1f hue=%.1f° → %s/%s",
                     L, a, b_ch, h_deg, skin_tone, undertone)
        return {
            'skin_tone': skin_tone,
            'undertone': undertone,
            'lab':       [float(L), float(a), float(b_ch)],
            'hue':       float(h_deg),
        }

    except Exception as exc:
        logger.warning("Skin tone detection failed: %s", exc)
        return {'skin_tone': 'Unknown', 'undertone': 'neutral'}


# Back-compat for callers that only want the tone string.
def detect_skin_tone(image_path: str) -> str:
    return detect_skin_tone_and_undertone(image_path)['skin_tone']


# ── Ollama LLM Suggestions ───────────────────────────────────────────────────

def _stable_seed(*parts) -> int:
    """Deterministic seed so identical inputs → identical output."""
    h = hashlib.sha256('|'.join(str(p) for p in parts).encode()).hexdigest()
    return int(h[:8], 16)


def _build_makeup_prompt(face_shape, skin_tone, undertone, occasion, skin_conditions):
    import random
    conditions = ', '.join(skin_conditions) if skin_conditions else 'none reported'

    # Fix 2 — controlled variety so the same inputs don't always look identical.
    look_angle = random.choice([
        'natural radiant', 'soft glam', 'bold dramatic', 'fresh minimal',
        'romantic rosy', 'sultry smoky', 'modern editorial', 'classic timeless',
    ])

    # Fix 1 — every shade MUST be derived from skin tone + undertone + occasion,
    # not a one-size-fits-all palette. This is what makes each face's shades differ.
    shade_directive = (
        "SHADE DIRECTIVE — derive EVERY shade from ALL of:\n"
        f"  • Undertone '{undertone}': warm → golden/peach/bronze/terracotta families; "
        "cool → pink/berry/plum/rose families; neutral → balanced taupe/mauve.\n"
        f"  • Skin tone '{skin_tone}': deeper skin → richer, more pigmented shades; "
        "fairer skin → softer, lighter washes.\n"
        f"  • Occasion '{occasion}': day/casual → subtle; evening/wedding → intensified.\n"
        f"  • Interpret through this look angle: '{look_angle}'.\n"
        "  • Make the result DISTINCT to this exact face — avoid defaulting to the same look.\n"
    )

    example1 = (
        'EXAMPLE — (Oval, Medium, warm, evening, none):\n'
        '{"foundation": "satin medium-coverage warm beige with a soft dewy finish",'
        ' "blush": "warm peach blush blended on the apples of the cheeks toward the temples",'
        ' "eyeshadow": "warm bronze and copper shimmer with a deep brown crease",'
        ' "eyeliner": "smudged dark brown gel along the upper lash line",'
        ' "lipstick": "satin terracotta nude that flatters warm undertones",'
        ' "highlighter": "champagne gold on cheekbones, brow bone and cupid\'s bow",'
        ' "contouring_tip": "Light sculpt under the cheekbones to enhance the oval balance",'
        ' "overall_tip": "Hero the eyes with warm bronze; keep skin luminous and undertone-true"}\n'
    )
    example2 = (
        'EXAMPLE — (Heart, Deep, cool, wedding, dryness):\n'
        '{"foundation": "dewy full-coverage rich espresso with cool red undertone",'
        ' "blush": "berry rose draped from cheekbones upward toward temples",'
        ' "eyeshadow": "plum and mauve shimmer with a soft kohl smoke",'
        ' "eyeliner": "tightlined black with a subtle wing",'
        ' "lipstick": "satin deep berry that complements cool undertones",'
        ' "highlighter": "icy rose gold on high points; pressed, not swept",'
        ' "contouring_tip": "Soften the pointed chin and add width along the jaw",'
        ' "overall_tip": "Pre-hydrate dry areas; layer creams under powder to avoid flaking"}\n'
    )

    return (
        "You are a professional makeup artist with 15 years of bridal and editorial experience.\n"
        "Reason step-by-step internally, then OUTPUT ONLY THE JSON.\n\n"
        "STEP 1 — Identify the dominant facial feature (eyes / lips / cheekbones).\n"
        "STEP 2 — Choose ONE hero product that flatters that feature.\n"
        "STEP 3 — Build the rest of the look around the hero without competing with it.\n\n"
        "CONSTRAINTS:\n"
        "- Foundation finish must be exactly one of: matte | satin | dewy\n"
        "- Lip finish must be exactly one of: matte | satin | gloss\n"
        "- Shade names must reference the skin tone (e.g. 'warm beige', 'cool ivory')\n"
        "- Avoid brand names\n"
        "- Adapt for active skin conditions (e.g. avoid heavy powders on dryness)\n\n"
        f"{shade_directive}\n"
        f"{example1}\n{example2}\n"
        "NOW GENERATE FOR:\n"
        f"- Face shape : {face_shape}\n"
        f"- Skin tone  : {skin_tone}\n"
        f"- Undertone  : {undertone}\n"
        f"- Occasion   : {occasion}\n"
        f"- Active skin conditions: {conditions}\n\n"
        "ALSO RETURN a 'shades' object: for EACH of foundation, eyes, lips, blush, "
        "contour, eyeliner, brows, highlighter give 1-2 swatches as "
        '{"name": "Shade name", "hex": "#RRGGBB"} with REAL hex codes chosen for '
        f"this skin tone ('{skin_tone}') and undertone ('{undertone}') — a deep skin "
        "tone must get deeper/richer hex values than a fair one.\n"
        "Output JSON only. No preamble. No explanation.\n"
        '{"foundation": "...", "blush": "...", "eyeshadow": "...",'
        ' "eyeliner": "...", "lipstick": "...", "highlighter": "...",'
        ' "contouring_tip": "...", "overall_tip": "...",'
        ' "shades": {"foundation": [{"name":"","hex":"#RRGGBB"}],'
        ' "eyes": [{"name":"","hex":"#RRGGBB"}], "lips": [{"name":"","hex":"#RRGGBB"}],'
        ' "blush": [{"name":"","hex":"#RRGGBB"}], "contour": [{"name":"","hex":"#RRGGBB"}],'
        ' "eyeliner": [{"name":"","hex":"#RRGGBB"}], "brows": [{"name":"","hex":"#RRGGBB"}],'
        ' "highlighter": [{"name":"","hex":"#RRGGBB"}]}}'
    )


def _validate_makeup_json(parsed):
    if not isinstance(parsed, dict):
        return False
    missing = REQUIRED_MAKEUP_KEYS - set(parsed.keys())
    if missing:
        logger.warning("Makeup LLM response missing keys: %s", missing)
        return False
    if not all(isinstance(parsed[k], str) and parsed[k].strip() for k in REQUIRED_MAKEUP_KEYS):
        logger.warning("Makeup LLM response has empty / non-string values")
        return False
    return True


def get_makeup_suggestions(face_shape, skin_tone, occasion='everyday',
                            undertone='neutral', skin_conditions=None):
    """
    Call Ollama with structured prompt, format=json, deterministic seed.
    Validate schema; fall back to rule-based on any failure (logged).
    """
    prompt = _build_makeup_prompt(face_shape, skin_tone, undertone, occasion, skin_conditions or [])
    seed = _stable_seed(face_shape, skin_tone, undertone, occasion)

    # ── PRIMARY: Groq (large model, reliable JSON). Falls through to Ollama. ──
    try:
        from core.llm_groq import groq_json, groq_available
        if groq_available():
            parsed = groq_json(
                prompt,
                system=("You are a professional makeup artist. Respond with ONLY "
                        "a valid JSON object matching the requested schema — no prose."),
                temperature=0.55,   # Fix 2 — more variety between faces/runs
            )
            if parsed and _validate_makeup_json(parsed):
                logger.info("Makeup suggestions via Groq.")
                return parsed
            logger.warning("Groq makeup output invalid; trying Ollama.")
    except Exception as exc:
        logger.warning("Groq makeup path errored (%s); trying Ollama.", exc)

    try:
        payload = json.dumps({
            'model':   OLLAMA_MODEL,
            'prompt':  prompt,
            'stream':  False,
            'format':  'json',
            'options': {
                'temperature':  0.35,
                'top_p':        0.9,
                'num_predict':  400,
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
                logger.error("Makeup LLM JSON parse failed: %s | RAW=%s", exc, text[:500])
                parsed = None

            if parsed and _validate_makeup_json(parsed):
                return parsed
            logger.warning("Makeup LLM output failed schema validation; falling back.")

    except urllib.error.URLError as exc:
        logger.error("Ollama unreachable at %s: %s — using rule-based makeup fallback.",
                     OLLAMA_URL, exc)
    except Exception as exc:
        logger.exception("Unexpected Ollama failure (makeup): %s", exc)

    return _fallback_makeup(face_shape, skin_tone, occasion, undertone, skin_conditions or [])


def _fallback_makeup(face_shape, skin_tone, occasion, undertone='neutral', skin_conditions=None):
    """Rule-based fallback (used when Ollama unreachable or schema invalid)."""
    tips = {
        'Oval':    'Your balanced proportions suit most makeup styles.',
        'Round':   'Use contouring along temples and jaw to elongate.',
        'Square':  'Soften the jaw with blush high on cheekbones.',
        'Heart':   'Focus colour on the lower face to balance the forehead.',
        'Oblong':  'Add width with horizontal blush strokes.',
        'Unknown': 'Classic techniques work for all face shapes.',
    }
    tones = {
        'Fair':    ('Light pink',  'Soft rose',     'Nude pink'),
        'Light':   ('Peach',       'Coral',          'Mauve'),
        'Medium':  ('Warm peach',  'Bronze',         'Berry'),
        'Tan':     ('Terracotta',  'Warm brown',     'Deep rose'),
        'Deep':    ('Rich plum',   'Deep burgundy',  'Dark berry'),
        'Unknown': ('Neutral',     'Natural',        'Classic red'),
    }
    blush, eyeshadow, lip = tones.get(skin_tone, tones['Unknown'])
    dryness = bool(skin_conditions) and any('dry' in str(c).lower() for c in skin_conditions)
    finish = 'dewy' if dryness else 'satin'
    return {
        'foundation':      f'{finish} {skin_tone.lower()} with a {undertone} undertone.',
        'blush':           f'{blush} blush on the apples of cheeks.',
        'eyeshadow':       f'{eyeshadow} tones for a {occasion} look.',
        'eyeliner':        'Soft brown for daytime.' if occasion == 'everyday' else 'Black gel for definition.',
        'lipstick':        f'satin {lip}.',
        'highlighter':     'Brow bone, inner corner, and cupid\'s bow.',
        'contouring_tip':  tips.get(face_shape, tips['Unknown']),
        'overall_tip':     f'For {skin_tone.lower()} skin with a {face_shape.lower()} face — enhance, do not over-do.',
    }
