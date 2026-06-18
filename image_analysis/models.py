import os
import logging

from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.conf import settings

logger = logging.getLogger(__name__)


class AnalysisResult(models.Model):
    """
    Persists the output of one AI pipeline run for a logged-in user.

    Every field mirrors a key in the `context` dict built inside
    AnalyzeImageView so serialisation is straightforward.
    """

    ANALYSIS_TYPE_CHOICES = [('skin', 'Skin'), ('scalp', 'Scalp')]
    SEVERITY_CHOICES = [('Mild', 'Mild'), ('Moderate', 'Moderate'), ('Severe', 'Severe')]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='analyses'
    )
    analysis_id = models.CharField(max_length=20, unique=True, db_index=True)
    analysis_type = models.CharField(max_length=10, choices=ANALYSIS_TYPE_CHOICES)

    # --- image URLs (relative /media/... paths) --------------------------------
    original_image = models.CharField(max_length=500, blank=True, default='')
    face_url = models.CharField(max_length=500, blank=True, null=True)
    scalp_url = models.CharField(max_length=500, blank=True, null=True)
    segmentation_mask = models.CharField(max_length=500, blank=True, null=True)
    visualized_image = models.CharField(max_length=500, blank=True, null=True)
    yolo_visualization = models.CharField(max_length=500, blank=True, null=True)
    yolo_chart = models.CharField(max_length=500, blank=True, null=True)
    efficientnet_visualization = models.CharField(max_length=500, blank=True, null=True)

    # --- AI results (stored as JSON) -----------------------------------------
    conditions = models.JSONField(default=list)
    recommendations = models.JSONField(default=list)
    recommendations_structured = models.JSONField(default=dict)

    # --- severity summary -----------------------------------------------------
    max_severity = models.IntegerField(default=0)
    severity_label = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='Mild')
    recommend_dermatologist = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} | {self.analysis_type} | {self.analysis_id}"

    # Fields that hold /media/... relative URL paths to image files on disk
    _IMAGE_FIELDS = (
        'original_image', 'face_url', 'scalp_url',
        'segmentation_mask', 'visualized_image',
        'yolo_visualization', 'yolo_chart', 'efficientnet_visualization',
    )

    def delete_media_files(self):
        """Delete all image files from disk that belong to this analysis."""
        for field in self._IMAGE_FIELDS:
            rel_url = getattr(self, field, None)
            if not rel_url:
                continue
            # Convert /media/uploads/abc.jpg  →  <MEDIA_ROOT>/uploads/abc.jpg
            rel_path = rel_url.lstrip('/')          # strip leading slash
            rel_path = rel_path[len('media/'):] if rel_path.startswith('media/') else rel_path
            abs_path = os.path.join(settings.MEDIA_ROOT, rel_path)
            if os.path.isfile(abs_path):
                try:
                    os.remove(abs_path)
                    logger.debug("Deleted media file: %s", abs_path)
                except OSError as exc:
                    logger.warning("Could not delete media file %s: %s", abs_path, exc)

    # Convenience: convert to the same dict shape the React frontend expects
    def to_context_dict(self):
        return {
            "analysis_id": self.analysis_id,
            "analysis_type": self.analysis_type,
            "original_image": self.original_image,
            "face_url": self.face_url,
            "scalp_url": self.scalp_url,
            "segmentation_mask": self.segmentation_mask,
            "visualized_image": self.visualized_image,
            "yolo_visualization": self.yolo_visualization,
            "yolo_chart": self.yolo_chart,
            "efficientnet_visualization": self.efficientnet_visualization,
            "conditions": self.conditions,
            "recommendations": self.recommendations,
            "recommendations_structured": self.recommendations_structured,
            "max_severity": self.max_severity,
            "severity": self.severity_label,
            "recommend_dermatologist": self.recommend_dermatologist,
            # Human-friendly label (kept for backward compatibility) …
            "date": self.created_at.strftime("%d %b %Y · %I:%M %p"),
            # … plus a clean ISO timestamp the frontend can reliably parse
            # (the "·" in `date` makes new Date() return Invalid Date).
            "created_at": self.created_at.isoformat(),
        }


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------

@receiver(post_delete, sender=AnalysisResult)
def cleanup_analysis_media(sender, instance, **kwargs):
    """Delete image files from disk when an analysis record is removed."""
    instance.delete_media_files()


from django.db.models.signals import post_save  # noqa: E402

@receiver(post_save, sender=AnalysisResult)
def create_diagnosis_and_recommendations(sender, instance, created, **kwargs):
    """
    After a new AnalysisResult is saved, automatically populate:
      - DiagnosisReport  (one per analysis)
      - Recommendation   (one row per recommendation item)
    Imported here to avoid circular imports (diagnosis/recommendations import
    AnalysisResult, which lives in this file).
    """
    if not created:
        return  # only on initial creation, not updates

    try:
        from diagnosis.models import DiagnosisReport
        from recommendations.models import Recommendation

        # --- DiagnosisReport ---
        conditions = instance.conditions or []
        primary = conditions[0].get('name', '') if conditions else ''
        confidence = conditions[0].get('severity_score', 0) if conditions else 0

        DiagnosisReport.objects.create(
            user=instance.user,
            analysis=instance,
            primary_condition=primary,
            confidence_score=float(confidence),
            severity_level=instance.severity_label,
            all_conditions=conditions,
            recommend_dermatologist=instance.recommend_dermatologist,
            summary='',  # can be populated by LLM in a future phase
        )

        # --- Recommendations ---
        recs_structured = instance.recommendations_structured or {}
        order = 0

        def _add(category, items):
            nonlocal order
            if not items:
                return
            if isinstance(items, str):
                items = [items]
            for item in items:
                if not item:
                    continue
                if isinstance(item, dict):
                    title = item.get('name', '')
                    desc  = item.get('reason', '') or str(item)
                else:
                    title = ''
                    desc  = str(item)
                Recommendation.objects.create(
                    user=instance.user, analysis=instance,
                    category=category, title=title,
                    description=desc, order=order,
                )
                order += 1

        _add('morning_routine', recs_structured.get('daily_routine', {}).get('morning', []))
        _add('evening_routine', recs_structured.get('daily_routine', {}).get('evening', []))
        _add('weekly_routine',  recs_structured.get('weekly_routine', []))
        _add('product',         recs_structured.get('products', []))
        _add('safety_note',     recs_structured.get('safety_notes', []))
        _add('dermatologist',   recs_structured.get('dermatologist_consult', ''))

        logger.debug(
            "Created DiagnosisReport + %d Recommendations for analysis %s",
            order, instance.analysis_id,
        )
    except Exception as exc:
        logger.warning("Signal create_diagnosis_and_recommendations failed: %s", exc)


# ── Daily scan-limit helpers (Free tier cap, Premium unlimited) ──────
# Free accounts may run up to FREE_DAILY_SCAN_LIMIT scans per CALENDAR DAY
# (resets at midnight, server timezone). Premium accounts are unlimited.
FREE_DAILY_SCAN_LIMIT = 5


def scans_used_today(user) -> int:
    """Count of analyses this user created today (server-local calendar day)."""
    from django.utils import timezone
    today = timezone.localdate()
    return AnalysisResult.objects.filter(user=user, created_at__date=today).count()


def scan_quota(user) -> dict:
    """Return the user's daily scan quota status.
    { account_type, is_premium, used, limit, remaining }.
    For premium, limit and remaining are None (unlimited)."""
    from django.conf import settings
    prof = getattr(user, 'profile', None)
    account_type = getattr(prof, 'account_type', 'free') if prof else 'free'
    is_premium = (account_type == 'premium')
    limit = None if is_premium else int(getattr(settings, 'FREE_DAILY_SCAN_LIMIT', FREE_DAILY_SCAN_LIMIT))
    used = scans_used_today(user)
    remaining = None if is_premium else max(0, limit - used)
    return {
        'account_type': account_type,
        'is_premium': is_premium,
        'used': used,
        'limit': limit,
        'remaining': remaining,
    }
