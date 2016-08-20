from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth import authenticate, login, logout, get_user
from django.contrib.admin.forms import AdminAuthenticationForm
from .forms import *
from .views import register_bots, DisplayGamePost
import random
import string
import itertools
import functools
import operator

"""
Test

+create game bot, create superuser
+create game
+register bots
+create departure
+assign roles
+new day
-generate possible votes
    create votes
    new day
    save results for analysis

"""


class IndexViewTestCase(TestCase):
    def test_index(self):
        resp = self.client.get(reverse('mafiaapp:index'))
        self.assertEqual(resp.status_code, 200)
        print('     IndexViewTestCase       OK')


def create_superuser(self):
    email = 'admin@maf.pub'
    code = "".join([random.SystemRandom().choice(string.hexdigits) for n in range(30)])
    ev = EmailValidation(email=email, code=code)
    ev.save()
    self.assertEqual(ev.email, email)
    print('         create email validation       OK')

    form_data = {'nickname': 'admin', 'password1': '123', 'password2': '123', 'email': email}
    form = UserCreateForm(data=form_data)
    self.assertTrue(form.is_valid())
    user = form.save()
    user.is_staff = True
    user.is_superuser = True
    user.save()
    self.assertTrue(user.is_superuser)
    print('         register user    %s        OK' % user)


def create_game_bot(self):
    form_data = {'nickname': 'Игровой Бот', 'password1': '123', 'password2': '123', 'email': 'bot@maf.pub'}
    form = UserCreateForm(data=form_data)
    self.assertTrue(form.is_valid())
    bot = form.save()
    self.assertEqual(str(bot), 'Игровой Бот')
    print('         register user    %s  OK' % bot)


def create_game(self):
    user = authenticate(username='admin', password='123')
    if user is not None:
        print('             auth user', user)
        self.client.login(username=user.username, password='123')

    create_game_url = reverse('mafiaapp:create_game')
    resp = self.client.get(create_game_url, follow=True)
    self.assertEqual(resp.status_code, 200)

    form = AdminAuthenticationForm(data={'username': 'admin', 'password': '123'})
    self.assertTrue(form.is_valid())
    resp = self.client.post(create_game_url, {'form': form}, follow=True)
    self.assertEqual(resp.status_code, 200)

    data = {'status': ['registration'], 'slug': ['game6'], 'day': ['0'], 'anchor': ['Игровой Бот', 'Русич'],
            'description': ['Тестовая Игрa I'], 'title': ['Тестовая Игрa I'], 'state': ['upcoming']}
    resp = self.client.post(create_game_url, data, follow=True)
    game = Game.objects.first()
    self.assertEqual(resp.context['game_list'][0], game)
    print('             game', game)
    print('         create game                   OK')


def wrap_register_bots(self):
    game = Game.objects.first()
    register_bots({'game': game.number, 'number': 9})
    participants = GameParticipant.objects.filter(game=game)
    self.assertEqual(len(participants), 10)
    print('         register bots                 OK')


def create_departure(self):
    game = Game.objects.first()
    create_game_post_url = reverse('mafiaapp:create_game_post')
    resp = self.client.get(create_game_post_url, follow=True)
    self.assertEqual(resp.status_code, 200)

    data = {'title': ['Зал Ожидания'], 'text': ['Зал Ожидания'], 'game': [game.number], 'short': ['departure'],
            'tags': ['general_day', 'current'], 'slug': ['game1_departure'], 'allow_role': ['everyone']}
    resp = self.client.post(create_game_post_url, data, follow=True)
    self.assertEqual(resp.status_code, 200)

    game_posts = GamePost.objects.filter(game=game, tags__contains=['general_day'])
    print('             general days', game_posts)
    print('         create departure              OK')


def assign_roles(self):
    game = Game.objects.first()
    edit_game_url = reverse('mafiaapp:edit_game', kwargs={'pk': game.number})
    resp = self.client.get(edit_game_url, follow=True)
    self.assertEqual(resp.status_code, 200)

    """
    data = {'action': ['Назначить'], 'game': [game.number]}
    resp = self.client.post(edit_game_url, data, follow=True)
    self.assertEqual(resp.status_code, 200)

    for p in participants:
        print('             %s  %s' % (p, p.role))
    """
    participants = GameParticipant.objects.filter(game=game).exclude(user__nickname='Игровой Бот')
    roles = ['head militia', 'militia',
             'neutral doctor', 'neutral barman', 'neutral killer',
             'maniac',
             'head mafia', 'mafia',
             'peaceful']
    for i, p in enumerate(participants):
        p.role = roles[i]
        if p.role in ['neutral barman', 'neutral killer', 'neutral doctor']:
            p.can_choose_side = True
        if p.role in ['militia', 'head militia']:
            p.sees_mil_q = True
        if p.role in ['mafia', 'head mafia']:
            p.sees_maf_q = True
        if p.role == 'neutral killer':
            p.can_ask_killer = False
        p.save()
    print('         assign roles                  OK')


def new_day(self):
    game = Game.objects.first()
    day = game.day
    game_posts_number = len(GamePost.objects.filter(game=game, tags__contains=['general_day']))
    edit_game_url = reverse('mafiaapp:edit_game', kwargs={'pk': game.number})
    resp = self.client.get(edit_game_url, follow=True)
    self.assertEqual(resp.status_code, 200)

    data = {'action': ['Новый день'], 'game': [game.number]}
    resp = self.client.post(edit_game_url, data, follow=True)
    self.assertEqual(resp.status_code, 200)

    game = Game.objects.first()
    print('             game day', game.day)
    self.assertEqual(game.day, day + 1)
    game_posts = GamePost.objects.filter(game=game, tags__contains=['general_day'])
    print('             general days', game_posts)
    self.assertEqual(len(game_posts), game_posts_number + 1)
    print('         end day, night, new day       OK')


def generate_possible_votes(self):
    game = Game.objects.first()
    participants = GameParticipant.objects.filter(game=game).exclude(user__nickname='Игровой Бот')
    heal_targets = list(participants)  # []
    spoil_targets = list(participants)  # []
    head_militia_check_targets = list(participants)  # []
    head_mafia_shoot_targets = list(participants)  # []
    killer_targets = list(participants)  # []
    maniac_targets = list(participants)  # []
    peaceful_hang_targets = list(participants)  # []

    iters = [heal_targets, spoil_targets, head_militia_check_targets,
        head_mafia_shoot_targets, killer_targets, maniac_targets, peaceful_hang_targets]
    f = functools.reduce(operator.mul, map(len, iters), 1)
    print('             map reduce targets', f)

    combinations = itertools.islice(itertools.product(heal_targets, spoil_targets, head_militia_check_targets,
        head_mafia_shoot_targets, killer_targets, maniac_targets, peaceful_hang_targets), 4782965, 4782969)
    print('     len comb\n', '\n'.join(str(x) for x in list(combinations)))
    """
    for p in participants:
        private_q_url = reverse('mafiaapp:display_game_post', kwargs={'game_slug': game.slug,
                                                                      'post_slug': game.slug + '_private_' +
                                                                                   p.user.username})
        print('             %s  %s' % (p, p.role))
        print('                 url', private_q_url)
        resp = self.client.get(private_q_url)
        self.assertEqual(resp.status_code, 404)

        user = authenticate(username=p.user.username, password='123')
        if user is not None:
            print('                 auth user', user)
            self.client.login(username=p.user.username, password='123')
        resp = self.client.get(private_q_url)
        print('                 GET url status code', resp.status_code)
        print('                 can_hang', resp.context['can_hang'])
        self.assertTrue(resp.context['can_hang'])
        self.game = game
        allowed_action = DisplayGamePost.allowed_actions(self, p.user)
        #print('                 allowed actions\n', allowed_action)
        if p.role == 'neutral doctor':
            heal_targets = allowed_action['heal_targets']
            print('                 heal_targets\n', heal_targets)
        elif p.role == 'neutral barman':
            spoil_targets = allowed_action['spoil_targets']
            print('                 spoil_targets\n', spoil_targets)
        elif p.role == 'neutral killer':
            killer_targets = allowed_action['participants']
            print('                 killer_targets\n', killer_targets)
        elif p.role == 'head militia':
            head_militia_check_targets = allowed_action['check_targets']
            print('                 head_militia_check_targets\n', head_militia_check_targets)
        elif p.role == 'head mafia':
            head_mafia_shoot_targets = allowed_action['shoot_targets']
            print('                 head_mafia_shoot_targets\n', head_mafia_shoot_targets)
        elif p.role == 'maniac':
            maniac_targets = allowed_action['shoot_targets']
            print('                 maniac_targets\n', maniac_targets)
        elif p.role == 'peaceful':
            peaceful_hang_targets = allowed_action['participants']
            print('                 peaceful_hang_targets\n', peaceful_hang_targets)
        print('---------------------------------------------------')
        self.client.logout()
    comb = list(itertools.product(heal_targets, spoil_targets))
    print('                 combinations', len(comb))
    for c in comb:
       print('                 ', c)
    """

    print('         generate possible votes       OK')


class GameTestCase(TestCase):
    def test_game(self):
        print('\n     GameTestCase        start')
        create_superuser(self)
        create_game_bot(self)
        create_game(self)
        wrap_register_bots(self)
        create_departure(self)
        assign_roles(self)
        new_day(self)
        generate_possible_votes(self)
        print('     GameTestCase        OK\n')
