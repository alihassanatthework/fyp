"""
makeup/services.py
──────────────────
Face shape detection (MediaPipe landmarks + geometry)
Skin tone detection  (OpenCV color sampling)
Makeup suggestions   (Ollama LLM)
"""
import math
import logging
import numpy as np
import cv2
import urllib.request
import json

logger = logging.getLogger(__name__)


# ── Face Shape Detection ──────────────────────────────────────────────────────

def detect_face_shape(image_path: str) -> str:
    """
    Uses MediaPipe FaceMesh landmarks to classify face shape.
    Returns one of: Oval, Round, Square, Heart, Oblong, Unknown
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
            return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2)

        # Key measurements using standard FaceMesh indices
        forehead_w  = dist(pt(54),  pt(284))   # across forehead
        cheekbone_w = dist(pt(234), pt(454))   # across cheekbones (widest)
        jaw_w       = dist(pt(172), pt(397))   # across jaw
        face_h      = dist(pt(10),  pt(152))   # top of head to chin

        ratio_h_w    = face_h / cheekbone_w if cheekbone_w else 1
        jaw_to_cheek = jaw_w / cheekbone_w   if cheekbone_w else 1
        fore_to_jaw  = forehead_w / jaw_w    if jaw_w else 1

        # Classification rules
        if ratio_h_w > 1.5:
            return 'Oblong'
        elif jaw_to_cheek > 0.9 and fore_to_jaw < 1.1:
            return 'Square'
        elif fore_to_jaw > 1.2:
            return 'Heart'
        elif ratio_h_w < 1.1 and jaw_to_cheek > 0.85:
            return 'Round'
        else:
            return 'Oval'

    except Exception as exc:
        logger.warning("Face shape detection failed: %s", exc)
        return 'Unknown'


# ── Skin Tone Detection ───────────────────────────────────────────────────────

def detect_skin_tone(image_path: str) -> str:
    """
    Sample skin tone from the cheek area using OpenCV.
    Returns: Fair, Light, Medium, Tan, Deep
    """
    try:
        import mediapipe as mp

        img = cv2.imread(image_path)
        if img is None:
            return 'Unknown'

        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w = img.shape[:2]

        mp_face = mp.solutions.face_mesh
        with mp_face.FaceMesh(static_image_mode=True, max_num_faces=1) as fm:
            results = fm.process(rgb)

        if not results.multi_face_landmarks:
            return 'Unknown'

        lm = results.multi_face_landmarks[0].landmark

        # Sample left cheek landmark (index 234 area)
        cx = int(lm[234].x * w)
        cy = int(lm[234].y * h)

        # Average a 20x20 patch
        patch = img[max(0, cy-10):cy+10, max(0, cx-10):cx+10]
        if patch.size == 0:
            return 'Unknown'

        mean_bgr = patch.mean(axis=(0, 1))
        # Convert to Lab for better skin tone comparison
        pixel = np.uint8([[mean_bgr]])
        lab   = cv2.cvtColor(pixel, cv2.COLOR_BGR2Lab)[0][0]
        L     = lab[0]  # 0=dark, 255=light

        if L > 200:
            return 'Fair'
        elif L > 170:
            return 'Light'
        elif L > 140:
            return 'Medium'
        elif L > 110:
            return 'Tan'
        else:
            return 'Deep'

    except Exception as exc:
        logger.warning("Skin tone detection failed: %s", exc)
        return 'Unknown'


# ── Ollama LLM Suggestions ────────────────────────────────────────────────────

def get_makeup_suggestions(face_shape: str, skin_tone: str, occasion: str = 'everyday') -> dict:
    """
    Call Ollama (local LLM) to generate makeup suggestions.
    Falls back to rule-based suggestions if Ollama is not running.
    """
    prompt = (
        f"You are a professional makeup artist. Give concise makeup suggestions for:\n"
        f"- Face shape: {face_shape}\n"
        f"- Skin tone: {skin_tone}\n"
        f"- Occasion: {occasion}\n\n"
        f"Provide recommendations in this exact JSON format:\n"
        f'{{"foundation": "...", "blush": "...", "eyeshadow": "...", '
        f'"eyeliner": "...", "lipstick": "...", "highlighter": "...", '
        f'"contouring_tip": "...", "overall_tip": "..."}}\n'
        f"Only respond with the JSON, no extra text."
    )

    try:
        payload = json.dumps({
            "model": "llama3.2",
            "prompt": prompt,
            "stream": False,
        }).encode()

        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            text   = result.get("response", "").strip()
            # Extract JSON from response
            start = text.find('{')
            end   = text.rfind('}') + 1
            if start != -1 and end > start:
                return json.loads(text[start:end])

    except Exception as exc:
        logger.warning("Ollama not available, using fallback suggestions: %s", exc)

    # Rule-based fallback when Ollama is not running
    return _fallback_makeup(face_shape, skin_tone, occasion)


def _fallback_makeup(face_shape: str, skin_tone: str, occasion: str) -> dict:
    """Rule-based makeup suggestions as fallback."""
    tips = {
        'Oval':    'Your balanced proportions suit most makeup styles.',
        'Round':   'Use contouring along temples and jaw to elongate.',
        'Square':  'Soften the jaw with blush high on cheekbones.',
        'Heart':   'Focus colour on the lower face to balance the forehead.',
        'Oblong':  'Add width with horizontal blush strokes.',
        'Unknown': 'Classic techniques work for all face shapes.',
    }
    tones = {
        'Fair':    ('Light pink', 'Soft rose',    'Nude pink'),
        'Light':   ('Peach',      'Coral',         'Mauve'),
        'Medium':  ('Warm peach', 'Bronze',        'Berry'),
        'Tan':     ('Terracotta', 'Warm brown',    'Deep rose'),
        'Deep':    ('Rich plum',  'Deep burgundy', 'Dark berry'),
        'Unknown': ('Neutral',    'Natural',       'Classic red'),
    }
    blush, eyeshadow, lip = tones.get(skin_tone, tones['Unknown'])
    return {
        'foundation':      f'Match your {skin_tone.lower()} skin tone with a dewy finish.',
        'blush':           f'{blush} blush on the apples of cheeks.',
        'eyeshadow':       f'{eyeshadow} tones for a {occasion} look.',
        'eyeliner':        'Brown eyeliner for a softer daytime look.' if occasion == 'everyday' else 'Black gel liner for definition.',
        'lipstick':        f'{lip} lipstick suits your skin tone beautifully.',
        'highlighter':     'Apply to brow bone, inner corner, and cupid\'s bow.',
        'contouring_tip':  tips.get(face_shape, tips['Unknown']),
        'overall_tip':     f'For {skin_tone.lower()} skin with a {face_shape.lower()} face, less is more — enhance your natural features.',
    }
