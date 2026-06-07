from django.core.mail import send_mail
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from providers.models import Provider
from .models import Booking
from .serializers import BookingSerializer


def _rate_limited(request, group, rate='10/h'):
    """Return True if the user has exceeded `rate` for this `group`."""
    if not getattr(settings, 'RATELIMIT_ENABLE', False):
        return False
    try:
        from django_ratelimit.core import is_ratelimited
        return is_ratelimited(request, group=group, key='user',
                              rate=rate, increment=True)
    except Exception:
        return False


def _resolve_provider(request):
    """
    Returns a (Provider | None, error_dict | None) tuple.

    Bookings can come from two sources:
      • Internal directory  → request.data['provider'] is an int pk.
      • Google Places result → request.data['google_place'] is a dict.
        In that case we get_or_create a Provider row so the FK works.
    """
    raw_provider = request.data.get('provider')

    # Case 1 — internal Provider pk
    if raw_provider not in (None, '', 'null'):
        try:
            pk = int(raw_provider)
            return Provider.objects.get(pk=pk), None
        except (ValueError, TypeError):
            # Not an int → fall through and try the Google-Place branch
            pass
        except Provider.DoesNotExist:
            return None, {'provider': 'Provider not found.'}

    # Case 2 — Google Place payload
    gp = request.data.get('google_place') or {}
    if gp and gp.get('name'):
        provider_type = (request.data.get('provider_type')
                         or gp.get('provider_type')
                         or 'dermatologist')
        if provider_type not in {'dermatologist', 'salon', 'clinic'}:
            provider_type = 'dermatologist'

        # Dedup by name + lat/lng if available, otherwise by name + address.
        lookup = {'name': gp.get('name')[:200]}
        if gp.get('lat') and gp.get('lng'):
            lookup['latitude']  = float(gp['lat'])
            lookup['longitude'] = float(gp['lng'])

        defaults = {
            'provider_type': provider_type,
            'address':       gp.get('vicinity') or gp.get('address') or '',
            'city':          gp.get('city') or '',
            'phone':         gp.get('formatted_phone_number') or gp.get('phone') or '',
            'is_active':     True,
        }
        provider, _ = Provider.objects.get_or_create(defaults=defaults, **lookup)
        return provider, None

    return None, {'provider': 'A provider id or google_place payload is required.'}


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def bookings_list(request):
    """
    GET  /api/bookings/  — list user's bookings
    POST /api/bookings/  — create a new booking
    """
    if request.method == 'GET':
        status_filter = request.query_params.get('status')
        qs = Booking.objects.filter(user=request.user)
        if status_filter:
            qs = qs.filter(status=status_filter)
        return Response(BookingSerializer(qs, many=True).data)

    # Rate limit booking creation (10/h per user).
    if _rate_limited(request, 'booking_create', '10/h'):
        return Response({'error': 'Rate limit exceeded — 10 bookings/hour.'}, status=429)

    # POST — create booking. Resolve provider FK from either an internal pk
    # or a Google Places payload before running the serializer.
    provider, err = _resolve_provider(request)
    if err:
        return Response(err, status=400)

    # Inject the resolved pk so the serializer accepts it as a valid FK.
    payload = dict(request.data)
    payload['provider'] = provider.pk

    serializer = BookingSerializer(data=payload)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    booking = serializer.save(user=request.user)

    # Send confirmation email
    try:
        send_mail(
            subject='Booking Confirmed — AI Skin Assistant',
            message=(
                f'Hi {request.user.first_name or request.user.email},\n\n'
                f'Your appointment has been booked!\n\n'
                f'Provider : {booking.provider.name}\n'
                f'Type     : {booking.provider.get_provider_type_display()}\n'
                f'Address  : {booking.provider.address}, {booking.provider.city}\n'
                f'Date     : {booking.date}\n'
                f'Time     : {booking.time}\n'
                f'Notes    : {booking.notes or "None"}\n\n'
                f'You can cancel anytime from the app.\n\n'
                f'— AI Skin Assistant Team'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[request.user.email],
            fail_silently=True,
        )
    except Exception:
        pass  # Don't fail the booking if email fails

    return Response(BookingSerializer(booking).data, status=201)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def booking_detail(request, pk):
    """
    GET    /api/bookings/<id>/         — booking detail
    PATCH  /api/bookings/<id>/cancel/  — cancel booking
    DELETE /api/bookings/<id>/         — delete booking
    """
    try:
        booking = Booking.objects.get(pk=pk, user=request.user)
    except Booking.DoesNotExist:
        return Response({'error': 'Booking not found.'}, status=404)

    if request.method == 'GET':
        return Response(BookingSerializer(booking).data)

    if request.method == 'PATCH':
        if booking.status == 'cancelled':
            return Response({'error': 'Booking is already cancelled.'}, status=400)
        booking.status = 'cancelled'
        booking.save()
        return Response(BookingSerializer(booking).data)

    if request.method == 'DELETE':
        booking.delete()
        return Response({'message': 'Booking deleted.'})


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def cancel_booking(request, pk):
    """PATCH /api/bookings/<id>/cancel/"""
    try:
        booking = Booking.objects.get(pk=pk, user=request.user)
    except Booking.DoesNotExist:
        return Response({'error': 'Booking not found.'}, status=404)

    if booking.status == 'cancelled':
        return Response({'error': 'Already cancelled.'}, status=400)

    booking.status = 'cancelled'
    booking.save()
    return Response(BookingSerializer(booking).data)
