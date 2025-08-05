from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Route, Building
from .serializers import RouteSerializer
from .utils import parse_building_from_code

@api_view(['GET'])
def get_route(request, room_code):
    try:
        route = Route.objects.get(room_code__iexact=room_code)
        serializer = RouteSerializer(route)
        return Response(serializer.data)
    except Route.DoesNotExist:
        return Response({'error': 'Маршрут не найден'}, status=404)

@api_view(['GET'])
def guess_building(request, room_code):
    code = parse_building_from_code(room_code)
    try:
        building = Building.objects.get(code=code)
        return Response({'building': building.name})
    except Building.DoesNotExist:
        return Response({'building': 'Главный корпус (север/центр)'})
