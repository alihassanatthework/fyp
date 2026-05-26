import logging

from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import FashionSuggestion
from .services import detect_body_type, get_fashion_suggestions
from makeup.services import detect_skin_tone  # reuse from makeup app

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def fashion_suggest(request):
    """
    POST /api/fashion/suggest/
    Body (multipart): image=<file>  event_type=casual|formal|wedding|party|business|outdoor|sports
    Returns: body_type, skin_tone, suggestions dict
    """
    image      = request.FILES.get('image')
    event_type = request.data.get('event_type', 'casual')

    valid_events = {'casual', 'formal', 'wedding', 'party', 'business', 'outdoor', 'sports'}
    if event_type not in valid_events:
        event_type = 'casual'

    if not image:
        return Response({'error': 'Image is required.'}, status=400)

    allowed = {'image/jpeg', 'image/png', 'image/heic', 'image/heif'}
    if getattr(image, 'content_type', '') not in allowed:
        return Response({'error': 'Only JPG, PNG and HEIC images are supported.'}, status=400)

    if image.size > 10 * 1024 * 1024:
        return Response({'error': 'Image must be under 10MB.'}, status=400)

    # Save image
    suggestion = FashionSuggestion(user=request.user, event_type=event_type)
    suggestion.image.save(image.name, image, save=True)
    image_path = suggestion.image.path

    # Detect body type + skin tone
    body_type = detect_body_type(image_path)
    skin_tone = detect_skin_tone(image_path)

    # Get LLM suggestions
    suggestions = get_fashion_suggestions(body_type, skin_tone, event_type)

    # Save results
    suggestion.body_type   = body_type
    suggestion.skin_tone   = skin_tone
    suggestion.suggestions = suggestions
    suggestion.save()

    logger.info("Fashion suggestion for user %s: %s / %s / %s",
                request.user.email, body_type, skin_tone, event_type)

    return Response({
        'id':          suggestion.id,
        'body_type':   body_type,
        'skin_tone':   skin_tone,
        'event_type':  event_type,
        'suggestions': suggestions,
        'created_at':  suggestion.created_at,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def fashion_history(request):
    """GET /api/fashion/history/  — user's past fashion suggestions"""
    qs = FashionSuggestion.objects.filter(user=request.user)
    data = [
        {
            'id':          s.id,
            'body_type':   s.body_type,
            'skin_tone':   s.skin_tone,
            'event_type':  s.event_type,
            'suggestions': s.suggestions,
            'created_at':  s.created_at,
        }
        for s in qs
    ]
    return Response(data)
