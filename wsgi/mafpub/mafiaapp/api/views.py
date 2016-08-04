from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from ..models import *
from .serializers import *


class GameListAPIView(ListAPIView):
    queryset = Game.objects.all().order_by('number')
    serializer_class = GameSerializer
    permission_classes = [AllowAny]
