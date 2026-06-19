"""
LLM-based recommendation engine — Ollama backend.

Uses a locally running Ollama instance (e.g. llama3, mistral, gemma2)
to generate structured, medically-aware skincare/scalp-care recommendations.

Fallback: if Ollama is unreachable, returns rule-based recommendations so
the pipeline never breaks.
"""

import json
import os
import re
import urllib.request
import urllib.error
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Safety rules baked into the prompt
# ---------------------------------------------------------------------------

SAFETY_RULES = """
STRICT SAFETY RULES (never violate these — they OVERRIDE every other instruction,
including the medicine recommendations):

GENERAL:
- ALWAYS cross-check EVERY recommended medicine AND product against the patient's
  medical flags, known allergens, and current medications below. If a medicine is
  contraindicated, DO NOT recommend it — silently pick a safe alternative instead.
- NEVER recommend a medicine that contains, or is cross-reactive with, any listed allergen.
- NEVER recommend a medicine that dangerously interacts with the patient's current medications.
- If you cannot find a safe medicine for a condition, return fewer medicines and add a
  safety_note telling the patient to see a doctor — do NOT recommend an unsafe one.

PREGNANCY / BREASTFEEDING — strictly AVOID and never recommend:
  retinoids (tretinoin, adapalene, isotretinoin, tazarotene), oral/ topical finasteride
  & dutasteride (handling risk), minoxidil, hydroquinone, salicylic acid >2%, high-dose
  benzoyl peroxide, oral tetracyclines (doxycycline/minocycline), griseofulvin, oral
  ketoconazole, chemical peels. Prefer pregnancy-safe options (e.g. azelaic acid,
  gentle emollients, topical erythromycin only if needed).

DIABETES: avoid potent prolonged topical steroids on large areas (impairs healing);
  prefer gentle antifungals/moisturisers; flag that steroids need doctor supervision.

CARDIOVASCULAR ISSUES / HYPERTENSION: avoid minoxidil (systemic absorption / tachycardia)
  and high-caffeine stimulating topicals; flag for doctor review.

ASTHMA: avoid fragranced/aerosol products and aspirin-family salicylates if aspirin-sensitive.

ALLERGIES: exclude every listed allergen and its known cross-reactors (e.g. neomycin,
  fragrance mix, formaldehyde-releasers, specific antibiotic classes).

SEVERITY: if any condition is Severe (score >= 70), make "consult a dermatologist" the
  first recommended step and keep self-medication conservative.
"""

SKIN_CONDITION_CONTEXT = {
    "acne": "bacterial/inflammatory skin condition; avoid pore-clogging ingredients, use non-comedogenic products",
    "dark_spots": "hyperpigmentation; brightening agents (niacinamide, vitamin C, azelaic acid) are helpful",
    "dryness": "compromised skin barrier; prioritise humectants (hyaluronic acid) and occlusives (ceramides, shea butter)",
    "normal": "no significant condition detected; focus on maintenance and sun protection",
}

SCALP_CONDITION_CONTEXT = {
    "dandruff": "Malassezia yeast overgrowth; antifungal ingredients (zinc pyrithione, ketoconazole, selenium sulphide) are first line",
    "hair_fall": "possible telogen effluvium or androgenic alopecia; strengthen with biotin, caffeine serums, minoxidil (after doctor check)",
    "oiliness": "sebum overproduction; use clarifying shampoos, avoid heavy oils on scalp",
    "dryness": "dry scalp / seborrheic dermatitis; use moisturising, fragrance-free shampoos and light scalp oils",
    "normal": "no significant condition detected; maintain regular gentle cleansing routine",
}


# ---------------------------------------------------------------------------
# Rule-based fallback (works offline, no LLM needed)
# ---------------------------------------------------------------------------

RULE_BASED: Dict[str, Dict] = {
    # SKIN
    "acne": {
        "daily_routine": {
            "morning": [
                "Wash face with a gentle, sulfate-free cleanser",
                "Apply niacinamide serum (5–10%)",
                "Use an oil-free, non-comedogenic moisturiser",
                "Apply broad-spectrum SPF 30+ sunscreen",
            ],
            "evening": [
                "Double-cleanse: micellar water then gentle cleanser",
                "Apply benzoyl peroxide spot treatment (2.5–5%) on active spots",
                "Use a lightweight, non-comedogenic moisturiser",
            ],
        },
        "weekly_routine": [
            "Exfoliate with a BHA (salicylic acid 1–2%) once or twice a week",
            "Apply a clay mask to absorb excess sebum",
        ],
        "products": [
            {"name": "CeraVe Foaming Facial Cleanser", "type": "cleanser", "reason": "Non-comedogenic, removes excess oil without stripping"},
            {"name": "Paula's Choice BHA 2% Exfoliant", "type": "exfoliant", "reason": "Unclogs pores, reduces blackheads"},
            {"name": "Neutrogena Hydro Boost (oil-free)", "type": "moisturiser", "reason": "Hydrates without clogging pores"},
            {"name": "La Roche-Posay Anthelios SPF 50", "type": "sunscreen", "reason": "Matte finish, non-comedogenic"},
        ],
        "dermatologist_consult": "Consult a dermatologist if acne is severe, cystic, or does not improve in 8–12 weeks of consistent care.",
    },
    "dark_spots": {
        "daily_routine": {
            "morning": [
                "Cleanse with a gentle brightening cleanser",
                "Apply Vitamin C serum (10–20%)",
                "Moisturise with a formula containing niacinamide",
                "Apply SPF 50+ sunscreen — critical to prevent spots darkening further",
            ],
            "evening": [
                "Cleanse thoroughly",
                "Apply azelaic acid (10–15%) or alpha-arbutin serum",
                "Moisturise with a ceramide-rich cream",
            ],
        },
        "weekly_routine": [
            "Use a gentle AHA (glycolic acid 5–7%) exfoliant once a week to accelerate cell turnover",
        ],
        "products": [
            {"name": "TruSkin Vitamin C Serum", "type": "serum", "reason": "Brightens and fades hyperpigmentation"},
            {"name": "The Ordinary Niacinamide 10% + Zinc 1%", "type": "serum", "reason": "Reduces pigmentation and pore appearance"},
            {"name": "Eucerin Anti-Pigment Cream", "type": "moisturiser", "reason": "Targets melanin production"},
        ],
        "dermatologist_consult": "See a dermatologist if spots are deeply pigmented, increasing in size, or new spots keep appearing.",
    },
    "dryness": {
        "daily_routine": {
            "morning": [
                "Cleanse with a creamy, hydrating cleanser",
                "Apply hyaluronic acid serum to damp skin",
                "Seal with a rich ceramide moisturiser",
                "Apply SPF 30+ (choose a moisturising formula)",
            ],
            "evening": [
                "Cleanse gently — avoid hot water",
                "Apply a hydrating essence or toner",
                "Apply a nourishing night cream or sleeping mask",
            ],
        },
        "weekly_routine": [
            "Use a gentle enzyme exfoliant (papain/bromelain) once a week to remove dry flakes",
            "Apply a hydrating sheet mask for 15–20 minutes",
        ],
        "products": [
            {"name": "Vanicream Gentle Facial Cleanser", "type": "cleanser", "reason": "Very gentle, fragrance-free, for dry/sensitive skin"},
            {"name": "The Ordinary Hyaluronic Acid 2% + B5", "type": "serum", "reason": "Deep hydration, plumps skin"},
            {"name": "CeraVe Moisturising Cream", "type": "moisturiser", "reason": "Ceramides restore skin barrier"},
        ],
        "dermatologist_consult": "Consult if dryness is severe, accompanied by redness, cracking, or does not respond to moisturising.",
    },
    # SCALP
    "dandruff": {
        "daily_routine": {
            "morning": [
                "Wet scalp thoroughly with lukewarm water",
                "Apply an antifungal shampoo (zinc pyrithione or ketoconazole 1%) — lather for 3–5 minutes before rinsing",
                "Follow with a lightweight, fragrance-free conditioner on ends only",
            ],
            "evening": [
                "If scalp is itchy, apply a few drops of tea tree oil diluted in jojoba oil (1:10 ratio) directly to scalp",
            ],
        },
        "weekly_routine": [
            "Use medicated shampoo 2–3 times per week; on other days use a gentle sulphate-free shampoo",
            "Once a week: apply diluted apple cider vinegar rinse (1:3 ACV:water) for 5 minutes to balance scalp pH",
        ],
        "products": [
            {"name": "Head & Shoulders Clinical Strength", "type": "shampoo", "reason": "Selenium sulphide targets Malassezia yeast"},
            {"name": "Nizoral Anti-Dandruff Shampoo (Ketoconazole 1%)", "type": "shampoo", "reason": "Antifungal, highly effective for persistent dandruff"},
            {"name": "Tea Tree Special Shampoo (Paul Mitchell)", "type": "shampoo", "reason": "Natural antifungal with tea tree oil"},
        ],
        "dermatologist_consult": "Consult a dermatologist if dandruff persists after 4 weeks of antifungal shampoo, or if scalp becomes red or inflamed.",
    },
    "hair_fall": {
        "daily_routine": {
            "morning": [
                "Gently massage scalp for 4–5 minutes with fingertips to stimulate blood flow",
                "Use a wide-tooth comb — avoid brushing wet hair aggressively",
                "Apply a lightweight scalp serum with biotin or peptides if available",
            ],
            "evening": [
                "Avoid tight hairstyles that pull at the roots",
                "Apply a few drops of rosemary oil diluted in carrier oil to scalp (studies show comparable efficacy to minoxidil for mild hair fall)",
            ],
        },
        "weekly_routine": [
            "Apply a deep conditioning hair mask to nourish follicles",
            "Wash with a strengthening shampoo containing biotin or caffeine",
        ],
        "products": [
            {"name": "Alpecin Caffeine Shampoo", "type": "shampoo", "reason": "Caffeine stimulates hair follicles, shown to reduce hair loss"},
            {"name": "Kérastase Genesis Anti-Hair Fall Serum", "type": "serum", "reason": "Strengthens roots and reduces breakage"},
            {"name": "Briogeo Scalp Revival Charcoal Shampoo", "type": "shampoo", "reason": "Unclogs follicles and removes build-up"},
        ],
        "dermatologist_consult": "Consult a dermatologist or trichologist if hair fall is sudden, excessive (>100 strands/day), or accompanied by bald patches.",
    },
    "oiliness": {
        "daily_routine": {
            "morning": [
                "Use a balancing, sulphate-free shampoo",
                "Avoid applying conditioner to scalp — apply to mid-lengths and ends only",
            ],
            "evening": [
                "If hair is not visibly oily, skip washing — over-washing triggers more sebum production",
                "Use a dry shampoo at roots if needed between washes",
            ],
        },
        "weekly_routine": [
            "Use a clarifying shampoo once a week to remove build-up",
            "Apply a light scalp toner with salicylic acid to control sebum",
        ],
        "products": [
            {"name": "Neutrogena T/Sal Therapeutic Shampoo", "type": "shampoo", "reason": "Salicylic acid removes excess oil and build-up"},
            {"name": "Batiste Dry Shampoo", "type": "dry shampoo", "reason": "Absorbs excess oil between washes"},
        ],
        "dermatologist_consult": "See a dermatologist if oiliness is extreme or accompanied by scalp acne or seborrheic dermatitis.",
    },
    "normal": {
        "daily_routine": {
            "morning": ["Cleanse gently", "Moisturise", "Apply SPF"],
            "evening": ["Cleanse", "Moisturise"],
        },
        "weekly_routine": ["Gentle exfoliation once a week", "Hydrating mask as needed"],
        "products": [],
        "dermatologist_consult": "No current concerns — annual skin check recommended.",
    },
}


# ---------------------------------------------------------------------------
# Ollama client helper
# ---------------------------------------------------------------------------

def _call_ollama(prompt: str, model: str, host: str, timeout: int) -> Optional[str]:
    """
    Call a locally running Ollama instance via its HTTP API.
    Returns the generated text or None on failure.
    """
    url = f"{host.rstrip('/')}/api/generate"
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "keep_alive": "5m",  # keep model loaded for 5 min -> fast subsequent calls
        "options": {
            "temperature": 0.3,   # low temperature = more consistent medical advice
            "num_predict": 1200,  # enough for full routine + products + notes
        }
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body.get("response", "").strip()
    except urllib.error.URLError as e:
        print(f"⚠️ Ollama unreachable at {host}: {e}")
        return None
    except Exception as e:
        print(f"⚠️ Ollama call failed: {e}")
        return None


def _extract_json(text: str) -> Optional[Dict]:
    """Extract first JSON object found in text."""
    if not text:
        return None
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try markdown code blocks
    for pattern in [r"```json\s*([\s\S]+?)```", r"```\s*([\s\S]+?)```"]:
        match = re.search(pattern, text)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass
    # Try finding raw { ... }
    match = re.search(r"\{[\s\S]+\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return None


# ---------------------------------------------------------------------------
# Deterministic medicine safety filter (belt-and-suspenders on top of the LLM)
# ---------------------------------------------------------------------------
# Drug name substrings that are contraindicated for a given condition flag.
# Matched case-insensitively against the medicine name + brand examples.
_CONTRAINDICATIONS = {
    "is_pregnant": [
        "tretinoin", "retinoin", "retinol", "adapalene", "tazarotene",
        "isotretinoin", "retinoid", "finasteride", "dutasteride", "minoxidil",
        "hydroquinone", "doxycycline", "minocycline", "tetracycline",
        "griseofulvin", "spironolactone", "tazorac",
    ],
    "has_cardio_issues": ["minoxidil"],
    "has_hypertension": ["minoxidil"],
}


def _filter_unsafe_medicines(medicines, medical_history):
    """Return (safe_medicines, removed_names). Drops medicines whose name/brand
    matches a contraindication for an active flag, or that contain a listed
    allergen. Conservative: only removes on a clear textual match."""
    if not isinstance(medicines, list) or not medical_history:
        return medicines, []

    # Active flag-based contraindicated substrings
    banned = set()
    for flag, drugs in _CONTRAINDICATIONS.items():
        if medical_history.get(flag):
            banned.update(drugs)

    # Allergen substrings (user-provided, comma-separated)
    allergens_raw = (medical_history.get("known_allergens") or "")
    allergens = [a.strip().lower() for a in allergens_raw.split(",")
                 if a.strip() and len(a.strip()) >= 3]

    safe, removed = [], []
    for med in medicines:
        if not isinstance(med, dict):
            continue
        hay = (str(med.get("name", "")) + " " +
               " ".join(med.get("brand_examples", []) or [])).lower()
        hit = next((b for b in banned if b in hay), None) \
            or next((a for a in allergens if a in hay), None)
        if hit:
            removed.append(med.get("name", hit))
        else:
            safe.append(med)
    return safe, removed


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class LLMRecommender:
    """
    Generates personalised skincare/scalp-care recommendations using
    a locally running Ollama model with rule-based fallback.
    """

    def __init__(
        self,
        model: str = None,
        host: str = None,
        timeout: int = 30,
        # legacy kwargs kept for compatibility — ignored
        model_path=None,
        api_key=None,
        use_api=False,
        model_name=None,
    ):
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.2")
        self.host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.timeout = timeout or 60  # 60s — enough for llama3.2 to generate full response
        self._ollama_available: Optional[bool] = None  # lazy check

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_care_routine(
        self,
        analysis_results: Dict,
        user_profile: Optional[Dict] = None,
        medical_history: Optional[Dict] = None,
    ) -> Dict:
        """
        Main entry point.  Returns structured recommendations dict.
        Falls back to rule-based recommendations if Ollama is unavailable.
        """
        user_profile = user_profile or {}
        medical_history = medical_history or {}

        # Check Ollama availability once per process lifetime
        if self._ollama_available is None:
            self._ollama_available = self._check_ollama()

        if self._ollama_available:
            result = self._generate_with_ollama(analysis_results, user_profile, medical_history)
            if result:
                return result
            # Ollama responded but gave unusable output — use fallback
            print("⚠️ Ollama gave unusable output — using rule-based fallback")

        return self._rule_based_fallback(analysis_results, medical_history)

    def generate_explanation(self, condition: str, detection_data: Dict) -> str:
        """Return a brief plain-language explanation of the detected condition."""
        confidence = detection_data.get("confidence", 0.0)
        condition_label = condition.replace("_", " ").title()

        if not self._ollama_available:
            return (
                f"{condition_label} was detected with {confidence:.0%} confidence. "
                "This is an AI-assisted finding — please consult a dermatologist for confirmation."
            )

        prompt = (
            f"In 2–3 plain, friendly sentences explain what '{condition_label}' is "
            f"and what it means for someone who just had it detected with {confidence:.0%} AI confidence. "
            "Do NOT use medical jargon. Do NOT give treatment advice here."
        )
        response = _call_ollama(prompt, self.model, self.host, timeout=30)
        if response:
            return response.strip()
        return (
            f"{condition_label} was detected with {confidence:.0%} confidence. "
            "Please consult a dermatologist for a proper diagnosis."
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _check_ollama(self) -> bool:
        """Ping Ollama health endpoint. Returns quickly (2s timeout)."""
        try:
            url = f"{self.host.rstrip('/')}/api/tags"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=2):
                print(f"✅ Ollama is running at {self.host} (model: {self.model})")
                return True
        except Exception:
            print(f"⚠️ Ollama not reachable at {self.host} — using rule-based fallback")
            return False

    def _build_prompt(
        self,
        analysis_results: Dict,
        user_profile: Dict,
        medical_history: Dict,
    ) -> str:
        """Build a structured clinical prompt."""

        # --- patient info ---
        age = user_profile.get("age", "unknown")
        gender = user_profile.get("gender", "unknown")
        skin_type = user_profile.get("skin_type", "unknown")
        hair_type = user_profile.get("hair_type", "unknown")

        # --- medical flags ---
        is_pregnant = medical_history.get("is_pregnant", False)
        is_diabetic = medical_history.get("is_diabetic", False)
        has_cardio = medical_history.get("has_cardio_issues", False)
        has_asthma = medical_history.get("has_asthma", False)
        has_hypertension = medical_history.get("has_hypertension", False)
        allergies_raw = medical_history.get("known_allergens", "") or ""
        allergies = [a.strip() for a in allergies_raw.split(",") if a.strip()]
        medications = medical_history.get("current_medications", "") or "none"
        other_conditions = medical_history.get("other_conditions", "") or "none"

        active_flags = []
        if is_pregnant:       active_flags.append("PREGNANT")
        if is_diabetic:       active_flags.append("DIABETIC")
        if has_cardio:        active_flags.append("CARDIOVASCULAR ISSUES")
        if has_asthma:        active_flags.append("ASTHMA")
        if has_hypertension:  active_flags.append("HYPERTENSION")

        # --- detected conditions ---
        analysis_type = analysis_results.get("analysis_type", "skin")
        conditions = analysis_results.get("detected_conditions", [])
        severity_scores = analysis_results.get("severity_scores", {})

        condition_lines = []
        for cond in conditions:
            name = cond.get("name", "unknown")
            confidence = cond.get("confidence", 0.0)
            sev = severity_scores.get(name, {})
            level = sev.get("level", "Mild")
            score = sev.get("score", int(confidence * 100))

            ctx_map = SKIN_CONDITION_CONTEXT if analysis_type == "skin" else SCALP_CONDITION_CONTEXT
            context_note = ctx_map.get(name, "")
            condition_lines.append(
                f"  - {name.replace('_', ' ').title()}: {level} severity (score {score}/100). Context: {context_note}"
            )

        conditions_text = "\n".join(condition_lines) if condition_lines else "  - No significant condition detected (normal)"

        # --- build prompt ---
        prompt = f"""You are a clinical dermatology AI assistant. Generate personalised, evidence-based skincare/scalp-care recommendations.

{SAFETY_RULES}

=== PATIENT PROFILE ===
Age: {age}
Gender: {gender}
Skin type: {skin_type}
Hair type: {hair_type}
Analysis type: {analysis_type}

=== DETECTED CONDITIONS ===
{conditions_text}

=== MEDICAL FLAGS (critical — apply safety rules above) ===
Active flags: {', '.join(active_flags) if active_flags else 'None'}
Known allergens: {', '.join(allergies) if allergies else 'None'}
Current medications: {medications}
Other conditions: {other_conditions}

=== TASK ===
Provide personalised, evidence-based recommendations tailored to the detected conditions, severity, and medical history.

For "medicines": recommend 3-5 ACTUAL pharmaceutical medicines specifically INDICATED for the
detected condition — use real generic drug names with example brand names, the dosage form and
strength. Include both over-the-counter (otc:true) and, where it is the medical standard, common
prescription options (otc:false). For prescription medicines, set otc:false and tell the patient to
consult a doctor — do NOT give exact personal dosing for prescription drugs. Examples of the level of
specificity required:
  • Scalp Psoriasis → Coal tar shampoo (Neutrogena T/Gel), Calcipotriol 0.005% (Dovonex), Clobetasol 0.05% (Temovate, Rx)
  • Seborrheic Dermatitis → Ketoconazole 2% shampoo (Nizoral), Zinc pyrithione (Head & Shoulders), Ciclopirox 1% (Rx)
  • Scalp Infection / Tinea / Folliculitis → Terbinafine (Lamisil), Griseofulvin (Rx), Mupirocin 2% (Bactroban, Rx)
  • Alopecia → Minoxidil 5% (Rogaine), Finasteride 1mg (Propecia, Rx)
  • Acne → Benzoyl peroxide 2.5-5% (Benzac), Adapalene 0.1% (Differin), Clindamycin (Rx)
  • Dryness/Dermatitis → Hydrocortisone 1% (Cortizone-10), Cetaphil/CeraVe moisturiser, Tacrolimus (Rx)
Pick the medicines that match the ACTUAL detected condition above — do not list unrelated drugs.

CRITICAL — PERSONALISE TO THIS PATIENT'S MEDICAL HISTORY: Before finalising the medicines
list, re-read the MEDICAL FLAGS, Known allergens, and Current medications below and apply
the STRICT SAFETY RULES. Remove ANY medicine that is contraindicated for this specific
patient (pregnancy, allergy, drug interaction, diabetes, cardiovascular/hypertension,
asthma) and replace it with a safe alternative. Each medicine you DO list must be safe for
THIS patient. Add a short "safe_for_patient" note on each medicine explaining why it is
appropriate given their history (e.g. "pregnancy-safe", "no interaction with current meds",
"allergen-free").
IMPORTANT: Return ONLY valid JSON — no markdown, no explanation outside the JSON.

Required JSON structure:
{{
  "daily_routine": {{
    "morning": ["step 1", "step 2", "..."],
    "evening": ["step 1", "step 2", "..."]
  }},
  "weekly_routine": ["suggestion 1", "suggestion 2"],
  "medicines": [
    {{"name": "generic drug name", "brand_examples": ["BrandA", "BrandB"], "form": "tablet|capsule|topical cream|ointment|medicated shampoo|solution|lotion", "strength": "e.g. 2%, 5mg, 0.1%", "usage": "how and when to apply/take it", "reason": "why this medicine treats the detected condition", "safe_for_patient": "why it is safe given this patient's medical history", "otc": true}}
  ],
  "products": [
    {{"name": "product name", "type": "cleanser|moisturiser|serum|shampoo|etc", "reason": "why this product suits this patient"}}
  ],
  "dermatologist_consult": "clear guidance on when/whether to see a dermatologist",
  "safety_notes": ["any ingredient, medicine or practice the patient must avoid given their medical flags"]
}}
"""
        return prompt

    def _generate_with_ollama(
        self,
        analysis_results: Dict,
        user_profile: Dict,
        medical_history: Dict,
    ) -> Optional[Dict]:
        """Generate the care routine. Tries Groq first (large model, reliable
        JSON), then falls back to the local Ollama model."""
        prompt = self._build_prompt(analysis_results, user_profile, medical_history)

        # ── PRIMARY: Groq ──
        parsed = None
        try:
            from core.llm_groq import groq_json, groq_available
            if groq_available():
                parsed = groq_json(
                    prompt,
                    system=("You are a careful dermatology/trichology assistant. "
                            "Respond with ONLY a valid JSON object — no prose. "
                            "You MAY name real pharmaceutical medicines (generic + brand) "
                            "that are standard treatment for the detected condition. For "
                            "prescription-only medicines, set otc:false and advise consulting "
                            "a doctor — never give exact personal dosing for prescription drugs. "
                            "PATIENT SAFETY IS THE TOP PRIORITY: every medicine you list MUST be "
                            "safe for THIS patient's medical history (pregnancy, allergies, current "
                            "medications, diabetes, cardiovascular/hypertension, asthma). Never "
                            "recommend a contraindicated or allergen-containing medicine — choose a "
                            "safe alternative instead."),
                    temperature=0.3,
                )
                if parsed and isinstance(parsed, dict):
                    print("✅ Skin/scalp recommendations via Groq.")
        except Exception as exc:
            print(f"⚠️ Groq recommender path errored ({exc}); trying Ollama.")
            parsed = None

        # ── FALLBACK: Ollama ──
        if not (parsed and isinstance(parsed, dict)):
            raw = _call_ollama(prompt, self.model, self.host, self.timeout)
            if not raw:
                return None
            parsed = _extract_json(raw)
        if parsed and isinstance(parsed, dict):
            # Ensure all expected keys exist
            parsed.setdefault("daily_routine", {"morning": [], "evening": []})
            parsed.setdefault("weekly_routine", [])
            parsed.setdefault("medicines", [])
            parsed.setdefault("products", [])
            parsed.setdefault("dermatologist_consult", "Consult a dermatologist if condition worsens.")
            parsed.setdefault("safety_notes", [])
            # ── Deterministic safety net — drop any contraindicated medicine the
            # LLM may have slipped through, regardless of what it returned. ──
            parsed["medicines"], removed = _filter_unsafe_medicines(
                parsed.get("medicines", []), medical_history)
            if removed:
                note = ("Some medicines were withheld because they may be unsafe "
                        "given your medical history — please consult a doctor.")
                if note not in parsed["safety_notes"]:
                    parsed["safety_notes"].append(note)
                print(f"🛡️ Safety filter removed {len(removed)} contraindicated medicine(s): {removed}")
            return parsed

        print(f"⚠️ Could not parse Ollama JSON output: {raw[:300]}")
        return None

    def _rule_based_fallback(
        self,
        analysis_results: Dict,
        medical_history: Dict,
    ) -> Dict:
        """
        Return rule-based recommendations when Ollama is unavailable.
        Merges advice for all detected conditions and applies safety filters.
        """
        conditions = analysis_results.get("detected_conditions", [])
        severity_scores = analysis_results.get("severity_scores", {})

        # Pick primary condition (highest severity score, non-normal)
        primary = None
        highest = -1
        for cond in conditions:
            name = cond.get("name", "normal")
            score = severity_scores.get(name, {}).get("score", 0)
            if name != "normal" and score > highest:
                highest = score
                primary = name

        if primary is None and conditions:
            primary = conditions[0].get("name", "normal")
        primary = primary or "normal"

        base = RULE_BASED.get(primary, RULE_BASED["normal"])
        result = {
            "daily_routine": base["daily_routine"],
            "weekly_routine": base["weekly_routine"],
            "medicines": list(base.get("medicines", [])),
            "products": list(base["products"]),
            "dermatologist_consult": base["dermatologist_consult"],
            "safety_notes": [],
        }

        # Apply safety filters
        is_pregnant = medical_history.get("is_pregnant", False)
        allergies_raw = medical_history.get("known_allergens", "") or ""
        allergies = [a.strip().lower() for a in allergies_raw.split(",") if a.strip()]

        if is_pregnant:
            result["safety_notes"].append(
                "Pregnancy: avoid retinoids, salicylic acid >2%, benzoyl peroxide, and hydroquinone."
            )
            # Filter out unsafe products from recommendations
            safe_products = []
            unsafe_keywords = ["salicylic", "retinol", "tretinoin", "benzoyl", "hydroquinone", "adapalene"]
            for product in result["products"]:
                reason_lower = product.get("reason", "").lower() + product.get("name", "").lower()
                if not any(kw in reason_lower for kw in unsafe_keywords):
                    safe_products.append(product)
            result["products"] = safe_products

        if allergies:
            result["safety_notes"].append(f"Known allergens to avoid: {', '.join(allergies)}.")

        if medical_history.get("is_diabetic"):
            result["safety_notes"].append(
                "Diabetes: prefer gentle, alcohol-free formulations; monitor skin for slow-healing reactions."
            )

        # Max severity → push dermatologist consult
        max_score = max(
            (v.get("score", 0) for v in severity_scores.values()),
            default=0
        )
        if max_score >= 70:
            result["dermatologist_consult"] = (
                "⚠️ Severity is HIGH. Please consult a dermatologist promptly before starting any new treatment."
            )

        return result
