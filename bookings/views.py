from django.core.mail import send_mail
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Booking
from .serializers import BookingSerializer


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

    # POST — create booking
    serializer = BookingSerializer(data=request.data)
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
