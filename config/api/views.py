"""
API endpoints for analysis history and detail.

Results are now stored in PostgreSQL (AnalysisResult model) linked to the
authenticated user, replacing the old session-based approach.
"""

import logging
from collections import Counter

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination

from image_analysis.models import AnalysisResult

from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


class HistoryPagination(PageNumberPagination):
    """20 items per page. Client can override with ?page_size=N (max 100)."""
    page_size            = 20
    page_size_query_param = 'page_size'
    max_page_size        = 100


def _compute_health_score(qs):
    """Composite 0–100 health score from severity distribution.
    Higher = healthier. Fallback 50 for empty querysets."""
    total = qs.count()
    if total == 0:
        return 50
    mild     = qs.filter(severity_label='Mild').count()
    moderate = qs.filter(severity_label='Moderate').count()
    severe   = qs.filter(severity_label='Severe').count()
    unknown  = total - (mild + moderate + severe)
    # Weighted: mild = 100, moderate = 55, severe = 15, unknown ≈ 70
    score = (mild * 100 + moderate * 55 + severe * 15 + unknown * 70) / max(total, 1)
    return int(round(max(0, min(100, score))))


def _linear_projection(daily_scores, days_ahead=30):
    """Tiny linear regression. Returns projected score `days_ahead` from
    the last data point; clamps to [0,100]. Falls back to last value if
    too few data points."""
    pts = [(i, v) for i, v in enumerate(daily_scores) if v is not None]
    if len(pts) < 2:
        return daily_scores[-1] if daily_scores and daily_scores[-1] is not None else 70
    n = len(pts)
    sx  = sum(p[0] for p in pts)
    sy  = sum(p[1] for p in pts)
    sxy = sum(p[0] * p[1] for p in pts)
    sxx = sum(p[0] ** 2  for p in pts)
    denom = (n * sxx - sx * sx) or 1
    slope = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n
    future_x = pts[-1][0] + days_ahead
    projected = slope * future_x + intercept
    return int(round(max(0, min(100, projected))))


def _compute_streak(qs):
    """Consecutive days ending today (or yesterday) with at least one scan."""
    if not qs.exists():
        return 0
    seen = {r.created_at.date() for r in qs}
    cur = timezone.now().date()
    if cur not in seen and (cur - timedelta(days=1)) not in seen:
        return 0
    if cur not in seen:
        cur = cur - timedelta(days=1)
    streak = 0
    while cur in seen:
        streak += 1
        cur = cur - timedelta(days=1)
    return streak


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def analysis_stats(request):
    """
    GET /api/analysis/stats/
    Rich dashboard payload — basic counts PLUS health score, projection,
    daily timeline, recurring conditions, streak and recent thumbnails
    for the bento dashboard.
    """
    qs = AnalysisResult.objects.filter(user=request.user)
    total = qs.count()

    last = qs.first()  # ordered by -created_at
    last_scan_date = last.created_at.strftime("%d %b %Y") if last else None
    last_scan_type = last.analysis_type if last else None

    severity_counts = {
        'Mild':     qs.filter(severity_label='Mild').count(),
        'Moderate': qs.filter(severity_label='Moderate').count(),
        'Severe':   qs.filter(severity_label='Severe').count(),
    }

    needs_followup = False
    if last:
        days_since = (timezone.now() - last.created_at).days
        needs_followup = days_since >= 30 or last.severity_label == 'Severe' or last.recommend_dermatologist

    # ── Health score + month-over-month trend ─────────────────────────
    today = timezone.now().date()
    month_ago = today - timedelta(days=30)
    sixty_ago = today - timedelta(days=60)
    qs_now  = qs.filter(created_at__date__gte=month_ago)
    qs_prev = qs.filter(created_at__date__gte=sixty_ago, created_at__date__lt=month_ago)
    health_score      = _compute_health_score(qs_now if qs_now.exists() else qs)
    health_score_prev = _compute_health_score(qs_prev) if qs_prev.exists() else None
    health_trend      = (health_score - health_score_prev) if health_score_prev is not None else 0

    # ── 30-day daily timeline (per-day counts + per-day score) ────────
    daily_counts = []
    daily_scores = []
    for i in range(29, -1, -1):
        d = today - timedelta(days=i)
        day_qs = qs.filter(created_at__date=d)
        c_total = day_qs.count()
        day_score = _compute_health_score(day_qs) if c_total else None
        daily_counts.append({
            'date':   d.isoformat(),
            'total':  c_total,
            'mild':     day_qs.filter(severity_label='Mild').count(),
            'moderate': day_qs.filter(severity_label='Moderate').count(),
            'severe':   day_qs.filter(severity_label='Severe').count(),
            'score':  day_score,
        })
        daily_scores.append(day_score)

    # Carry-forward score so projection doesn't snap to 0 on gap days.
    carried = []
    last_val = None
    for v in daily_scores:
        if v is not None:
            last_val = v
        carried.append(last_val if last_val is not None else 50)
    projection_30d = _linear_projection(carried, days_ahead=30)

    # ── Top recurring conditions (excludes "Normal") ─────────────────
    # P4 — cache per-user for 60s to avoid O(N) iteration on each load.
    cache_key = f"recurring_conditions:{request.user.id}"
    recurring_conditions = cache.get(cache_key)
    if recurring_conditions is None:
        cond_counter = Counter()
        for obj in qs:
            if isinstance(obj.conditions, list):
                for c in obj.conditions:
                    name = c.get('name') if isinstance(c, dict) else None
                    if name and name.lower() != 'normal':
                        cond_counter[name] += 1
        recurring_conditions = [
            {'name': n, 'count': c} for n, c in cond_counter.most_common(5)
        ]
        cache.set(cache_key, recurring_conditions, 60)

    # ── Recent scans (timeline + constellation source) ───────────────
    recent_scans = []
    for obj in qs[:30]:
        top_condition = ''
        if isinstance(obj.conditions, list) and obj.conditions:
            first = obj.conditions[0]
            top_condition = first.get('name', '') if isinstance(first, dict) else ''
        recent_scans.append({
            'analysis_id':   obj.analysis_id,
            'analysis_type': obj.analysis_type,
            'date':          obj.created_at.isoformat(),
            'severity':      obj.severity_label,
            'severity_score': int(obj.max_severity or 0),
            'top_condition': top_condition,
            'thumbnail':     getattr(obj, 'visualized_image_url', None)
                             or getattr(obj, 'face_image_url', None)
                             or getattr(obj, 'original_image_url', None),
        })

    return Response({
        'total_scans':     total,
        'skin_scans':      qs.filter(analysis_type='skin').count(),
        'scalp_scans':     qs.filter(analysis_type='scalp').count(),
        'severity_counts': severity_counts,
        'last_scan_date':  last_scan_date,
        'last_scan_type':  last_scan_type,
        'needs_followup':  needs_followup,

        # Bento dashboard extensions
        'health_score':      health_score,
        'health_trend':      health_trend,
        'projection_30d':    projection_30d,
        'streak_days':       _compute_streak(qs),
        'daily_timeline':    daily_counts,
        'recurring_conditions': recurring_conditions,
        'recent_scans':      recent_scans,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def analysis_history(request):
    """
    GET /api/analysis/history/
    Returns the current user's past analyses, newest first.
    Supports ?type= and ?severity= filters (same values the React UI sends).
    """
    qs = AnalysisResult.objects.filter(user=request.user)

    # --- optional filters sent by the React AnalysisHistory page ---
    type_filter = request.query_params.get("type", "All Types")
    severity_filter = request.query_params.get("severity", "All Severities")

    if type_filter and type_filter != "All Types":
        if "skin" in type_filter.lower():
            qs = qs.filter(analysis_type="skin")
        elif "scalp" in type_filter.lower():
            qs = qs.filter(analysis_type="scalp")

    if severity_filter and severity_filter != "All Severities":
        qs = qs.filter(severity_label=severity_filter)

    # Build the list shape the React History/AnalysisHistory pages expect
    results = []
    for obj in qs:
        top_condition = ""
        if isinstance(obj.conditions, list) and obj.conditions:
            top_condition = obj.conditions[0].get("name", "")

        if obj.max_severity < 30:
            severity_class = "badge-mild"
        elif obj.max_severity < 70:
            severity_class = "badge-moderate"
        else:
            severity_class = "badge-severe"

        results.append({
            "id":            obj.analysis_id,
            "type":          obj.analysis_type,
            "date":          obj.created_at.strftime("%d %b %Y · %I:%M %p"),
            "name":          top_condition or obj.analysis_type,
            "severity":      obj.severity_label,
            "severityClass": severity_class,
        })

    # Paginate
    paginator = HistoryPagination()
    page = paginator.paginate_queryset(results, request)
    if page is not None:
        return paginator.get_paginated_response(page)
    return Response(results, status=status.HTTP_200_OK)


@api_view(["GET", "DELETE"])
@permission_classes([IsAuthenticated])
def analysis_detail(request, analysis_id):
    """
    GET  /api/analysis/<id>/  — full result for one scan
    DELETE /api/analysis/<id>/  — delete it
    Both are scoped to the current user (can't read another user's scan).
    """
    try:
        obj = AnalysisResult.objects.get(analysis_id=analysis_id, user=request.user)
    except AnalysisResult.DoesNotExist:
        return Response({"error": "Analysis not found."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        return Response(obj.to_context_dict(), status=status.HTTP_200_OK)

    if request.method == "DELETE":
        obj.delete()
        logger.info("Deleted analysis %s for user %s", analysis_id, request.user.email)
        return Response({}, status=status.HTTP_200_OK)

    return Response({"error": "Method not allowed."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
