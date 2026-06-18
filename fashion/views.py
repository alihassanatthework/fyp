import logging

from django.conf import settings
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import FashionSuggestion
from .services import (
    detect_body_type, get_fashion_suggestions, classify_body_type, EVENT_ALIASES,
)
from makeup.services import detect_skin_tone  # reuse from makeup app

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def fashion_suggest(request):
    """
    POST /api/fashion/suggest/
    Body (multipart):
        image=<file>
        event_type=<str>
        bust=<cm>  waist=<cm>  hip=<cm>     (optional — preferred path)
        body_type=<explicit pick>           (fallback when measurements missing)
        season=<spring|summer|autumn|winter|all-season>
    Returns: body_type, skin_tone, suggestions, etc.
    """
    if getattr(settings, 'RATELIMIT_ENABLE', False):
        try:
            from django_ratelimit.core import is_ratelimited
            limited = is_ratelimited(request, group='fashion_suggest',
                                     key='user', rate='10/h', increment=True)
            if limited:
                return Response({'error': 'Rate limit exceeded — 10 fashion suggestions/hour.'},
                                status=429)
        except Exception:
            pass

    image = request.FILES.get('image')

    raw_event = (request.data.get('event_type') or 'casual').lower().strip()
    event_normalised = EVENT_ALIASES.get(raw_event, 'casual')

    bust  = request.data.get('bust')
    waist = request.data.get('waist')
    hip   = request.data.get('hip')

    if not image:
        return Response({'error': 'Image is required.'}, status=400)

    allowed = {'image/jpeg', 'image/png', 'image/heic', 'image/heif'}
    if getattr(image, 'content_type', '') not in allowed:
        return Response({'error': 'Only JPG, PNG and HEIC images are supported.'}, status=400)

    if image.size > 10 * 1024 * 1024:
        return Response({'error': 'Image must be under 10MB.'}, status=400)

    # Require a full body in frame (MediaPipe Pose — shoulders, hips, knees,
    # ankles all detected) before processing.
    from core.ai_models.upload_validation import has_full_body
    if not has_full_body(image):
        return Response(
            {'error': 'Please upload a full-body photo for accurate fashion recommendations'},
            status=400,
        )

    # ── Body type resolution ──
    # 1. Explicit user choice wins (UI fallback selector).
    user_body_choice = request.data.get('body_type')
    body_type = detect_body_type(user_body_choice, bust=bust, waist=waist, hip=hip)

    # Save the image first so we can analyse the photo (skin tone + pose).
    suggestion = FashionSuggestion(user=request.user, event_type=event_normalised)
    suggestion.image.save(image.name, image, save=True)
    image_path = suggestion.image.path

    # 2. No choice and no measurements → estimate body type from the PHOTO
    #    using MediaPipe Pose (shoulder-vs-hip ratio).
    if body_type == 'Unknown' and not user_body_choice and not any([bust, waist, hip]):
        from .services import detect_body_type_from_pose
        body_type = detect_body_type_from_pose(image_path)
        # 3. Only if the photo ALSO can't determine it → ask the user.
        if body_type == 'Unknown':
            suggestion.delete()  # no orphan record
            return Response({
                'error': 'body_type_required',
                'message': 'Provide bust/waist/hip measurements (cm) OR pick a body_type explicitly.',
                'valid_body_types': ['Hourglass', 'Pear', 'Apple', 'Rectangle', 'Inverted Triangle'],
            }, status=400)

    skin_tone = detect_skin_tone(image_path)

    # Undertone (warm/cool/neutral) drives the colour palette — reuse the
    # makeup detector which already computes it from skin patches.
    undertone = 'neutral'
    try:
        from makeup.services import detect_skin_tone_and_undertone
        tone_info = detect_skin_tone_and_undertone(image_path)
        undertone = (tone_info or {}).get('undertone', 'neutral') or 'neutral'
    except Exception:
        undertone = 'neutral'

    measurements = {'bust': bust, 'waist': waist, 'hip': hip} if any([bust, waist, hip]) else None
    season = request.data.get('season') or 'all-season'
    gender = (request.data.get('gender') or 'female').strip().lower()
    if gender not in ('male', 'female'):
        gender = 'female'
    suggestions = get_fashion_suggestions(
        body_type=body_type,
        skin_tone=skin_tone,
        event_type=event_normalised,
        measurements=measurements,
        season=season,
        gender=gender,
        undertone=undertone,
    )

    suggestion.body_type   = body_type
    suggestion.skin_tone   = skin_tone
    suggestion.suggestions = suggestions
    suggestion.save()

    logger.info("Fashion suggestion for %s: %s / %s / %s",
                request.user.email, body_type, skin_tone, event_normalised)

    return Response({
        'id':           suggestion.id,
        'body_type':    body_type,
        'skin_tone':    skin_tone,
        'event_type':   event_normalised,
        'measurements': measurements,
        'season':       season,
        'suggestions':  suggestions,
        'created_at':   suggestion.created_at,
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
