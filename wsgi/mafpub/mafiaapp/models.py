# -*- coding: utf-8 -*-
from django.contrib.auth.models import User as U
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import ArrayField
from django import forms
from django.db import models
import time


# Create your models here.

def save_path(instance, filename):
    name, ext = filename.split('.')
    if hasattr(instance, 'game'):
        return 'MaskMedia/%s/avatar.%s' % (instance.username, ext)
    else:
        return 'UserMedia/%s/avatar.%s' % (instance.username, ext)


class User(U):
    avatar = models.ImageField(upload_to=save_path, blank=True)
    nickname = models.CharField(max_length=30, default='', unique=True)
    # number of received likes
    like = models.IntegerField(default=0)
    # list of comment id's user liked
    liked = ArrayField(models.IntegerField(), default='{}')
    comments_number = models.IntegerField(default=0)

    def __str__(self):
        return self.nickname


class EmailValidation(models.Model):
    email = models.EmailField(max_length=50)
    code = models.CharField(max_length=30)


class Game(models.Model):
    number = models.AutoField(primary_key=True)
    title = models.CharField(max_length=50, verbose_name='Заголовок')

    # states are
    #   'upcoming'  description and registration are available
    #               displayed under dashboard's 'Предстоящая игра' section
    #   'current'   registration not available. game is in progress
    #               displayed under dashboard's 'Текущая игра' section
    #   'past'      game is finished. no interaction available. read only
    #               displayed under dashboard's 'Прошедшие игры' section
    STATE_CHOICES = (
        ('upcoming',    'Регистрация'),
        ('current',     'В процессе'),
        ('past',        'Завершена'),
    )
    state = models.CharField(max_length=10, choices=STATE_CHOICES, default='upcoming', verbose_name='Фаза')

    # this is slug. used to navigate through list of past games
    short = models.CharField(max_length=50, verbose_name='URL')
    slug = models.SlugField(verbose_name='slug URL', default=time.time())
    # current day
    day = models.IntegerField(default=0, blank=True, verbose_name='День')
    # custom string to display more info
    status = models.CharField(max_length=100, null=True, verbose_name='Статус')
    # choose leader form not avail if True
    hasHeadMafia = models.BooleanField(default=False, verbose_name='ГлавМаф назначен')
    # recruit form not avail if True
    hasRecruit = models.BooleanField(default=False, verbose_name='Есть завербованный')
    anchor = ArrayField(models.CharField(max_length=30, unique=True), verbose_name='Ведущие')

    def __str__(self):
        return self.title + '(id=' + str(self.number) + '). Фаза: ' + \
               ('Регистрация' if self.state == 'upcoming' else 'В процессе' if self.state == 'current' else 'Завершена')


class Mask(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    avatar = models.ImageField(upload_to=save_path)
    taken = models.BooleanField(default=False)
    username = models.CharField(max_length=50)

    def __str__(self):
        return self.username


class GameParticipant(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    mask = models.ForeignKey(Mask, on_delete=models.CASCADE, null=True)
    comments_number = models.IntegerField(default=0)

    # roles are ['mafia', 'head mafia', 'mafia doctor', 'mafia barman', 'mafia killer', 'mafia recruit',
    #            'militia', 'head militia', 'militia doctor', 'militia barman', 'militia killer', 'militia recruit',
    #            'neutral doctor', 'neutral barman', 'neutral killer',
    #            'maniac',
    #            'peaceful',
    #            'dead']
    role = models.CharField(max_length=20)

    # used to store the last doctor's or barman's target to filter it out from next day's available targets
    prevTarget = models.ForeignKey('self', on_delete=models.CASCADE, null=True)
    # if True, killer's 'contract form' displayed in private quarters
    # contract target cannot be changed. use this bool rather then query db for existing vote
    can_ask_killer = models.BooleanField(default=True)
    # if True, 'choose side' form displayed in private quarters
    # True, if 'recruit' vote's target is this participant or role in ['neutral barman', 'neutral killer']
    can_choose_side = models.BooleanField(default=False)
    # can see mafia quarters
    sees_maf_q = models.BooleanField(default=False)
    # can see militia quarters
    sees_mil_q = models.BooleanField(default=False)
    # if True, head mafia can recruit
    # True, if game.hasRecruit == False and there is no vote with action == 'recruit' and day == game.day
    can_recruit = models.BooleanField(default=False)
    # participant was checked by militia or head militia
    checked_by_mil = models.BooleanField(default=False)

    def __str__(self):
        return str(self.user)+' as '+str(self.mask)


class Post(models.Model):
    title = models.CharField(max_length=100)
    text = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    tags = ArrayField(models.CharField(max_length=20))
    short = models.CharField(max_length=50)
    slug = models.SlugField(verbose_name='slug URL', default=time.time())
    allow_comment = models.BooleanField(default=True)


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    text = models.TextField
    date = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    like = models.IntegerField(default=0)


class GamePost(models.Model):
    title = models.CharField(max_length=100, verbose_name='Заголовок')
    text = models.TextField(verbose_name='Содержание')
    date = models.DateTimeField(auto_now_add=True)
    game = models.ForeignKey(Game, on_delete=models.CASCADE, verbose_name='Игра')

    # tags are
    #   'general'   used by filter_tag under game's 'Общая информация' section
    #   'day'       used by filter_tag under game's 'Игровые дни' section
    #   'description'   game's description post
    #   'summary'   game's nights' summary
    #   'morgue'    post for game participants with role 'dead'
    #   'current'   used by filter_tag to show comment form
    #   'mafia'     post displayed only in mafia quarters
    #   'militia'   post displayed only in militia quarters
    #   'private'   post for game participant's private quarter. used both with <User.username>
    #   <User.username>   post for game participant's private quarter. used both with 'private'
    TAGS_CHOICES = (
        ('general', 'general'),
        ('general_day', 'general_day'),
        ('mafia_day', 'mafia_day'),
        ('militia_day', 'militia_day'),
        ('mafia_secret', 'mafia_secret'),
        ('militia_secret', 'militia_secret'),
        ('private', 'private'),
        #('description', 'description'),
        #('summary', 'summary'),
        #('morgue', 'morgue'),
        ('current', 'current'),
        #('departure', 'departure'),
    )
    tags = ArrayField(models.CharField(max_length=20), verbose_name='Тэги(без пробелов, через запятую)')

    short = models.CharField(max_length=50, verbose_name='URL')
    slug = models.SlugField(verbose_name='slug URL', default=time.time())
    allow_comment = models.BooleanField(default=True)
    ALLOW_ROLE_CHOICES = (
        ('mafia_core',      'mafia_core'),
        ('mafia_recruit',   'mafia_recruit'),
        ('militia_core',    'militia_core'),
        ('militia_recruit', 'militia_recruit'),
        ('everyone',    'everyone'),
        ('private',     'private'),
        ('dead',        'dead'),
    )
    allow_role = ArrayField(models.CharField(max_length=20))
    # author can be either User or Mask, so make relation dynamically
    # content_type = models.ForeignKey(ContentType)
    # object_id = models.PositiveIntegerField()
    # author = GenericForeignKey('content_type', 'object_id')
    author = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.title

    def get_mask(self):
        participant = GameParticipant.objects.get(game=self.game, user=self.author)
        return participant.mask


class GameComment(models.Model):
    post = models.ForeignKey(GamePost, on_delete=models.CASCADE)
    text = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    # author can be either User or Mask, so make relation dynamically
    # content_type = models.ForeignKey(ContentType)
    # object_id = models.PositiveIntegerField()
    # author = GenericForeignKey('content_type', 'object_id')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    like = models.IntegerField(default=0)
    mask = models.ForeignKey(Mask, on_delete=models.CASCADE, null=True)

    def __str__(self):
        return self.text


class Vote(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    day = models.IntegerField()
    voter = models.ForeignKey(GameParticipant, on_delete=models.CASCADE, related_name='voter')
    # actions are
    #   hang    any voter who's role != 'dead'. used to change role to 'dead' of the most targeted target
    #   leader  any voter who's role == 'mafia'. used to change role to 'head mafia' of the most targeted target
    #   shoot   any voter who's role in ['head mafia', 'neutral killer', 'mafia killer', 'militia killer', 'maniac'].
    #           used to change role to 'dead' of the target
    #   check   any voter who's role in ['head mafia', 'head militia', 'militia', 'maniac']
    #   heal    any voter who's role in ['neutral doctor', 'mafia doctor', 'militia doctor']. provides immunity against
    #           'shoot' action on target
    #   spoil   any voter who's role in ['neutral barman', 'mafia barman', 'militia barman']. decline any action in
    #           ['shoot', 'heal', 'check']
    #   mafia_side      changes 'neutral' role to 'mafia', 'peaceful' -> 'mafia recruit'
    #   militia_side    changes 'neutral' role to 'militia', 'peaceful' -> 'militia recruit'
    #   recruit any voter who's role == 'head mafia'. used to change role to 'mafia recruit' of the target.
    #           game participant can accept it, decline or take 'militia recruit' role.
    #           any target with role != 'peaceful' automatically declines recruit
    #   contract    any voter who's role not in ['dead', 'neutral killer', 'mafia killer', 'militia killer'].
    #               contract targets are killer's shoot_targets
    action = models.CharField(max_length=20, null=True)
    target = models.ForeignKey(GameParticipant, on_delete=models.CASCADE, related_name='target', null=True)
    date = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        d = {
            'hang': ' решает вешать игрока ',
            'leader': ' выбирает главой игрока ',
            'shoot': ' решает стрелять в игрока ',
            'check': ' решает проверить игрока ',
            'heal': ' решает лечить игрока ',
            'spoil': ' решает спаивать игрока ',
            'mafia_side': ' выбирает сторону мафии. Ночью произойдет смена роли игрока ',
            'militia_side': ' выбирает сторону милиции. Ночью произойдет смена роли игрока ',
            'recruit': ' пробует вербовать игрока ',
            'contract': ' заказывает убийство игрока ',
        }
        return 'День '+str(self.day)+': '+str(self.voter.mask)+d[self.action]+str(self.target.mask)