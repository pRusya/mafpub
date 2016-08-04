from rest_framework import serializers
from ..models import *


class GameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Game
        fields = ['title', 'short', 'status', 'state', 'day', 'hasHeadMafia', 'hasRecruit', 'slug'
                  ]
