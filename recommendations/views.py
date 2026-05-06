import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from image_analysis.models import AnalysisResult
from .models import Recommendation

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recommendations_for_analysis(request, analysis_id):
    """
    GET /api/recommendations/<analysis_id>/
    Returns all Recommendation rows for one of the user's analyses,
    grouped by category for easy rendering.
    """
    try:
        analysis = AnalysisResult.objects.get(analysis_id=analysis_id, user=request.user)
    except AnalysisResult.DoesNotExist:
        return Response({'error': 'Analysis not found.'}, status=status.HTTP_404_NOT_FOUND)

    recs = Recommendation.objects.filter(analysis=analysis).order_by('order')

    # Group by category
    grouped = {}
    for r in recs:
        grouped.setdefault(r.category, []).append({
            'id':          r.id,
            'title':       r.title,
            'description': r.description,
            'order':       r.order,
        })

    return Response({
        'analysis_id': analysis_id,
        'total':       recs.count(),
        'grouped':     grouped,
        'flat':        list(recs.values('id', 'category', 'title', 'description', 'order')),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def all_recommendations(request):
    """
    GET /api/recommendations/
    Returns all recommendations for the current user across all analyses,
    newest analysis first. Useful for a "My recommendations" summary page.
    """
    recs = (
        Recommendation.objects
        .filter(user=request.user)
        .select_related('analysis')
        .order_by('-analysis__created_at', 'order')
    )

    data = [{
        'id':           r.id,
        'analysis_id':  r.analysis.analysis_id,
        'analysis_type':r.analysis.analysis_type,
        'category':     r.category,
        'title':        r.title,
        'description':  r.description,
        'order':        r.order,
    } for r in recs]

    return Response(data)
