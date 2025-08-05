from rest_framework import serializers
from .models import Route, Step

class StepSerializer(serializers.ModelSerializer):
    class Meta:
        model = Step
        fields = ['step_number', 'description', 'image']

class RouteSerializer(serializers.ModelSerializer):
    steps = StepSerializer(many=True)

    class Meta:
        model = Route
        fields = ['room_code', 'floor', 'building', 'steps']
