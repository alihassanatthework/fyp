import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from image_analysis.models import AnalysisResult
from .models import AnalysisFeedback
from .serializers import FeedbackSerializer

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_feedback(request, analysis_id):
    """
    POST /api/feedback/<analysis_id>/
    Submit a star rating + optional comment for one of the user's analyses.
    Only the owner of the analysis can submit feedback.
    """
    try:
        analysis = AnalysisResult.objects.get(analysis_id=analysis_id, user=request.user)
    except AnalysisResult.DoesNotExist:
        return Response({'error': 'Analysis not found.'}, status=status.HTTP_404_NOT_FOUND)

    # Only one feedback per analysis (OneToOne)
    if hasattr(analysis, 'feedback'):
        return Response({'error': 'Feedback already submitted for this analysis.'}, status=status.HTTP_400_BAD_REQUEST)

    data = {**request.data, 'analysis': analysis.id}
    serializer = FeedbackSerializer(data=data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    serializer.save(user=request.user, analysis=analysis)
    logger.info("Feedback submitted by %s for analysis %s (rating=%s)",
                request.user.email, analysis_id, request.data.get('rating'))
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_feedback(request, analysis_id):
    """
    GET /api/feedback/<analysis_id>/
    Retrieve existing feedback for an analysis (if submitted).
    """
    try:
        analysis = AnalysisResult.objects.get(analysis_id=analysis_id, user=request.user)
    except AnalysisResult.DoesNotExist:
        return Response({'error': 'Analysis not found.'}, status=status.HTTP_404_NOT_FOUND)

    if not hasattr(analysis, 'feedback'):
        return Response({'feedback': None}, status=status.HTTP_200_OK)

    return Response(FeedbackSerializer(analysis.feedback).data)
