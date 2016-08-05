from rest_framework import serializers
from ..models import *


class GameSerializer(serializers.ModelSerializer):
    anchor = serializers.ListField(child=serializers.CharField(max_length=30, allow_blank=True))
    black_list = serializers.ListField(child=serializers.CharField(max_length=30, allow_blank=True))

    class Meta:
        model = Game
        fields = ['title', 'short', 'status', 'state', 'day', 'hasHeadMafia', 'hasRecruit', 'slug', 'anchor',
                  'black_list']
