import os
import logging

from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import MakeupSuggestion
from .services import detect_face_shape, detect_skin_tone, get_makeup_suggestions

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def makeup_suggest(request):
    """
    POST /api/makeup/suggest/
    Body (multipart): image=<file>  occasion=everyday|evening|wedding|party
    Returns: face_shape, skin_tone, suggestions dict
    """
    image    = request.FILES.get('image')
    occasion = request.data.get('occasion', 'everyday')

    if not image:
        return Response({'error': 'Image is required.'}, status=400)

    # Validate file type
    allowed = {'image/jpeg', 'image/png', 'image/heic', 'image/heif'}
    if getattr(image, 'content_type', '') not in allowed:
        return Response({'error': 'Only JPG, PNG and HEIC images are supported.'}, status=400)

    if image.size > 10 * 1024 * 1024:
        return Response({'error': 'Image must be under 10MB.'}, status=400)

    # Save temporarily to run MediaPipe on it
    suggestion = MakeupSuggestion(user=request.user)
    suggestion.image.save(image.name, image, save=True)
    image_path = suggestion.image.path

    # Detect face shape + skin tone
    face_shape = detect_face_shape(image_path)
    skin_tone  = detect_skin_tone(image_path)

    # Get LLM suggestions
    suggestions = get_makeup_suggestions(face_shape, skin_tone, occasion)

    # Save results
    suggestion.face_shape  = face_shape
    suggestion.skin_tone   = skin_tone
    suggestion.suggestions = suggestions
    suggestion.save()

    logger.info("Makeup suggestion for user %s: %s / %s", request.user.email, face_shape, skin_tone)

    return Response({
        'id':          suggestion.id,
        'face_shape':  face_shape,
        'skin_tone':   skin_tone,
        'occasion':    occasion,
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
