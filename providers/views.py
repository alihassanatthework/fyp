import math
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Provider
from .serializers import ProviderSerializer


def _haversine_km(lat1, lon1, lat2, lon2):
    """Return distance in km between two GPS coordinates."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_providers(request):
    """
    GET /api/providers/
    Optional filters: ?type=dermatologist|salon|clinic  ?city=Lahore
    """
    qs    = Provider.objects.filter(is_active=True)
    ptype = request.query_params.get('type')
    city  = request.query_params.get('city')
    if ptype:
        qs = qs.filter(provider_type=ptype)
    if city:
        qs = qs.filter(city__icontains=city)
    return Response(ProviderSerializer(qs, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def nearby_providers(request):
    """
    GET /api/providers/nearby/?lat=31.5&lng=74.3&radius=10&type=dermatologist
    Returns providers within `radius` km (default 10 km).
    """
    try:
        lat    = float(request.query_params['lat'])
        lng    = float(request.query_params['lng'])
        radius = float(request.query_params.get('radius', 10))
    except (KeyError, ValueError):
        return Response({'error': 'lat and lng are required.'}, status=400)

    ptype = request.query_params.get('type')
    qs    = Provider.objects.filter(is_active=True, latitude__isnull=False, longitude__isnull=False)
    if ptype:
        qs = qs.filter(provider_type=ptype)

    results = []
    for p in qs:
        dist = _haversine_km(lat, lng, p.latitude, p.longitude)
        if dist <= radius:
            data = ProviderSerializer(p).data
            data['distance_km'] = round(dist, 2)
            results.append(data)

    results.sort(key=lambda x: x['distance_km'])
    return Response(results)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def provider_detail(request, pk):
    """GET /api/providers/<id>/"""
    try:
        provider = Provider.objects.get(pk=pk, is_active=True)
    except Provider.DoesNotExist:
        return Response({'error': 'Provider not found.'}, status=404)
    return Response(ProviderSerializer(provider).data)
