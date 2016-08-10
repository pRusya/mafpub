from django.contrib import admin
from .models import *
from .forms import *


# Register your models here.

#admin.site.register(Game)
@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    def render_change_form(self, request, context, obj, *args, **kwargs):
        context['adminform'].form.fields['description'].initial = obj.get_description().text
        return super(GameAdmin, self).render_change_form(request, context, args, kwargs)

    form = CreateGameForm


admin.site.register(GameParticipant)
admin.site.register(GamePost)
admin.site.register(GameComment)
admin.site.register(Mask)
admin.site.register(Vote)
admin.site.register(User)
