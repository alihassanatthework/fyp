import os
import logging

from django.conf import settings
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import MakeupSuggestion
from .services import (
    detect_face_shape, detect_skin_tone_and_undertone, get_makeup_suggestions,
)

logger = logging.getLogger(__name__)


def _latest_skin_conditions(user, limit=3):
    """Pull condition names from the user's most recent skin analysis."""
    try:
        from image_analysis.models import AnalysisResult
        latest = (AnalysisResult.objects
                  .filter(user=user, analysis_type='skin')
                  .order_by('-created_at')
                  .first())
        if not latest or not isinstance(latest.conditions, list):
            return []
        out = []
        for c in latest.conditions[:limit]:
            if isinstance(c, dict) and c.get('name'):
                name = str(c['name']).strip()
                if name.lower() != 'normal':
                    out.append(name)
        return out
    except Exception as exc:
        logger.debug("Could not load latest skin conditions: %s", exc)
        return []


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def makeup_suggest(request):
    """
    POST /api/makeup/suggest/
    Body (multipart): image=<file>  event_type|occasion=...
    Returns: face_shape, skin_tone, undertone, conditions, suggestions dict
    """
    # Optional rate limit (settings.RATELIMIT_ENABLE)
    if getattr(settings, 'RATELIMIT_ENABLE', False):
        try:
            from django_ratelimit.core import is_ratelimited
            limited = is_ratelimited(request, group='makeup_suggest',
                                     key='user', rate='10/h', increment=True)
            if limited:
                return Response({'error': 'Rate limit exceeded — 10 makeup suggestions/hour.'},
                                status=429)
        except Exception:
            pass

    image = request.FILES.get('image')
    occasion = (
        request.data.get('occasion')
        or request.data.get('event_type')
        or 'everyday'
    )

    if not image:
        return Response({'error': 'Image is required.'}, status=400)

    allowed = {'image/jpeg', 'image/png', 'image/heic', 'image/heif'}
    if getattr(image, 'content_type', '') not in allowed:
        return Response({'error': 'Only JPG, PNG and HEIC images are supported.'}, status=400)

    if image.size > 10 * 1024 * 1024:
        return Response({'error': 'Image must be under 10MB.'}, status=400)

    # Require a visible human face (MediaPipe FaceMesh) before processing.
    from core.ai_models.upload_validation import has_face
    if not has_face(image):
        return Response(
            {'error': 'Please upload a clear photo with your face visible'},
            status=400,
        )

    # Save + analyse
    suggestion = MakeupSuggestion(user=request.user)
    suggestion.image.save(image.name, image, save=True)
    image_path = suggestion.image.path

    face_shape = detect_face_shape(image_path)
    tone_info  = detect_skin_tone_and_undertone(image_path)
    skin_tone  = tone_info['skin_tone']
    undertone  = tone_info['undertone']

    # Pull latest detected skin conditions to inform the LLM prompt.
    skin_conditions = _latest_skin_conditions(request.user)

    suggestions = get_makeup_suggestions(
        face_shape=face_shape,
        skin_tone=skin_tone,
        occasion=occasion,
        undertone=undertone,
        skin_conditions=skin_conditions,
    )

    suggestion.face_shape  = face_shape
    suggestion.skin_tone   = skin_tone
    suggestion.suggestions = suggestions
    suggestion.save()

    logger.info("Makeup suggestion for %s: %s / %s / %s",
                request.user.email, face_shape, skin_tone, undertone)

    return Response({
        'id':          suggestion.id,
        'face_shape':  face_shape,
        'skin_tone':   skin_tone,
        'undertone':   undertone,
        'occasion':    occasion,
        'active_conditions': skin_conditions,
        'suggestions': suggestions,
        'created_at':  suggestion.created_at,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def makeup_history(request):
    """GET /api/makeup/history/  — user's past makeup suggestions"""
    qs = MakeupSuggestion.objects.filter(user=request.user)
    data = [
        {
            'id':         s.id,
            'face_shape': s.face_shape,
            'skin_tone':  s.skin_tone,
            'suggestions': s.suggestions,
            'created_at': s.created_at,
        }
        for s in qs
    ]
    return Response(data)
