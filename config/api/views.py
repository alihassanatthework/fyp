"""
API endpoints for analysis history and detail.

Results are now stored in PostgreSQL (AnalysisResult model) linked to the
authenticated user, replacing the old session-based approach.
"""

import logging

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination

from image_analysis.models import AnalysisResult

from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


class HistoryPagination(PageNumberPagination):
    """20 items per page. Client can override with ?page_size=N (max 100)."""
    page_size            = 20
    page_size_query_param = 'page_size'
    max_page_size        = 100


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def analysis_stats(request):
    """
    GET /api/analysis/stats/
    Returns a summary card for the dashboard — total scans, breakdown by
    severity, last scan date, and whether a follow-up is recommended.
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

    # Recommend follow-up if last scan was >= 30 days ago or had severe result
    needs_followup = False
    if last:
        days_since = (timezone.now() - last.created_at).days
        needs_followup = days_since >= 30 or last.severity_label == 'Severe' or last.recommend_dermatologist

    return Response({
        'total_scans':     total,
        'skin_scans':      qs.filter(analysis_type='skin').count(),
        'scalp_scans':     qs.filter(analysis_type='scalp').count(),
        'severity_counts': severity_counts,
        'last_scan_date':  last_scan_date,
        'last_scan_type':  last_scan_type,
        'needs_followup':  needs_followup,
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
