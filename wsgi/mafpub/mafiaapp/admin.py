from django.contrib import admin
from django.contrib.auth import get_user
from .models import *
from .forms import *


# Register your models here.

@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    def render_change_form(self, request, context, obj, *args, **kwargs):
        if obj:
            context['adminform'].form.fields['description'].initial = obj.get_description().text
        return super(GameAdmin, self).render_change_form(request, context, args, kwargs)

    def save_model(self, request, obj, form, change):
        obj.save()
        user = get_user(request)
        description, created = GamePost.objects.get_or_create(game=obj, tags__contains=['description'],
                                                              defaults={
                                                                  "title": "Регистрация",
                                                                  "text": form.cleaned_data['description'],
                                                                  "game": obj,
                                                                  "tags": ["general", "description"],
                                                                  "short": "description",
                                                                  "slug": "game"+obj.slug+"_description",
                                                                  "allow_comment": True,
                                                                  "allow_role": ["everyone"],
                                                                  # user inherits default user. default user required
                                                                  "author": user.user
                                                              })
        if not created:
            description.text = form.cleaned_data['description']
            description.save()
        else:
            bot = User.objects.get(nickname='Игровой Бот')
            summary = GamePost(title='Итоги ночей', game=obj, text='Итоги обновляются каждую игровую ночь.',
                               author=bot, tags=['general', 'summary'], short='summary',
                               slug=obj.slug + '_summary', allow_comment=False, allow_role=['everyone'])
            summary.save()
            morgue = GamePost(title='Морг', game=obj, text='Здесь уют.',
                              author=bot, tags=['morgue'], short='morgue', slug=obj.slug + '_morgue',
                              allow_role=['dead'])
            morgue.save()
            bot_mask = Mask(game=obj, avatar=bot.avatar, username=bot.nickname)
            bot_mask.save()
            bot_participant = GameParticipant(game=obj, user=bot, mask=bot_mask)
            bot_participant.save()

    form = CreateGameForm


admin.site.register(GameParticipant)
admin.site.register(GamePost)
admin.site.register(GameComment)
admin.site.register(Post)
admin.site.register(Comment)
admin.site.register(Mask)
admin.site.register(Vote)
admin.site.register(User)
admin.site.register(Achievment)
