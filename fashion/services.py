"""
fashion/services.py
───────────────────
Body type detection  (MediaPipe Pose landmarks)
Skin tone detection  (reuse from makeup.services)
Fashion suggestions  (Ollama LLM with rule-based fallback)
"""
import math
import logging
import json
import urllib.request

logger = logging.getLogger(__name__)


# ── Body Type Detection ───────────────────────────────────────────────────────

def detect_body_type(image_path: str) -> str:
    """
    Uses MediaPipe Pose to estimate body proportions.
    Returns: Hourglass, Pear, Apple, Rectangle, Inverted Triangle, Unknown
    """
    try:
        import mediapipe as mp
        import cv2

        img = cv2.imread(image_path)
        if img is None:
            return 'Unknown'

        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w = img.shape[:2]

        mp_pose = mp.solutions.pose
        with mp_pose.Pose(static_image_mode=True, model_complexity=1) as pose:
            results = pose.process(rgb)

        if not results.pose_landmarks:
            return 'Unknown'

        lm = results.pose_landmarks.landmark

        def pt(idx):
            return lm[idx].x * w, lm[idx].y * h

        def dist(a, b):
            return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2)

        # Shoulder width: left shoulder (11) to right shoulder (12)
        shoulder_w = dist(pt(11), pt(12))
        # Hip width: left hip (23) to right hip (24)
        hip_w      = dist(pt(23), pt(24))
        # Waist approximation: midpoint between shoulders and hips
        waist_w    = (shoulder_w + hip_w) / 2 * 0.75

        s_h_ratio  = shoulder_w / hip_w if hip_w else 1
        w_s_ratio  = waist_w / shoulder_w if shoulder_w else 1

        if w_s_ratio < 0.75:
            if abs(s_h_ratio - 1) < 0.15:
                return 'Hourglass'
            elif s_h_ratio < 0.85:
                return 'Pear'
            elif s_h_ratio > 1.15:
                return 'Inverted Triangle'
        if w_s_ratio > 0.85:
            return 'Apple'
        return 'Rectangle'

    except Exception as exc:
        logger.warning("Body type detection failed: %s", exc)
        return 'Unknown'


# ── Ollama Fashion Suggestions ────────────────────────────────────────────────

def get_fashion_suggestions(body_type: str, skin_tone: str, event_type: str) -> dict:
    """
    Call Ollama for outfit suggestions.
    Falls back to rule-based suggestions if Ollama is not running.
    """
    prompt = (
        f"You are a professional fashion stylist. Suggest an outfit for:\n"
        f"- Body type : {body_type}\n"
        f"- Skin tone : {skin_tone}\n"
        f"- Event     : {event_type}\n\n"
        f"Respond in this exact JSON format:\n"
        f'{{"outfit": "...", "colors": "...", "avoid": "...", '
        f'"accessories": "...", "shoes": "...", "styling_tip": "..."}}\n'
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
            start  = text.find('{')
            end    = text.rfind('}') + 1
            if start != -1 and end > start:
                return json.loads(text[start:end])

    except Exception as exc:
        logger.warning("Ollama not available, using fallback suggestions: %s", exc)

    return _fallback_fashion(body_type, skin_tone, event_type)


def _fallback_fashion(body_type: str, skin_tone: str, event_type: str) -> dict:
    """Rule-based fashion suggestions as fallback."""
    outfits = {
        ('Hourglass',          'casual'):   'Fitted jeans with a tucked-in blouse',
        ('Hourglass',          'formal'):   'Wrap dress or tailored blazer with trousers',
        ('Pear',               'casual'):   'A-line skirt with a fitted top',
        ('Pear',               'formal'):   'Dark trousers with a statement top',
        ('Apple',              'casual'):   'Empire waist top with straight-leg pants',
        ('Apple',              'formal'):   'Structured blazer with wide-leg trousers',
        ('Rectangle',          'casual'):   'Ruffled top with skinny jeans',
        ('Rectangle',          'formal'):   'Peplum top with pencil skirt',
        ('Inverted Triangle',  'casual'):   'Flared trousers with a simple top',
        ('Inverted Triangle',  'formal'):   'A-line skirt with a fitted blouse',
    }

    colors = {
        'Fair':   'Pastels, soft blues, blush pink',
        'Light':  'Coral, peach, warm whites',
        'Medium': 'Earthy tones, olive, mustard',
        'Tan':    'Burnt orange, teal, warm reds',
        'Deep':   'Bold jewel tones, white, gold',
        'Unknown':'Neutrals and classic tones',
    }

    outfit = outfits.get((body_type, event_type),
             outfits.get((body_type, 'casual'),
             'Classic well-fitted outfit in neutral tones'))

    return {
        'outfit':      outfit,
        'colors':      colors.get(skin_tone, colors['Unknown']),
        'avoid':       f'Avoid overly boxy cuts that hide your {body_type.lower()} shape.',
        'accessories': 'Belt to define the waist, simple jewellery.' if event_type == 'formal' else 'Minimal accessories for a clean look.',
        'shoes':       'Heels or block heels' if event_type in ('formal', 'wedding', 'party') else 'Sneakers or loafers',
        'styling_tip': f'For a {body_type.lower()} body type at a {event_type} event, focus on balance and proportion.',
    }
