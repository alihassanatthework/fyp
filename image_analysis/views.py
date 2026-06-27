from matplotlib.style import context
from datetime import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from image_analysis.models import AnalysisResult
from django.conf import settings
import logging
import os
import uuid
import hashlib
from threading import Lock
from time import time
import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Import your AI Logic
from core.ai_models.mediapipe_detector import FaceScalpDetector
from core.ai_models import process_image
import numpy as np

# Module logger. Configured via LOGGING in config/settings.py — emits at
# DEBUG when settings.DEBUG is True, INFO otherwise. Replaces scattered
# print() calls so verbosity can be tuned centrally and suppressed in prod.
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helper: extract user_profile and medical_history from request user (if logged in)
# ---------------------------------------------------------------------------

def _get_user_context(request) -> tuple:
    """
    Returns (user_profile_dict, medical_history_dict).
    Both dicts are empty if the user is not authenticated or has no saved data.
    """
    user_profile = {}
    medical_history = {}

    if not request.user or not request.user.is_authenticated:
        return user_profile, medical_history

    try:
        profile = request.user.profile
        user_profile = {
            "age": profile.age,
            "gender": profile.gender,
            "skin_type": profile.skin_type,
            "hair_type": profile.hair_type,
        }
    except Exception:
        pass

    try:
        mh = request.user.medical_history
        medical_history = {
            "is_pregnant": mh.is_pregnant,
            "is_diabetic": mh.is_diabetic,
            "has_cardio_issues": mh.has_cardio_issues,
            "has_asthma": mh.has_asthma,
            "has_hypertension": mh.has_hypertension,
            "has_allergies": mh.has_allergies,
            "known_allergens": mh.known_allergens or "",
            "current_medications": mh.current_medications or "",
            "other_conditions": mh.other_conditions or "",
        }
    except Exception:
        pass

    return user_profile, medical_history


def _format_recommendations_for_template(recommendations: dict) -> list:
    """
    Convert structured LLM recommendations dict into a flat list of
    human-readable strings for the HTML template.
    """
    lines = []

    morning = recommendations.get("daily_routine", {}).get("morning", [])
    evening = recommendations.get("daily_routine", {}).get("evening", [])
    weekly = recommendations.get("weekly_routine", [])
    products = recommendations.get("products", [])
    consult = recommendations.get("dermatologist_consult", "")
    safety = recommendations.get("safety_notes", [])

    if morning:
        lines.append("🌅 Morning Routine:")
        lines.extend([f"  • {s}" for s in morning])

    if evening:
        lines.append("🌙 Evening Routine:")
        lines.extend([f"  • {s}" for s in evening])

    if weekly:
        lines.append("📅 Weekly Care:")
        lines.extend([f"  • {s}" for s in weekly])

    if products:
        lines.append("🛍️ Recommended Products:")
        for p in products:
            name = p.get("name", "")
            reason = p.get("reason", "")
            lines.append(f"  • {name} — {reason}" if reason else f"  • {name}")

    if safety:
        lines.append("⚠️ Safety Notes:")
        lines.extend([f"  • {s}" for s in safety])

    if consult:
        lines.append(f"👨‍⚕️ {consult}")

    return lines

# Global in-memory cache for idempotency.
# Keyed by "<sha256>:<image_type>".
# This avoids double-upload issues even if React sends requests with different session cookies.
GLOBAL_ANALYSIS_CACHE_LOCK = Lock()
GLOBAL_ANALYSIS_CACHE = {}  # key -> {"ts": float, "context": dict}
GLOBAL_ANALYSIS_INFLIGHT = {}  # key -> {"event": threading.Event, "ts": float}
GLOBAL_CACHE_TTL_SECONDS = 5 * 60  # 5 minutes
GLOBAL_CACHE_MAX_ITEMS = 50
GLOBAL_INFLIGHT_TTL_SECONDS = 90  # wait up to 90s for the first request


def _clear_inflight(cache_key):
    """
    Clear the inflight marker for a cache key so other waiting requests
    can proceed instead of hanging. Safe to call multiple times.
    """
    if not cache_key:
        return
    try:
        with GLOBAL_ANALYSIS_CACHE_LOCK:
            inflight = GLOBAL_ANALYSIS_INFLIGHT.pop(cache_key, None)
            if inflight and inflight.get("event"):
                try:
                    inflight["event"].set()
                except Exception:
                    pass
    except Exception:
        pass

class AnalyzeImageView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        """
        Handles image upload + AI pipeline. Rate-limited to 10 requests/hour per user.
        """
        # Rate limit: 10 uploads per hour per authenticated user (only when Redis is available)
        if getattr(settings, 'RATELIMIT_ENABLE', False):
            from django_ratelimit.core import is_ratelimited
            limited = is_ratelimited(
                request,
                group='analysis_upload',
                key='user',
                rate='10/h',
                increment=True,
            )
            if limited:
                return Response(
                    {"success": False, "error": "Too many analysis requests. You can run up to 10 analyses per hour. Please try again later."},
                    status=429,
                )

        file_obj = request.FILES.get('image')
        
        if not file_obj:
            return Response(
                {"success": False, "error": "No image provided. Please select a file."},
                status=400
            )

        # Server-side content-type validation — reject non-image uploads
        # before any expensive AI processing starts.
        ALLOWED_CONTENT_TYPES = {'image/jpeg', 'image/png', 'image/heic', 'image/heif'}
        content_type = getattr(file_obj, 'content_type', '') or ''
        if content_type not in ALLOWED_CONTENT_TYPES:
            return Response(
                {"success": False, "error": f"Unsupported file type '{content_type}'. Please upload a JPEG or PNG image."},
                status=400
            )

        # Enforce server-side size limit (10 MB)
        MAX_UPLOAD_BYTES = 10 * 1024 * 1024
        if file_obj.size > MAX_UPLOAD_BYTES:
            return Response(
                {"success": False, "error": "File too large. Maximum allowed size is 10 MB."},
                status=400
            )

        # ── Daily scan limit (Free tier) ──────────────────────────────
        # Free accounts: capped per calendar day. Premium: unlimited.
        from .models import scan_quota
        quota = scan_quota(request.user)
        if not quota['is_premium'] and quota['remaining'] <= 0:
            return Response(
                {
                    "success": False,
                    "error": (
                        f"Daily scan limit reached ({quota['limit']}/{quota['limit']}). "
                        "Free accounts can run "
                        f"{quota['limit']} scans per day — your limit resets at midnight. "
                        "Upgrade to Premium for unlimited scans."
                    ),
                    "limit_reached": True,
                    "scan_quota": quota,
                },
                status=429,
            )

        # React requests JSON; legacy flow renders HTML.
        accept = ""
        try:
            accept = request.headers.get("Accept", "") or ""
        except Exception:
            accept = request.META.get("HTTP_ACCEPT", "") or ""
        wants_json = ("application/json" in accept) or (getattr(request, "query_params", {}).get("format") == "json")

        # 1. Setup Folder Paths
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
        processed_dir = os.path.join(settings.MEDIA_ROOT, 'processed')
        os.makedirs(upload_dir, exist_ok=True)
        os.makedirs(processed_dir, exist_ok=True)

        # 2. Save Original File with Unique Name
        unique_name = f"{uuid.uuid4().hex[:8]}_{file_obj.name}"
        file_path = os.path.join(upload_dir, unique_name)
        
        with open(file_path, 'wb+') as destination:
            for chunk in file_obj.chunks():
                destination.write(chunk)

        logger.debug("Image saved to: %s", file_path)

        # 3. Run AI Detector (MediaPipe / fallback rules)
        detector = FaceScalpDetector()
        logger.debug("Starting FaceScalpDetector...")

        # Determine requested analysis type (default to skin)
        # React frontend sends `analysis_type`, while legacy/templates may send `image_type`.
        image_type = (
            request.data.get('image_type')
            or request.data.get('analysis_type')
            or request.POST.get('image_type')
            or request.POST.get('analysis_type')
            or 'skin'
        )
        logger.info("Image type received: %s", image_type)

        # -----------------------------
        # Idempotency cache — DISABLED during AI/model rebuild phase
        # -----------------------------
        # The cache used to short-circuit identical uploads to avoid running
        # the heavy AI pipeline twice. But while we are actively iterating on
        # the model (binary normal detector, mask logic, retraining), the
        # cache returns stale results from before the change. We compute a
        # cache_key so the in-flight signalling at the end of the view still
        # works, but we never return from cache. The double-upload protection
        # is already handled on the React side by the Axios interceptor.
        session_cache = {}
        cache_limit = 20
        cache_key = None
        try:
            sha = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    sha.update(chunk)
            file_hash = sha.hexdigest()
            cache_key = f"{file_hash}:{image_type}"
            logger.debug("[cache] DISABLED — bypassing for key %s", cache_key)
            # Clear any stale entry for this key so old results don't linger.
            with GLOBAL_ANALYSIS_CACHE_LOCK:
                GLOBAL_ANALYSIS_CACHE.pop(cache_key, None)
        except Exception:
            cache_key = None

        face_path = None
        scalp_path = None
        face_crop = None
        scalp_crop = None

        # Load image — handle HEIC/HEIF natively since cv2.imread cannot read them.
        _file_lower = file_path.lower()
        if _file_lower.endswith(('.heic', '.heif')):
            try:
                import pillow_heif
                _heif = pillow_heif.read_heif(file_path)
                img = cv2.cvtColor(np.array(_heif[0]), cv2.COLOR_RGB2BGR)
            except Exception as _he:
                logger.warning("HEIC decode failed: %s", _he)
                img = None
        else:
            img = cv2.imread(file_path)

        if img is None:
            _clear_inflight(cache_key)
            return Response(
                {"success": False, "error": "Could not read uploaded image."},
                status=400
            )

        if image_type == 'skin':
            # DISABLED: strict face detection requirement
            # The previous logic REQUIRED MediaPipe to detect a human face and
            # rejected everything else, which blocked legitimate body-skin photos
            # (arm, leg, back, etc.). Preserved here for reference:
            #
            # try:
            #     face_crop = detector.detect_and_crop_face(img)
            #     unique_face = f"face_{uuid.uuid4().hex[:8]}.jpg"
            #     face_path = os.path.join(processed_dir, unique_face)
            #     cv2.imwrite(face_path, cv2.cvtColor(face_crop, cv2.COLOR_RGB2BGR))
            #     logger.debug("Face crop saved at: %s", face_path)
            #     normalized_crop = face_crop
            # except Exception as e:
            #     logger.warning("Face not detected: %s", e)
            #     _clear_inflight(cache_key)
            #     return Response(
            #         {"success": False,
            #          "error": "No human face detected. Please upload a clear, well-lit photo of your face (no hats, no obstructions)."},
            #         status=400,
            #     )

            # SKIN LOGIC: validates human skin presence, not limited to facial detection
            # Prefer a face crop when a face IS present (best ROI for facial
            # conditions). When no face is found, accept ANY image that contains a
            # sufficient proportion of human-skin-coloured pixels using YCrCb skin
            # segmentation — so arm / leg / back / hand photos are allowed. Images
            # with no skin tones at all (objects, screenshots, animals on neutral
            # backgrounds) are still rejected.
            face_crop = None
            try:
                face_crop = detector.detect_and_crop_face(img)
            except Exception as e:
                logger.info("No face detected, falling back to skin-presence check: %s", e)
                face_crop = None

            if face_crop is not None:
                unique_face = f"face_{uuid.uuid4().hex[:8]}.jpg"
                face_path = os.path.join(processed_dir, unique_face)
                cv2.imwrite(face_path, cv2.cvtColor(face_crop, cv2.COLOR_RGB2BGR))
                logger.debug("Face crop saved at: %s", face_path)
                normalized_crop = face_crop
            else:
                # Generic human-skin presence: ratio of skin-coloured pixels in
                # YCrCb space (standard Cr 133-173, Cb 77-127 chrominance range).
                ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
                skin_mask = cv2.inRange(ycrcb, (0, 133, 77), (255, 173, 127))
                skin_ratio = float(cv2.countNonZero(skin_mask)) / float(skin_mask.size or 1)
                logger.info("Skin mode (no face): skin-pixel ratio = %.3f", skin_ratio)

                if skin_ratio < 0.15:
                    _clear_inflight(cache_key)
                    return Response(
                        {
                            "success": False,
                            "error": "No human skin detected. Please upload a clear, well-lit photo of a skin area (face, arm, leg, back, hand, etc.).",
                        },
                        status=400,
                    )
                # Accept the full image as the skin ROI (RGB for the pipeline).
                normalized_crop = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        elif image_type == 'scalp':
            # SCALP mode: REQUIRE proper scalp detection via MediaPipe face
            # landmarks. NO fallback to generic dark-pixel thresholding
            # (which was accepting anything with dark pixels like cats/objects).
            #
            # Also REJECT face photos — if the face occupies a large portion of
            # the image, it's a face/selfie photo, not a scalp/top-of-head photo.
            try:
                # First check face-to-image ratio. A scalp photo typically has
                # either NO face visible, OR the face is small (<35% of image
                # height) because the camera is looking down at the head.
                img_h, img_w = img.shape[:2]
                rgb_for_check = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                face_results = detector.face_mesh.process(rgb_for_check)

                if face_results.multi_face_landmarks:
                    landmarks = face_results.multi_face_landmarks[0].landmark
                    ys = [pt.y * img_h for pt in landmarks]
                    xs = [pt.x * img_w for pt in landmarks]
                    face_height = max(ys) - min(ys)
                    face_width = max(xs) - min(xs)
                    face_area_ratio = (face_height * face_width) / float(img_h * img_w)

                    # If face takes up more than 70% of image area, it's almost
                    # certainly a straight-on selfie, not a scalp photo. We use
                    # 70% (not 35%) because angled or slightly-downward shots
                    # can still show a substantial portion of the face while the
                    # scalp/crown is the primary subject.
                    if face_area_ratio > 0.70:
                        logger.info("Rejecting scalp mode — face area ratio %.2f%% (too large)", face_area_ratio * 100)
                        _clear_inflight(cache_key)
                        return Response(
                            {
                                "success": False,
                                "error": "This looks like a face photo. For scalp analysis, please upload a top-down photo of your head showing the scalp/hair area.",
                            },
                            status=400,
                        )

                scalp_crop = detector.detect_and_crop_scalp(img)
                unique_scalp = f"scalp_{uuid.uuid4().hex[:8]}.jpg"
                scalp_path = os.path.join(processed_dir, unique_scalp)
                cv2.imwrite(scalp_path, cv2.cvtColor(scalp_crop, cv2.COLOR_RGB2BGR))
                logger.debug("Scalp crop saved at: %s", scalp_path)
                normalized_crop = scalp_crop
            except Exception as e:
                logger.warning("Scalp detection failed: %s", e)
                _clear_inflight(cache_key)
                return Response(
                    {
                        "success": False,
                        "error": "No scalp detected. Please upload a clear photo showing the top of the head / scalp area.",
                    },
                    status=400,
                )

        else:
            _clear_inflight(cache_key)
            return Response(
                {"success": False, "error": "Invalid image_type. Must be 'skin' or 'scalp'."},
                status=400
            )

        normalized_crop = normalized_crop.astype(np.uint8)

        # 4. Fetch user context (profile + medical history) for personalised recommendations
        user_profile, medical_history = _get_user_context(request)

        # 5. Base context (conditions and recommendations will be filled by pipeline below)
        context = {
            "analysis_type": image_type,
            "original_image": f"/media/uploads/{unique_name}",
            "face_url": f"/media/processed/{os.path.basename(face_path)}" if face_path else None,
            "scalp_url": f"/media/processed/{os.path.basename(scalp_path)}" if scalp_path else None,
            "analysis_id": uuid.uuid4().hex[:8].upper(),
            "created_at": datetime.utcnow().isoformat() + "Z",
            "max_severity": 0,
            "recommend_dermatologist": False,
            "conditions": [],
            "recommendations": [],
            "recommendations_structured": {},
        }

        # 6. Run AI pipeline (detection + segmentation + severity + LLM recommendations)
        try:
            pipeline_start = time()
            logger.info("Starting pipeline for analysis_id=%s type=%s", context['analysis_id'], image_type)
            pipeline_result = process_image(
                normalized_crop,
                analysis_type=image_type,
                user_profile=user_profile,
                medical_history=medical_history,
                # Full uncropped image (RGB) for the dryness specialist, whose
                # signal weakens on the tight face crop.
                original_image=cv2.cvtColor(img, cv2.COLOR_BGR2RGB),
            )
            logger.info("Pipeline finished in %.2fs — keys: %s", time() - pipeline_start, list(pipeline_result.keys()))
            

            # Add EfficientNet classification scores — show ALL classes
            # (acne, dark_spots, dryness, normal) with their probability, with
            # the % value printed on top of each bar and "normal" coloured
            # green while diseases are coloured warm.
            if image_type == "skin" and 'classification_scores' in pipeline_result:
                scores = pipeline_result['classification_scores']
                context['classification'] = scores

                # Sort by probability descending so the top class is leftmost
                ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
                labels_raw = [k for k, _ in ordered]
                values     = [round(v * 100, 2) for _, v in ordered]
                # Pretty labels: "dark_spots" -> "Dark Spots"
                labels = [l.replace('_', ' ').title() for l in labels_raw]

                # Colour: green for Normal, warm gradient for diseases
                disease_colors = ["#E07A30", "#D45A4A", "#B3454A"]
                colors = []
                disease_i = 0
                for raw in labels_raw:
                    if raw.lower() == "normal":
                        colors.append("#2E8B57")
                    else:
                        colors.append(disease_colors[disease_i % len(disease_colors)])
                        disease_i += 1

                fig, ax = plt.subplots(figsize=(5.5, 3.4))
                bars = ax.bar(labels, values, color=colors, edgecolor="#444444", linewidth=0.6)
                ax.set_title("EfficientNet Classification", fontsize=11, fontweight="bold")
                ax.set_ylabel("Probability (%)")
                ax.set_ylim(0, max(105, max(values) + 10))
                ax.grid(axis='y', linestyle='--', alpha=0.4)
                ax.spines['top'].set_visible(False)
                ax.spines['right'].set_visible(False)
                # Print the % value on top of each bar
                for bar, v in zip(bars, values):
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + 1.5,
                        f"{v:.1f}%",
                        ha='center', va='bottom',
                        fontsize=10, fontweight='bold', color="#222222",
                    )
                plt.tight_layout()

                viz_name = f"efficientnet_{unique_name}.png"
                viz_path = os.path.join(processed_dir, viz_name)
                plt.savefig(viz_path, dpi=130)
                plt.close()

                context['efficientnet_visualization'] = f"/media/processed/{viz_name}"


            if image_type == "scalp" and 'yolo_detections' in pipeline_result:
                # ── P1.3 — YOLO confidence floor (0.45) ──
                # Filter out low-confidence boxes BEFORE any chart, overlay,
                # or condition aggregation runs.
                YOLO_CONF_MIN = 0.45
                _raw_dets = pipeline_result.get('yolo_detections') or []
                detections = [
                    d for d in _raw_dets
                    if float(d.get('confidence', 0)) >= YOLO_CONF_MIN
                ]
                pipeline_result['yolo_detections'] = detections  # keep downstream consistent
                logger.info("YOLO detections kept: %d / %d (≥%.2f conf)",
                            len(detections), len(_raw_dets), YOLO_CONF_MIN)
                logger.debug("Pipeline detected conditions: %s", pipeline_result.get('detected_conditions'))

                try:
                    # ── Prefer the 5-class scalp classifier's FULL probability
                    # distribution so every class appears on the chart (mirrors
                    # the skin chart). Falls back to YOLO per-class max when the
                    # classifier is not active. ──
                    SCALP_DISPLAY = {
                        "Alopecia": "Alopecia",
                        "Dermatitis": "Dermatitis",
                        "Infections": "Infection",
                        "Normal": "Normal Scalp",
                        "Psoriasis": "Psoriasis",
                    }
                    scalp_probs = None
                    for c in (pipeline_result.get('detected_conditions') or []):
                        if c.get('type') == 'scalp' and c.get('probs'):
                            scalp_probs = c['probs']
                            break

                    if scalp_probs:
                        # All classes, highest probability first.
                        ordered = sorted(scalp_probs.items(), key=lambda kv: kv[1], reverse=True)
                        labels_raw = [k for k, _ in ordered]
                        values = [round(v * 100, 2) for _, v in ordered]
                        chart_title = "Scalp Condition Analysis"
                    else:
                        # Legacy YOLO path — aggregate detections by class at MAX conf.
                        per_class_max = {}
                        for det in detections:
                            label = det.get("condition") or det.get("class", "unknown")
                            conf = float(det.get("confidence", 0)) * 100
                            if label not in per_class_max or conf > per_class_max[label]:
                                per_class_max[label] = conf
                        ordered = sorted(per_class_max.items(), key=lambda kv: kv[1], reverse=True)
                        labels_raw = [k for k, _ in ordered]
                        values     = [round(v, 2) for _, v in ordered]
                        if not labels_raw:
                            labels_raw = ["Normal Scalp"]
                            values = [100.0]
                        chart_title = "YOLOv8 Scalp Detection"

                    labels = [SCALP_DISPLAY.get(l, l.replace('_', ' ').title()) for l in labels_raw]

                    disease_colors = ["#E07A30", "#D45A4A", "#B3454A", "#8B3E55"]
                    colors = []
                    di = 0
                    for raw in labels_raw:
                        if raw.lower() in ("normal scalp", "normal"):
                            colors.append("#2E8B57")
                        else:
                            colors.append(disease_colors[di % len(disease_colors)])
                            di += 1

                    fig, ax = plt.subplots(figsize=(6.2, 3.6))
                    bars = ax.bar(labels, values, color=colors, edgecolor="#444444", linewidth=0.6)
                    ax.set_title(chart_title, fontsize=11, fontweight="bold")
                    ax.set_ylabel("Confidence (%)")
                    ax.set_ylim(0, max(105, max(values) + 10))
                    ax.set_xticklabels(labels, rotation=15, ha='right', fontsize=9)
                    ax.grid(axis='y', linestyle='--', alpha=0.4)
                    ax.spines['top'].set_visible(False)
                    ax.spines['right'].set_visible(False)
                    for bar, v in zip(bars, values):
                        ax.text(
                            bar.get_x() + bar.get_width() / 2,
                            bar.get_height() + 1.5,
                            f"{v:.1f}%",
                            ha='center', va='bottom',
                            fontsize=10, fontweight='bold', color="#222222",
                        )
                    plt.tight_layout()

                    yolo_graph_name = f"yolo_chart_{unique_name}.png"
                    yolo_graph_path = os.path.join(processed_dir, yolo_graph_name)
                    plt.savefig(yolo_graph_path, dpi=130)
                    plt.close()

                    context["yolo_chart"] = f"/media/processed/{yolo_graph_name}"

                except Exception as e:
                    logger.warning("YOLO graph error: %s", e)



                scalp_vis = scalp_crop if scalp_crop is not None else normalized_crop
                vis_img = scalp_vis.copy()

                for det in detections:
                    bbox = det.get("bbox")
                    if bbox is None:
                        continue

                    x1, y1, x2, y2 = map(int, bbox)

                    # FIX: use condition instead of class
                    label = det.get("class") or det.get("condition", "unknown")
                    conf = det.get("confidence", 0)

                    cv2.rectangle(vis_img,(x1,y1),(x2,y2),(0,255,0),2)

                    cv2.putText(
                        vis_img,
                        f"{label}:{conf:.2f}",
                        (x1,y1-10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0,255,0),
                        2
                    )

                    

                yolo_name = f"yolo_{unique_name}.jpg"
                yolo_path = os.path.join(processed_dir,yolo_name)

                cv2.imwrite(yolo_path,cv2.cvtColor(vis_img,cv2.COLOR_RGB2BGR))

                context["yolo_visualization"] = f"/media/processed/{yolo_name}"

            if pipeline_result.get('segmentation_mask') is not None:
                logger.debug("Segmentation mask received from pipeline")

                seg = np.array(pipeline_result['segmentation_mask'], dtype=np.uint8)
                # ---------- Severity calculation from segmentation ----------
                total_pixels = seg.size
                affected_pixels = np.count_nonzero(seg)


                coverage_ratio = affected_pixels / total_pixels
                severity_percent = int(min(coverage_ratio * 100, 100))
                
                

                logger.debug("Segmentation coverage: %s%%", severity_percent)

                # attach ROI area to detected conditions
                for cond in pipeline_result.get("detected_conditions", []):
                    cond["roi_area"] = coverage_ratio

                # attach ROI area to YOLO detections as well
                for cond in pipeline_result.get("detected_conditions", []):
                    cond["roi_area"] = coverage_ratio

                # only iterate if YOLO detections exist
                detections = pipeline_result.get("yolo_detections")

                if detections:
                    for det in detections:
                        det["roi_area"] = coverage_ratio
                # Attach segmentation coverage to detected conditions
                if "conditions" in context:
                    for cond in context["conditions"]:
                        cond["coverage"] = severity_percent


                if seg.max() <= 1:
                    seg = (seg * 255).astype(np.uint8)

                # Save colored mask
                mask_name = f"mask_{unique_name}.jpg"
                mask_path = os.path.join(processed_dir, mask_name)

                # normalize segmentation mask for heatmap
                heatmap = cv2.normalize(seg, None, 0, 255, cv2.NORM_MINMAX)

                heatmap = heatmap.astype(np.uint8)

                # create severity heatmap
                colored = cv2.applyColorMap(heatmap, cv2.COLORMAP_TURBO)

                cv2.imwrite(mask_path, colored)

                context['segmentation_mask'] = f"/media/processed/{mask_name}"
                logger.debug("Segmentation mask URL: %s", context['segmentation_mask'])

                
                # Create overlay using selected crop
                if image_type == "skin":

                    if face_crop is not None:
                        overlay_crop = face_crop

                    elif scalp_crop is not None:
                        overlay_crop = scalp_crop

                    else:
                        overlay_crop = normalized_crop

                elif image_type == "scalp":

                    if scalp_crop is not None:
                        overlay_crop = scalp_crop

                    else:
                        overlay_crop = normalized_crop
                # ensure RGB format
                overlay_crop = overlay_crop.astype(np.uint8)

                seg_resized = cv2.resize(
                    seg,
                    (overlay_crop.shape[1], overlay_crop.shape[0]),
                    interpolation=cv2.INTER_NEAREST
                )
                colored_seg = cv2.applyColorMap(seg_resized, cv2.COLORMAP_JET)
                overlay = cv2.addWeighted(overlay_crop, 0.65, colored_seg, 0.35, 0)


                vis_name = f"vis_{unique_name}.jpg"
                viz_dir = os.path.join(settings.MEDIA_ROOT, 'visualizations')
                os.makedirs(viz_dir, exist_ok=True)
                final_vis_path = os.path.join(viz_dir, vis_name)

                cv2.imwrite(final_vis_path, cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR))
                context['visualized_image'] = f"/media/visualizations/{vis_name}"
                logger.debug("Segmentation overlay URL: %s", context['visualized_image'])

            

            # ── P1.3 — Area-percentage severity scoring ──────────────
            # mild = <5% affected area, moderate = 5-15%, severe = >15%.
            # Falls back to confidence-derived score when no per-condition
            # area information is available.
            def _area_to_severity(area_pct):
                if area_pct < 5:    return 'Mild',     int(min(35,  area_pct * 7))
                if area_pct < 15:   return 'Moderate', int(35 + (area_pct - 5)  * 4)
                return                   'Severe',     int(min(100, 75 + (area_pct - 15) * 1.5))

            # --- Scalp via 5-class classifier (no YOLO boxes / no area) ---
            # The classifier returns a single predicted class + full per-class
            # probabilities. Severity is derived from model confidence (there is
            # no lesion-area segmentation for scalp), so the report shows a real
            # condition + severity instead of "Normal / Unknown".
            _scalp_clf = None
            if image_type == "scalp":
                for _c in pipeline_result.get('detected_conditions', []):
                    if _c.get('type') == 'scalp' and _c.get('probs'):
                        _scalp_clf = _c
                        break

            if image_type == "scalp" and _scalp_clf is not None:
                SCALP_DISPLAY = {
                    "Alopecia": "Alopecia (Hair Loss)", "Dermatitis": "Dermatitis",
                    "Infections": "Scalp Infection", "Normal": "Healthy Scalp",
                    "Psoriasis": "Scalp Psoriasis",
                }
                # Per-condition clinical weight — how serious the condition is when
                # present (Infections > Psoriasis ≈ Alopecia > Dermatitis). Used to
                # scale the confidence-derived severity, since there is no lesion-area
                # segmentation for scalp.
                SCALP_WEIGHT = {
                    "Infections": 1.00, "Psoriasis": 0.90, "Alopecia": 0.85,
                    "Dermatitis": 0.75,
                }

                probs = _scalp_clf['probs']
                top_cls = max(probs, key=probs.get)
                top_p = float(probs[top_cls])
                disp = SCALP_DISPLAY.get(top_cls, top_cls)
                # True affected-area fraction from the classifier's CAM (0..1).
                affected_area = float(_scalp_clf.get('affected_area', 0.0))
                area_pct = round(affected_area * 100, 1)

                if top_cls.lower() == 'normal':
                    context['conditions'] = [{
                        'name': 'Healthy Scalp', 'severity_level': 'Healthy',
                        'severity_score': 0, 'area_pct': 0.0,
                        'confidence': round(top_p, 3),
                    }]
                    context['max_severity'] = 0
                else:
                    # TRUE area-based severity: how much of the scalp the condition
                    # covers (from the CAM), scaled by the condition's clinical
                    # weight — same mild/moderate/severe bands the skin branch uses.
                    weight = SCALP_WEIGHT.get(top_cls, 0.85)
                    base_level, base_score = _area_to_severity(area_pct)
                    score_int = int(round(min(100, max(8, base_score * weight))))
                    if score_int < 35:
                        level = 'Mild'
                    elif score_int < 70:
                        level = 'Moderate'
                    else:
                        level = 'Severe'
                    context['conditions'] = [{
                        'name': disp, 'severity_level': level,
                        'severity_score': score_int, 'area_pct': area_pct,
                        'confidence': round(top_p, 3),
                    }]
                    context['max_severity'] = score_int

            # --- Scalp: build conditions from filtered YOLO detections ---
            elif image_type == "scalp" and pipeline_result.get('yolo_detections'):
                # Aggregate by class, computing total bbox area as a % of frame.
                frame_h, frame_w = normalized_crop.shape[:2]
                frame_area = max(1, frame_h * frame_w)
                per_cls_area = {}
                per_cls_conf = {}
                for det in pipeline_result['yolo_detections']:
                    name = det.get('condition') or det.get('class') or 'normal'
                    bbox = det.get('bbox')
                    if bbox and len(bbox) == 4:
                        x1, y1, x2, y2 = bbox
                        a = max(0, (x2 - x1)) * max(0, (y2 - y1)) / frame_area * 100
                    else:
                        a = float(det.get('roi_area', 0)) * 100
                    per_cls_area[name] = per_cls_area.get(name, 0) + a
                    per_cls_conf[name] = max(per_cls_conf.get(name, 0),
                                              float(det.get('confidence', 0)))

                # Per-zone breakdown — split image into crown / sides / nape.
                zones = {'crown': 0.0, 'sides': 0.0, 'nape': 0.0}
                for det in pipeline_result['yolo_detections']:
                    bbox = det.get('bbox')
                    if not bbox or len(bbox) != 4:
                        continue
                    _, y1, _, y2 = bbox
                    cy = (y1 + y2) / 2
                    rel = cy / frame_h
                    a = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]) / frame_area * 100
                    if rel < 1/3:
                        zones['crown'] += a
                    elif rel < 2/3:
                        zones['sides'] += a
                    else:
                        zones['nape']  += a
                context['scalp_zones'] = {k: round(v, 2) for k, v in zones.items()}

                # Top-3 by area only; suppress noise.
                ranked = sorted(per_cls_area.items(), key=lambda kv: kv[1], reverse=True)[:3]
                formatted = []
                for name, area_pct in ranked:
                    if name.lower() == 'normal':
                        continue
                    level, score_int = _area_to_severity(area_pct)
                    formatted.append({
                        'name':            name.replace('_', ' ').title(),
                        'severity_level':  level,
                        'severity_score':  score_int,
                        'area_pct':        round(area_pct, 2),
                        'confidence':      round(per_cls_conf.get(name, 0), 3),
                    })
                if formatted:
                    context['conditions'] = formatted

            # --- Skin: detected_conditions, top-3 by area when available --
            elif 'detected_conditions' in pipeline_result:
                sev = pipeline_result.get('severity_scores', {})
                formatted = []
                for c in pipeline_result.get('detected_conditions', []):
                    name = c.get('name') or c.get('condition') or "normal"
                    if name.lower() == 'normal':
                        continue
                    confidence = float(c.get('confidence', 0))
                    area_pct   = float(c.get('roi_area', 0)) * 100

                    # Prefer area-based severity; fall back to LLM/score map.
                    if area_pct > 0:
                        level, score_int = _area_to_severity(area_pct)
                    else:
                        s = sev.get(name, {'score': confidence * 100, 'level': 'Mild'})
                        score_int = int(s.get('score', confidence * 100))
                        level     = s.get('level', 'Mild')

                    formatted.append({
                        'name':           name.replace('_', ' ').title(),
                        'severity_level': level,
                        'severity_score': score_int,
                        'area_pct':       round(area_pct, 2),
                        'confidence':     round(confidence, 3),
                    })
                # Top-3 by area first, then by score.
                formatted.sort(key=lambda x: (x['area_pct'], x['severity_score']), reverse=True)
                if formatted:
                    context['conditions'] = formatted[:3]


            # Skip for the scalp-classifier path — it already set max_severity
            # from model confidence (XGBoost severity doesn't apply there).
            if 'severity_scores' in pipeline_result and _scalp_clf is None:
                context['max_severity'] = max(
                    [v.get('score', 0) for v in pipeline_result.get('severity_scores', {}).values()],
                    default=0
                )

            # LLM personalised recommendations
            if 'recommendations' in pipeline_result:
                recs_structured = pipeline_result['recommendations']
                context['recommendations_structured'] = recs_structured
                # Also flatten to list for HTML template
                context['recommendations'] = _format_recommendations_for_template(recs_structured)
                # Flag: recommend dermatologist if severity high or LLM says so
                consult_text = recs_structured.get('dermatologist_consult', '')
                max_sev_check = context.get('max_severity', 0)
                context['recommend_dermatologist'] = (
                    max_sev_check >= 70
                    or any(w in consult_text.lower() for w in ['promptly', 'urgent', 'immediately', '⚠️'])
                )

            # Store last analysis for results view
            try:
                request.session['last_analysis'] = {
                    'analysis_id': context.get('analysis_id'),
                    'image_type': image_type,
                    'original_image': context.get('original_image'),
                    'face_crop': context.get('face_url'),
                    'scalp_crop': context.get('scalp_url'),
                    'segmentation_mask': context.get('segmentation_mask', ''),
                    'visualized_image': context.get('visualized_image', ''),
                    'conditions': context.get('conditions', []),
                    'recommendations': context.get('recommendations', []),
                    'recommendations_structured': context.get('recommendations_structured', {}),
                    'recommend_dermatologist': context.get('recommend_dermatologist', False),
                    'max_severity': context.get('max_severity', 0),
                }

                # Save to database (persistent, user-linked history)
                try:
                    max_sev = int(context.get('max_severity', 0) or 0)
                except Exception:
                    max_sev = 0

                if max_sev < 30:
                    severity_label = "Mild"
                elif max_sev < 70:
                    severity_label = "Moderate"
                else:
                    severity_label = "Severe"

                if request.user and request.user.is_authenticated:
                    try:
                        AnalysisResult.objects.update_or_create(
                            analysis_id=context.get('analysis_id'),
                            defaults={
                                'user': request.user,
                                'analysis_type': image_type,
                                'original_image': context.get('original_image', ''),
                                'face_url': context.get('face_url'),
                                'scalp_url': context.get('scalp_url'),
                                'segmentation_mask': context.get('segmentation_mask'),
                                'visualized_image': context.get('visualized_image'),
                                'yolo_visualization': context.get('yolo_visualization'),
                                'yolo_chart': context.get('yolo_chart'),
                                'efficientnet_visualization': context.get('efficientnet_visualization'),
                                'conditions': context.get('conditions', []),
                                'recommendations': context.get('recommendations', []),
                                'recommendations_structured': context.get('recommendations_structured', {}),
                                'max_severity': max_sev,
                                'severity_label': severity_label,
                                'recommend_dermatologist': context.get('recommend_dermatologist', False),
                            }
                        )
                        logger.info("Saved analysis %s to DB for user %s", context.get('analysis_id'), request.user.email)
                    except Exception as db_err:
                        logger.warning("Failed to save analysis to DB: %s", db_err)

                request.session.modified = True
            except Exception:
                pass

        except Exception as e:
            logger.exception("Failed to run pipeline during upload: %s", e)

        # 6. Return JSON for API clients, otherwise render HTML
        if wants_json:
            # Store in idempotency cache for future duplicates.
            try:
                if cache_key:
                    # Store in global cache (works across sessions)
                    with GLOBAL_ANALYSIS_CACHE_LOCK:
                        # Publish result and clear inflight marker.
                        inflight = GLOBAL_ANALYSIS_INFLIGHT.pop(cache_key, None)
                        if inflight and inflight.get("event"):
                            try:
                                inflight["event"].set()
                            except Exception:
                                pass
                        GLOBAL_ANALYSIS_CACHE[cache_key] = {
                            "ts": time(),
                            "context": context,
                        }
                        # Soft limit
                        if len(GLOBAL_ANALYSIS_CACHE) > GLOBAL_CACHE_MAX_ITEMS:
                            # Remove oldest-ish keys
                            sorted_items = sorted(
                                GLOBAL_ANALYSIS_CACHE.items(),
                                key=lambda kv: kv[1].get("ts", 0)
                            )
                            for k, _ in sorted_items[: max(0, len(GLOBAL_ANALYSIS_CACHE) - GLOBAL_CACHE_MAX_ITEMS)]:
                                GLOBAL_ANALYSIS_CACHE.pop(k, None)

                # Session cache disabled during AI rebuild — actively wipe
                # any stored entries so a future "re-enable" doesn't serve
                # stale data from before the model change.
                if "analysis_result_cache" in request.session:
                    request.session.pop("analysis_result_cache", None)
                    request.session.modified = True
            except Exception:
                pass
            return Response({"success": True, "data": context}, status=200)

        # HTML fallback (existing template flow)
        try:
            if cache_key:
                with GLOBAL_ANALYSIS_CACHE_LOCK:
                    # Publish result and clear inflight marker.
                    inflight = GLOBAL_ANALYSIS_INFLIGHT.pop(cache_key, None)
                    if inflight and inflight.get("event"):
                        try:
                            inflight["event"].set()
                        except Exception:
                            pass
                    GLOBAL_ANALYSIS_CACHE[cache_key] = {
                        "ts": time(),
                        "context": context,
                    }
                # Session cache disabled during AI rebuild (same reason as JSON branch above).
                if "analysis_result_cache" in request.session:
                    request.session.pop("analysis_result_cache", None)
                    request.session.modified = True
        except Exception:
            pass
        # API is JSON-only (React frontend). The legacy template render was
        # removed; non-JSON clients get the same JSON payload as the JSON branch.
        return Response({"success": True, "data": context}, status=200)