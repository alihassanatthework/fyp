import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from image_analysis.models import AnalysisResult
from .models import DiagnosisReport

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def diagnosis_detail(request, analysis_id):
    """
    GET /api/diagnosis/<analysis_id>/
    Returns the DiagnosisReport for one of the user's analyses.
    """
    try:
        analysis = AnalysisResult.objects.get(analysis_id=analysis_id, user=request.user)
    except AnalysisResult.DoesNotExist:
        return Response({'error': 'Analysis not found.'}, status=status.HTTP_404_NOT_FOUND)

    try:
        report = analysis.diagnosis
    except DiagnosisReport.DoesNotExist:
        return Response({'error': 'Diagnosis report not available for this analysis.'}, status=status.HTTP_404_NOT_FOUND)

    return Response({
        'analysis_id':            analysis_id,
        'primary_condition':      report.primary_condition,
        'confidence_score':       report.confidence_score,
        'severity_level':         report.severity_level,
        'all_conditions':         report.all_conditions,
        'recommend_dermatologist':report.recommend_dermatologist,
        'summary':                report.summary,
        'created_at':             report.created_at.strftime('%d %b %Y · %I:%M %p'),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def diagnosis_list(request):
    """
    GET /api/diagnosis/
    Returns all DiagnosisReports for the current user, newest first.
    """
    reports = DiagnosisReport.objects.filter(user=request.user).select_related('analysis')

    data = []
    for r in reports:
        data.append({
            'analysis_id':             r.analysis.analysis_id,
            'analysis_type':           r.analysis.analysis_type,
            'primary_condition':       r.primary_condition,
            'confidence_score':        r.confidence_score,
            'severity_level':          r.severity_level,
            'recommend_dermatologist': r.recommend_dermatologist,
            'created_at':              r.created_at.strftime('%d %b %Y · %I:%M %p'),
        })

    return Response(data)
