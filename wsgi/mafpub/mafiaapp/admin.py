from django.contrib import admin
from .models import *
from .forms import *


# Register your models here.

#admin.site.register(Game)
@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    form = CreateGameForm


admin.site.register(GameParticipant)
admin.site.register(GamePost)
admin.site.register(GameComment)
admin.site.register(Mask)
admin.site.register(Vote)
admin.site.register(User)
