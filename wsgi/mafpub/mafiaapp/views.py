import time
import random
import string
from threading import Timer
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user
from django.contrib.auth.models import AnonymousUser
from django.core.mail import send_mail
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.urlresolvers import reverse_lazy
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404, redirect
from django.shortcuts import render
from django.views import generic
from django.http import Http404
from .forms import *
from .models import User as mafpub_user
from django.contrib.auth.decorators import login_required


class IndexView(generic.ListView):
    template_name = 'mafiaapp/index.html'

    def get_queryset(self):
        return None

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated():
            return redirect('mafiaapp:dashboard')
        else:
            return render(request, 'mafiaapp/index.html')

    def post(self, request):
        action = request.POST.get('submit', '')
        if action == 'Логин':
            form = LoginForm(request.POST)
            if form.is_valid():
                nickname = form.cleaned_data['nickname']
                user = get_object_or_404(mafpub_user, nickname__iexact=nickname)
                password = form.cleaned_data['password']
                user = authenticate(username=user.username, password=password)
                if user is not None:
                    login(request, user)
                    return redirect('mafiaapp:dashboard')
                else:
                    messages.add_message(request, messages.ERROR, 'Check your login credentials!')
                    return render(request, 'mafiaapp/index.html', {'form': form})
        elif action == 'Регистрация':
            form = EmailValidationForm(request.POST)
            if form.is_valid():
                email = request.POST['email']
                code = "".join([random.SystemRandom().choice(string.hexdigits) for n in range(30)])
                ev = EmailValidation(email=email, code=code)
                ev.save()
                email_body = 'На форуме Галамафия 2.0 (http://www.maf.pub/) появилась регистрационная ' \
                             'запись,\r' \
                             'в которой был указал ваш электронный адрес (e-mail).\r' \
                             '\r' \
                             'Если вы не понимаете, о чем идет речь — просто проигнорируйте это сообщение!\r' \
                             '\r' \
                             'Если же именно вы решили зарегистрироваться на форуме Галамафия 2.0,\r' \
                             'то вам следует завершить свою регистрацию и тем самым активировать вашу ' \
                             'учетную запись.\r' \
                             'Регистрация производится один раз и необходима для повышения безопасности форума и ' \
                             'защиты его от злоумышленников.\r' \
                             'Чтобы завершить регистрацию и активировать вашу учетную запись, необходимо перейти ' \
                             'по ссылке:\r' \
                             'http://www.maf.pub/register/%s\r' \
                             'После активации учетной записи вы сможете войти в форум, используя выбранные вами ' \
                             'имя пользователя (login) и пароль.\r' \
                             '\r' \
                             'С этого момента вы сможете оставлять сообщения.\r' \
                             '\r' \
                             'Благодарим за регистрацию!'
                send_mail('Галамафия 2.0: Регистрация учетной записи', email_body % code, 'Галамафия 2.0 <noreply@maf.pub>',
                          [email], fail_silently=False)
                messages.add_message(request, messages.INFO, 'Check your email box to finish registration')
                return redirect('mafiaapp:index')
            else:
                messages.add_message(request, messages.ERROR, 'Provide valid e-mail!111')
                return redirect('mafiaapp:index')
        else:
            messages.add_message(request, messages.ERROR, 'Something went really bad!')
            return redirect('mafiaapp:index')


class RegisterView(generic.CreateView):
    model = User
    success_url = '/'
    template_name = 'mafiaapp/register_user.html'
    form_class = UserCreateForm

    def get_initial(self):
        email = get_object_or_404(EmailValidation, code=self.kwargs['code'])
        messages.add_message(self.request, messages.INFO, 'Registration successful. You may now login using your '
                                                          'credentials')
        return {'email': email.email}


class DisplayUsersView(generic.ListView):
    template_name = 'mafiaapp/display_users.html'
    context_object_name = 'users_list'

    def get_queryset(self):
        return User.objects.all()


class DisplayMasksView(generic.ListView):
    template_name = 'mafiaapp/display_masks.html'
    context_object_name = 'masks_list'

    def get_queryset(self):
        return Mask.objects.all()


class DeleteUser(generic.DeleteView):
    model = User
    success_url = '/users/'


class Dashboard(generic.ListView):
    template_name = 'mafiaapp/dashboard.html'
    model = Game


class Logout(generic.View):
    def get(self, request):
        logout(request)
        messages.add_message(request, messages.INFO, 'Logout performed')
        return redirect('mafiaapp:index')


class CreateGame(generic.CreateView):
    model = Game
    form_class = CreateGameForm
    success_url = '/dashboard/'
    template_name = 'mafiaapp/create_game.html'

    def form_valid(self, form):
        self.object = form.save()
        user = User.objects.get(username=self.request.user)
        bot = User.objects.get(nickname='Игровой Бот')
        description = GamePost(title='Описание', game=self.object, text=self.request.POST['description'], author=user,
                               tags=['general', 'description'], short='description',
                               slug=self.object.slug+'_description', allow_role=['everyone'])
        description.save()
        summary = GamePost(title='Итоги ночей', game=self.object, text='Итоги обновляются каждую игровую ночь.',
                           author=bot, tags=['general', 'summary'], short='summary', slug=self.object.slug+'_summary',
                           allow_comment=False, allow_role=['everyone'])
        summary.save()
        morgue = GamePost(title='Морг', game=self.object, text='Здесь уют.',
                          author=bot, tags=['morgue'], short='morgue', slug=self.object.slug+'_morgue',
                          allow_role=['dead'])
        morgue.save()
        bot_mask = Mask(game=self.object, avatar=bot.avatar, username=bot.nickname)
        bot_mask.save()
        bot_participant = GameParticipant(game=self.object, user=bot, mask=bot_mask)
        bot_participant.save()
        return redirect(self.success_url)


class CreateGamePost(generic.CreateView):
    model = GamePost
    form_class = CreateGamePostForm
    success_url = '/dashboard/'
    template_name = 'mafiaapp/create_game_post.html'

    def form_valid(self, form):
        bot = User.objects.get(nickname='Игровой Бот')
        fcd = form.cleaned_data
        print('     fcd', fcd)
        post = GamePost(title=fcd['title'], game=fcd['game'], text=self.request.POST['text'], author=bot,
                        tags=fcd['tags'], short=fcd['short'], slug=fcd['slug'], allow_role=fcd['allow_role'])
        post.save()
        if 'general_day' in fcd['tags'] and fcd['game'].day > 0:
            mafia_day = GamePost(title=fcd['title'], game=fcd['game'], text=self.request.POST['text'], author=bot,
                                 tags=fcd['tags'] + ['mafia'], short=fcd['short'], slug=fcd['slug'] + '_mafia',
                                 allow_role=fcd['allow_role'] + ['mafia'])
            mafia_day.save()
            militia_day = GamePost(title=fcd['title'], game=fcd['game'], text=self.request.POST['text'], author=bot,
                                   tags=fcd['tags'] + ['militia'], short=fcd['short'], slug=fcd['slug'] + '_militia',
                                   allow_role=fcd['allow_role'] + ['militia'])
            militia_day.save()
        return redirect(self.success_url)
    
    def post(self, request, *args, **kwargs):
        self.object = None
        print('     POST', request.POST)
        return super(CreateGamePost, self).post(request, *args, **kwargs)


class CreateGameMask(generic.CreateView):
    model = Mask
    form_class = CreateGameMaskForm
    success_url = '/dashboard/creategamemask/'
    template_name = 'mafiaapp/create_game_mask.html'


class DeleteGameView(generic.DeleteView):
    model = Game
    success_url = '/dashboard/games/'


class DeleteGameComment(generic.DeleteView):
    model = GameComment

    def get_success_url(self):
        return reverse_lazy('mafiaapp:display_game_post', kwargs={'game_slug': self.kwargs.get('game_slug', ''),
                                                                  'post_slug': self.kwargs.get('post_slug', '')})


class EditGameView(generic.ListView, generic.edit.UpdateView):
    model = Game
    template_name = 'mafiaapp/edit_game.html'
    form_class = CreateGameForm

    def get_object(self, queryset=None):
        game = get_object_or_404(Game, number=self.kwargs['pk'])
        return game  # Game.objects.get(number=self.kwargs['pk'])

    def get_queryset(self):
        game = get_object_or_404(Game, number=self.kwargs['pk'])
        return game  # Game.objects.get(number=self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        game = kwargs.pop('object_list', self.object_list)
        participants = GameParticipant.objects.filter(game=game).exclude(user__nickname='Игровой Бот')
        masks = Mask.objects.filter(game=game).exclude(username='Игровой Бот')
        description = GamePost.objects.get(game=game, tags__contains=['description'])
        users = mafpub_user.objects.all()
        context = {
            'paginator': None,
            'page_obj': None,
            'is_paginated': False,
            'game': game,
            'participants': participants,
            'masks': masks,
            'description': description,
            'users': users,
        }
        return context

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        context = self.get_context_data()
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        self.object = self.get_object()
        context = self.get_context_data()
        action = request.POST.get('action', '')
        if action == 'Назначить':
            participants = random.sample(list(context['participants']), len(context['participants']))
            masks = random.sample(list(context['masks']), len(context['masks']))
            roles = ['head militia', 'neutral doctor', 'neutral barman', 'maniac']
            mafia = ['mafia']
            killer = ['neutral killer']
            militia = ['militia']
            if len(participants) >= 15:
                roles = roles + killer
            if len(participants) >= 12:
                roles = roles + militia
            if len(participants) <= 18:
                roles = roles + mafia * 3
            elif 19 <= len(participants) <= 25:
                roles = roles + mafia * 4
            elif len(participants) > 25:
                roles = roles + mafia * 6
            peaceful = ['peaceful'] * (len(participants) - len(roles))
            roles = roles + peaceful
            roles = random.sample(roles, len(roles))
            bot = User.objects.get(nickname='Игровой Бот')
            for participant in participants:
                if not participant.mask:
                    participant.mask = masks.pop()
                participant.role = roles.pop()
                if participant.role in ['neutral barman', 'neutral killer', 'neutral doctor']:
                    participant.can_choose_side = True
                if participant.role in ['militia', 'head militia']:
                    participant.sees_mil_q = True
                if participant.role in ['mafia', 'head mafia']:
                    participant.sees_maf_q = True
                if participant.role == 'neutral killer':
                    participant.can_ask_killer = False
                participant.save()
                post = GamePost.objects.get(game=context['game'], tags__contains=['private', participant.user.nickname])
                inform = GameComment(post=post, author=bot, text=roles_description[participant.role])
                inform.save()
        elif action == 'Сохранить':
            form = self.get_form()
            if form.is_valid():
                context['game'] = form.save()
                description = GamePost.objects.get(game=context['game'], tags__contains=['description'])
                description.text = request.POST['description']
                if context['game'].state != 'upcoming':
                    description.allow_comment = False
                description.save()
                context['description'] = description
            else:
                context['form'] = form
        elif action == 'Изменить':
            participant = GameParticipant.objects.get(id=int(request.POST['id']))
            participant.role = request.POST['role']
            if participant.role in ['neutral barman', 'neutral killer', 'neutral doctor']:
                participant.can_choose_side = True
            elif participant.role in ['militia', 'head militia']:
                participant.sees_mil_q = True
            elif participant.role in ['mafia', 'head mafia']:
                participant.sees_maf_q = True
            elif participant.role == 'neutral killer':
                participant.can_ask_killer = False
            participant.save()
            context = self.get_context_data()
        elif action == 'Новый день':
            # t = Timer(1.0, night, args=(request.POST.dict(),))
            # t.start()
            night(request.POST.dict())
            context = self.get_context_data()
        elif action == 'Голосовать':
            simulate_vote(request.POST.dict())
            vote_hang(request.POST.dict())
        elif action == 'Зарегистрировать':
            register_bots(request.POST.dict())
        elif action == 'Флудить':
            simulate_flood(request.POST.dict())
        elif action == 'Создать':
            create_random_masks(request.POST.dict())
        return render(request, self.template_name, context)


def create_random_masks(d):
    game = Game.objects.get(number=d['game'])
    bot = Mask.objects.get(game=game, username='Игровой Бот')
    participants = GameParticipant.objects.exclude(mask=bot).filter(game=game, mask=None)
    for participant in participants:
        temp = NamedTemporaryFile()
        temp.write(urllib.request.urlopen('http://python-prusya.rhcloud.com/identicon/').read())
        temp.flush()

        mask = Mask(game=game, username='Маска ' + participant.user.nickname)
        mask.avatar.save(os.path.basename(save_path(mask, 'avatar.png')), File(temp))
        mask.save()

        participant.mask = mask
        participant.save()


def simulate_flood(d):
    game = Game.objects.get(number=d['game'])
    # bot = Mask.objects.get(game=game, username='Игровой Бот')
    mafia = GameParticipant.objects.filter(role__contains='mafia', game=game)
    militia = GameParticipant.objects.filter(role__contains='militia', game=game)
    if game.day > 0:
        mafia_post = GamePost.objects.get(game=game, tags__contains=['mafia_day', 'current'])
        militia_post = GamePost.objects.get(game=game, tags__contains=['militia_day', 'current'])
        for maf in mafia:
            comment = GameComment(post=mafia_post, text=flood[random.randint(0, len(flood) - 1)], author=maf.user)
            comment.save()
        for mil in militia:
            comment = GameComment(post=militia_post, text=flood[random.randint(0, len(flood) - 1)], author=mil.user)
            comment.save()
    participants = GameParticipant.objects.filter(game=game)
    post = GamePost.objects.exclude(Q(tags__contains=['mafia_day']) | Q(tags__contains=['militia_day'])) \
        .get(game=game, tags__contains=['general_day', 'current'])
    for participant in participants:
        comment = GameComment(post=post, text=flood[random.randint(0, len(flood) - 1)], author=participant.user,
                              mask=participant.mask)
        comment.save()


def register_bots(d):
    game = Game.objects.get(number=d['game'])
    if not d['number']:
        d['number'] = 1
    for x in range(0, int(d['number'])):
        available = False
        while not available:
            name = 'Бот ' + str(random.randint(1, 999999))
            available = False if User.objects.filter(nickname=name).first() else True
        user = User.objects.create_user(nickname=name, username=re.sub(r'[^\w.@+-]', '_', name), password='123')
        temp = NamedTemporaryFile()
        temp.write(urllib.request.urlopen('http://maf.pub/identicon/').read())
        temp.flush()
        user.avatar.save(os.path.basename(save_path(user, 'avatar.png')), File(temp))
        user.save()

        mask = Mask(game=game, username=user.nickname)
        mask.avatar.save(os.path.basename(save_path(mask, 'avatar.png')), File(temp))
        mask.save()

        participant = GameParticipant(game=game, user=user, mask=mask)
        participant.save()

        private_quarters = GamePost(title='Своя каюта', text='Каюта игрока %s' % user.nickname,
                                    game=game, tags=['private', user.nickname],
                                    short='private', author=user, slug=game.slug+'_private_'+user.username,
                                    allow_role=['private'])
        private_quarters.save()


def simulate_vote(d):
    game = Game.objects.get(number=d['game'])
    bot = Mask.objects.get(game=game, username='Игровой Бот')
    participants = GameParticipant.objects.exclude(mask=bot).filter(game=game)
    for participant in participants:
        target = random.choice(participants)
        Vote.objects.update_or_create(game=game, day=game.day, voter=participant, action='hang',
                                      defaults={'target': target})


def vote_hang(d):
    game = Game.objects.get(number=d['game'])
    participants = GameParticipant.objects.filter(game=game).exclude(Q(mask__username='Игровой Бот') | Q(role='dead'))
    # get longest mask username
    mask = Mask.objects.extra(select={'length': 'length(username)'}).order_by('-length').values('length').first()
    longest = mask['length']
    votes_result = 'Общее голосование:'
    for participant in participants:
        vote = Vote.objects.filter(game=game, day=game.day, voter=participant, action='hang').first()
        if vote:
            votes_result += '\n  ' + participant.mask.username + '.'*(longest-len(participant.mask.username)) + '.....' \
                           + vote.target.mask.username
        else:
            hang1 = Vote(game=game, day=game.day, voter=participant, action='hang', target=participant)
            hang1.save()
            hang2 = Vote(game=game, day=game.day, voter=participant, action='hang', target=participant)
            hang2.save()
            votes_result += '\n  ' + participant.mask.username + '.'*(longest-len(participant.mask.username)) \
                            + '.....Не голосовал'
    all_votes = Vote.objects.filter(game=game, day=game.day, action='hang')
    # there are no votes for current day, so everybody dies of space plague
    if not all_votes:
        for participant in participants:
            participant.role = 'dead'
            participant.save()
        return votes_result
    # get targets' ids and number of votes against them, sorted desc
    votes = Vote.objects.filter(game=game, day=game.day, action='hang').values('target').annotate(Count('target')) \
        .order_by('-target__count')
    # get targets with max votes among others. votes[0] has max votes
    departed = [p for p in votes if p['target__count'] == votes[0]['target__count']]
    hang_result = 'Ночь ' + str(
        game.day) + ': Вы были повешаны на общем голосовании. Можете оставить последнее сообщение.'
    success_result = '\n\nПовешаны:'
    bot = User.objects.get(nickname='Игровой Бот')
    for dead in departed:
        participant = GameParticipant.objects.get(id=dead['target'])
        # participant's quarters
        post = GamePost.objects.get(game=game, tags__contains=['private', participant.user.nickname])
        inform = GameComment(post=post, text=hang_result, author=bot)
        inform.save()
        participant.role = 'dead'
        participant.sees_maf_q = False
        participant.sees_mil_q = False
        participant.save()
        success_result += '\n  ' + participant.mask.username
    return votes_result + success_result


def doctor_heal(d):
    game = Game.objects.get(number=d['game'])
    doctor = GameParticipant.objects.filter(game=game, role__in=['neutral doctor', 'mafia doctor', 'militia doctor']) \
        .first()
    # there is no doctor:
    if not doctor:
        return ''
    heal_vote = Vote.objects.filter(game=game, day=game.day, voter=doctor, action='heal').first()
    # there is no action='heal' vote
    if not heal_vote:
        return ''
    # save barman's target to exclude it from next day
    doctor.prevTarget = heal_vote.target
    doctor.save()
    return ''


def barman_spoil(d):
    game = Game.objects.get(number=d['game'])
    barman = GameParticipant.objects.filter(game=game, role__in=['neutral barman', 'mafia barman', 'militia barman']) \
        .first()
    # there is no barman
    if not barman:
        return ''
    spoil_vote = Vote.objects.filter(game=game, day=game.day, voter=barman, action='spoil').first()
    # there is no action='spoil' vote
    if not spoil_vote:
        return ''
    # save barman's target to exclude it from next day
    barman.prevTraget = spoil_vote.target
    barman.save()
    # barman's quarters
    post = GamePost.objects.get(game=game, tags__contains=['private', barman.user.nickname])
    bot = User.objects.get(nickname='Игровой Бот')
    spoil_result = ''
    success_spoil = False
    # barman's target is dead
    if spoil_vote.target.role == 'dead':
        spoil_result = 'Ночь ' + str(
            game.day) + ': Вам не удалось напоить игрока ' + spoil_vote.target.mask.username + '.'
    else:
        spoil_result = 'Ночь ' + str(game.day) + ': Вам удалось напоить игрока ' + spoil_vote.target.mask.username + '.'
        # target's quarters
        target_post = GamePost.objects.get(game=game, tags__contains=['private', spoil_vote.target.user.nickname])
        target_spoil_result = 'Ночь ' + str(game.day) + ': Вы провели ночь в трактире.'
        target_inform = GameComment(post=target_post, text=target_spoil_result, author=bot)
        target_inform.save()
        success_spoil = True
    inform = GameComment(post=post, text=spoil_result, author=bot)
    inform.save()
    return '\n\nТрактирщик угощал:\n  ' + spoil_vote.target.mask.username if success_spoil else ''


def killer_kill(d):
    game = Game.objects.get(number=d['game'])
    killer = GameParticipant.objects.filter(game=game, role__in=['neutral killer', 'mafia killer', 'militia killer']) \
        .first()
    # there is no killer
    if not killer:
        return ''
    # killer's quarters
    post = GamePost.objects.get(game=game, tags__contains=['private', killer.user.nickname])
    bot = User.objects.get(nickname='Игровой Бот')
    shoot_result = ''
    success_shoot = False
    success_result = ''
    barman = GameParticipant.objects.filter(game=game, role__in=['neutral barman', 'mafia barman', 'militia barman']) \
        .first()
    spoil_vote = Vote.objects.filter(game=game, day=game.day, voter=barman, action='spoil').first() if barman else None
    # killer is drunk. no one dies
    if spoil_vote and spoil_vote.target == killer:
        return ''
    # killer is ok. get his target
    else:
        shoot_vote = Vote.objects.filter(game=game, day=game.day, voter=killer, action='shoot').first()
    doctor = GameParticipant.objects.filter(game=game, role__in=['neutral doctor', 'mafia doctor', 'militia doctor']) \
        .first()
    heal_vote = Vote.objects.filter(game=game, day=game.day, voter=doctor, action='heal').first() if doctor else None
    # perform kill
    # if killer's target is barman, then he kills barman's target first(if it's not dead already)
    if (shoot_vote and barman and shoot_vote.target == barman) and (spoil_vote and spoil_vote.target.role != 'dead'):
        # doctor saves both barman and barman's target
        if heal_vote and heal_vote.target == barman:
            success_result += '\n  ' + spoil_vote.target.mask.username + ' спасён доктором.'
        else:
            success_result += '\n    ' + spoil_vote.target.mask.username
            spoil_vote.target.role = 'dead'
            spoil_vote.target.save()
            shoot_result = ' Вы убили игрока ' + str(spoil_vote.target.mask.username) + '.'
            # barman's target quarters
            spoil_target_post = GamePost.objects.get(game=game, tags__contains=['private', spoil_vote.target.user.nickname])
            spoil_target_result = 'Ночь ' + str(game.day) + ': Вы были убиты в трактире киллером. ' \
                                                            'Можете оставить последнее сообщение.'
            spoil_target_inform = GameComment(post=spoil_target_post, text=spoil_target_result, author=bot)
            spoil_target_inform.save()
        success_shoot = True
    # killer's target is already dead
    if shoot_vote and shoot_vote.target.role == 'dead':
        shoot_result = 'Ночь ' + str(
            game.day) + ': Вам не удалось убить игрока ' + shoot_vote.target.mask.username + '.' + shoot_result
    # killer's target barman's target. no one dies
    elif spoil_vote and spoil_vote.target == shoot_vote.target:
        shoot_result = 'Ночь ' + str(
            game.day) + ': Вам не удалось убить игрока ' + shoot_vote.target.mask.username + '.' + shoot_result
    # killer's shoot target is doctor's target. doctor heals target.
    elif shoot_vote and heal_vote and heal_vote.target == shoot_vote.target:
        success_result += '\n  ' + shoot_vote.target.mask.username + ' спасён доктором.'
        success_shoot = True
        shoot_result = 'Ночь ' + str(
            game.day) + ': Вам не удалось убить игрока ' + shoot_vote.target.mask.username + '.' + shoot_result
        # killer's target quarters
        shoot_target_post = GamePost.objects.get(game=game, tags__contains=['private', shoot_vote.target.user.nickname])
        shoot_target_result = 'Ночь ' + str(game.day) + ': На вас совершил покушение киллер. Доктор спас вам жизнь.'
        shoot_target_inform = GameComment(post=shoot_target_post, text=shoot_target_result, author=bot)
        shoot_target_inform.save()
    elif shoot_vote:
        success_result = '\n  ' + shoot_vote.target.mask.username
        success_shoot = True
        shoot_vote.target.role = 'dead'
        shoot_vote.target.save()
        shoot_result = 'Ночь ' + str(game.day) + ': Вы убили игрока ' + shoot_vote.target.mask.username + '.' \
                       + shoot_result
        # killer's target quarters
        shoot_target_post = GamePost.objects.get(game=game, tags__contains=['private', shoot_vote.target.user.nickname])
        shoot_target_result = 'Ночь ' + str(game.day) + ': Вы были убиты киллером. Можете оставить последнее сообщение.'
        shoot_target_inform = GameComment(post=shoot_target_post, text=shoot_target_result, author=bot)
        shoot_target_inform.save()
    if shoot_vote:
        inform = GameComment(post=post, text=shoot_result, author=bot)
        inform.save()
    return '\n\nПокушение киллера:' + success_result if success_shoot else ''


def mafia_kill(d):
    game = Game.objects.get(number=d['game'])
    mafia = GameParticipant.objects.filter(game=game, role='head mafia') \
        .first()
    # there is no head mafia
    if not mafia:
        return ''
    # head mafia's quarters
    post = GamePost.objects.get(game=game, tags__contains=['private', mafia.user.nickname])
    bot = User.objects.get(nickname='Игровой Бот')
    shoot_result = ''
    success_result = ''
    success_shot = False
    barman = GameParticipant.objects.filter(game=game, role__in=['neutral barman', 'mafia barman', 'militia barman']) \
        .first()
    spoil_vote = Vote.objects.filter(game=game, day=game.day, voter=barman, action='spoil').first() if barman else None
    # head mafia is drunk. no one dies
    if spoil_vote and spoil_vote.target == mafia:
        return ''
    # head mafia is ok. get his target
    else:
        shoot_vote = Vote.objects.filter(game=game, day=game.day, voter=mafia, action='shoot').first()
    doctor = GameParticipant.objects.filter(game=game, role__in=['neutral doctor', 'mafia doctor', 'militia doctor']) \
        .first()
    heal_vote = Vote.objects.filter(game=game, day=game.day, voter=doctor, action='heal').first() if doctor else None
    # perform kill
    # if head mafia's target is barman, then he kills barman's target first(if it's not dead already)
    if (shoot_vote and barman and shoot_vote.target == barman) and (spoil_vote and spoil_vote.target.role != 'dead'):
        if heal_vote and heal_vote.target == barman:
            success_result += '\n  ' + spoil_vote.target.mask.username + 'спасён доктором.'
        else:
            success_result += '\n  ' + spoil_vote.target.mask.username
            spoil_vote.target.role = 'dead'
            spoil_vote.target.save()
            shoot_result = ' Вы убили игрока ' + str(spoil_vote.target.mask.username) + '.'
            # barman's target quarters
            spoil_target_post = GamePost.objects.get(game=game, tags__contains=['private', spoil_vote.target.user.nickname])
            spoil_target_result = 'Ночь ' + str(game.day) + ': Вы были убиты в трактире мафией. ' \
                                                            'Можете оставить последнее сообщение.'
            spoil_target_inform = GameComment(post=spoil_target_post, text=spoil_target_result, author=bot)
            spoil_target_inform.save()
        success_shot = True
    # head mafia's target is already dead
    if shoot_vote and shoot_vote.target.role == 'dead':
        shoot_result = 'Ночь ' + str(
            game.day) + ': Вам не удалось убить игрока ' + shoot_vote.target.mask.username + '.' + shoot_result
    # head mafia's target barman's target. no one dies
    elif spoil_vote and spoil_vote.target == shoot_vote.target:
        shoot_result = 'Ночь ' + str(
            game.day) + ': Вам не удалось убить игрока ' + shoot_vote.target.mask.username + '.' + shoot_result
    # head mafia's target is doctor's target, so doctor heals target. Or, head mafia's target is already dead
    elif shoot_vote and heal_vote and heal_vote.target == shoot_vote.target:
        success_result += '\n  ' + shoot_vote.target.mask.username + 'спасён доктором.'
        success_shot = True
        shoot_result = 'Ночь ' + str(
            game.day) + ': Вам не удалось убить игрока ' + shoot_vote.target.mask.username + '.' + shoot_result
        # maniac's target quarters
        shoot_target_post = GamePost.objects.get(game=game, tags__contains=['private', shoot_vote.target.user.nickname])
        shoot_target_result = 'Ночь ' + str(game.day) + ': На вас совершила покушение мафия. Доктор спас вам жизнь.'
        shoot_target_inform = GameComment(post=shoot_target_post, text=shoot_target_result, author=bot)
        shoot_target_inform.save()
    elif shoot_vote:
        success_result += '\n  ' + shoot_vote.target.mask.username
        success_shot = True
        shoot_vote.target.role = 'dead'
        shoot_vote.target.save()
        shoot_result = 'Ночь ' + str(game.day) + ': Вы убили игрока ' + shoot_vote.target.mask.username + '.' \
                       + shoot_result
        # head mafia's target quarters
        shoot_target_post = GamePost.objects.get(game=game, tags__contains=['private', shoot_vote.target.user.nickname])
        shoot_target_result = 'Ночь ' + str(game.day) + ': Вы были убиты мафией. Можете оставить последнее сообщение.'
        shoot_target_inform = GameComment(post=shoot_target_post, text=shoot_target_result, author=bot)
        shoot_target_inform.save()
    if shoot_vote:
        inform = GameComment(post=post, text=shoot_result, author=bot)
        inform.save()
    return '\n\nПокушение мафии:' + success_result if success_shot else ''


# roles are ['mafia', 'head mafia', 'mafia doctor', 'mafia barman', 'mafia killer', 'mafia recruit',
#            'militia', 'head militia', 'militia doctor', 'militia barman', 'militia killer', 'militia recruit',
#            'neutral doctor', 'neutral barman', 'neutral killer',
#            'maniac',
#            'peaceful',
#            'dead']
roles_dict = {
    'mafia': 'рядовой мафиози',
    'head mafia': 'глава мафии',
    'mafia doctor': 'тёмный доктор',
    'mafia barman': 'тёмный трактирщик',
    'mafia killer': 'тёмный киллер',
    'mafia recruit': 'адвокат мафии',
    'militia': 'помощник комиссара милиции',
    'head militia': 'комиссар милиции',
    'militia doctor': 'светлый доктор',
    'militia barman': 'светлый трактирщик',
    'militia killer': 'светлый киллер',
    'militia recruit': 'двойной агент милиции',
    'neutral doctor': 'нейтральный доктор',
    'neutral barman': 'нейтральный трактирщик',
    'neutral killer': 'нейтральный киллер',
    'maniac': 'маньяк',
    'peaceful': 'мирный',
    'dead': 'мертвец',
}
roles_description = {
    'mafia': 'Вы - рядовой мафиози. Ваша задача - выбрать главу мафии '
             'и вместе с подельниками избавиться от тех, кто вам мешает, в первую очередь - от милиции.',
    'head mafia': 'Вы - глава мафии. Вы решаете кого убивать, кого вербовать, а так же направляете своих подельников.',
    'mafia doctor': 'Вы - тёмный доктор.',
    'mafia barman': 'Вы - тёмный трактирщик.',
    'mafia killer': 'Вы - тёмный киллер.',
    'mafia recruit': 'Вы - адвокат мафии.',
    'militia': 'Вы - помощник комиссара милиции. '
               'Ваша задача - помогать комиссару милиции в поисках преступных элементов.',
    'head militia': 'Вы - комиссар милиции. Ваша задача - обнаружить и арестовать всех преступников.',
    'militia doctor': 'Вы - светлый доктор.',
    'militia barman': 'Вы - светлый трактирщик.',
    'militia killer': 'Вы - светлый киллер.',
    'militia recruit': 'Вы - двойной агент милиции.',
    'neutral doctor': 'Вы - нейтральный доктор. Ваша задача - выбрать сторону и добиваться победы вашей стороны.',
    'neutral barman': 'Вы - нейтральный трактирщик. Ваша задача - выбрать сторону и добиваться победы вашей стороны.',
    'neutral killer': 'Вы - нейтральный киллер. Ваша задача - выбрать сторону и добиваться победы вашей стороны.',
    'maniac': 'Вы - маньяк. Ваша задача - обнаружить и убить всех ролевых игроков.',
    'peaceful': 'Вы - мирный игрок. Ваша задача - помогать обнаруживать преступников.',
    'dead': 'Вы - мертвец.',
}


def maniac_kill_check(d):
    game = Game.objects.get(number=d['game'])
    maniac = GameParticipant.objects.filter(game=game, role='maniac').first()
    # there is no maniac
    if not maniac:
        return ''
    # maniac's quarters
    post = GamePost.objects.get(game=game, tags__contains=['private', maniac.user.nickname])
    bot = User.objects.get(nickname='Игровой Бот')
    shoot_result = ''
    success_shoot = False
    success_result = ''
    check_result = ''
    barman = GameParticipant.objects.filter(game=game, role__in=['neutral barman', 'mafia barman', 'militia barman']) \
        .first()
    spoil_vote = Vote.objects.filter(game=game, day=game.day, voter=barman, action='spoil').first() if barman else None
    # maniac is drunk. no one dies and no one checked
    if spoil_vote and spoil_vote.target == maniac:
        return ''
    # maniac is ok. get his targets
    else:
        shoot_vote = Vote.objects.filter(game=game, day=game.day, voter=maniac, action='shoot').first()
        check_vote = Vote.objects.filter(game=game, day=game.day, voter=maniac, action='check').first()
    doctor = GameParticipant.objects.filter(game=game, role__in=['neutral doctor', 'mafia doctor', 'militia doctor']) \
        .first()
    heal_vote = Vote.objects.filter(game=game, day=game.day, voter=doctor, action='heal').first() if doctor else None
    # perform shoot
    # if maniac's shoot target is barman, then he kills barman's target first(if it's not dead already)
    if (shoot_vote and barman and shoot_vote.target == barman) and (spoil_vote and spoil_vote.target.role != 'dead'):
        if heal_vote and heal_vote.target == barman:
            success_result += '\n  ' + spoil_vote.target.mask.username + 'спасён доктором.'
        else:
            success_result += '\n  ' + spoil_vote.target.mask.username
            spoil_vote.target.role = 'dead'
            spoil_vote.target.save()
            shoot_result = ' Вы убили игрока ' + str(spoil_vote.target.mask.username) + '.'
            # barman's target quarters
            spoil_target_post = GamePost.objects.get(game=game, tags__contains=['private', spoil_vote.target.user.nickname])
            spoil_target_result = 'Ночь ' + str(game.day) + ': Вы были убиты в трактире маньяком. ' \
                                                            'Можете оставить последнее сообщение.'
            spoil_target_inform = GameComment(post=spoil_target_post, text=spoil_target_result, author=bot)
            spoil_target_inform.save()
        success_shoot = True
    # maniac's target is already dead
    if shoot_vote and shoot_vote.target.role == 'dead':
        shoot_result = 'Ночь ' + str(
            game.day) + ': Вам не удалось убить игрока ' + shoot_vote.target.mask.username + '.' + shoot_result
    # maniac's target is barman's target. no one dies
    elif shoot_vote and spoil_vote and spoil_vote.target == shoot_vote.target:
        shoot_result = 'Ночь ' + str(
            game.day) + ': Вам не удалось убить игрока ' + shoot_vote.target.mask.username + '.' + shoot_result
    # maniac's shoot target is doctor's target. doctor heals target.
    elif shoot_vote and heal_vote and heal_vote.target == shoot_vote.target:
        success_result += '\n  ' + spoil_vote.target.mask.username + 'спасён доктором.'
        success_shoot = True
        shoot_result = 'Ночь ' + str(
            game.day) + ': Вам не удалось убить игрока ' + shoot_vote.target.mask.username + '.' + shoot_result
        # maniac's target quarters
        shoot_target_post = GamePost.objects.get(game=game, tags__contains=['private', shoot_vote.target.user.nickname])
        shoot_target_result = 'Ночь ' + str(game.day) + ': На вас совершил покушение маньяк. Доктор спас вам жизнь.'
        shoot_target_inform = GameComment(post=shoot_target_post, text=shoot_target_result, author=bot)
        shoot_target_inform.save()
    elif shoot_vote:
        success_result += '\n  ' + shoot_vote.target.mask.username
        success_shoot = True
        shoot_vote.target.role = 'dead'
        shoot_vote.target.save()
        shoot_result = 'Ночь ' + str(game.day) + ': Вы убили игрока ' + shoot_vote.target.mask.username + '.' \
                       + shoot_result
        # maniac's target quarters
        shoot_target_post = GamePost.objects.get(game=game, tags__contains=['private', shoot_vote.target.user.nickname])
        shoot_target_result = 'Ночь ' + str(game.day) + ': Вы были убиты маньяком. Можете оставить последнее сообщение.'
        shoot_target_inform = GameComment(post=shoot_target_post, text=shoot_target_result, author=bot)
        shoot_target_inform.save()
    if shoot_vote:
        inform = GameComment(post=post, text=shoot_result, author=bot)
        inform.save()
    # perform check
    # if maniac's check target is barman, then he checks both barman and barman's target
    if (check_vote and barman and check_vote.target == barman) and (spoil_vote and spoil_vote.target.role != 'dead'):
        check_result = ' Проверка: игрок ' + spoil_vote.target.mask.username + ' - ' + roles_dict[
            spoil_vote.target.role] + '.'
        check_result = 'Ночь ' + str(game.day) + ': Проверка: игрок ' + check_vote.target.mask.username + ' - ' \
                       + roles_dict[check_vote.target.role] + '.' + check_result
    # maniac's check target is barman's target. no one checked
    elif check_vote and spoil_vote and spoil_vote.target == check_vote.target:
        check_result = 'Ночь ' + str(
            game.day) + ': Вам не удалось проверить игрока ' + check_vote.target.mask.username + '.'
    elif check_vote:
        check_result = 'Ночь ' + str(game.day) + ': Проверка: игрок ' + check_vote.target.mask.username + ' - ' \
                       + roles_dict[check_vote.target.role] + '.' + check_result
    if check_vote:
        inform = GameComment(post=post, text=check_result, author=bot)
        inform.save()
    return '\n\nПокушение киллера:' + success_result if success_shoot else ''


def militia_check(d):
    game = Game.objects.get(number=d['game'])
    militia = GameParticipant.objects.filter(game=game, role='militia').first()
    # there is no militia
    if not militia:
        return ''
    # militia's quarters
    post = GamePost.objects.get(game=game, tags__contains=['private', militia.user.nickname])
    bot = User.objects.get(nickname='Игровой Бот')
    check_result = ''
    militia_roles = ['militia doctor', 'militia barman', 'militia killer', 'militia recruit']
    barman = GameParticipant.objects.filter(game=game, role__in=['neutral barman', 'mafia barman', 'militia barman']) \
        .first()
    spoil_vote = Vote.objects.filter(game=game, day=game.day, voter=barman, action='spoil').first() if barman else None
    # militia is drunk. no one checked
    if spoil_vote and spoil_vote.target == militia:
        return ''
    # militia is ok. get his target
    else:
        check_vote = Vote.objects.filter(game=game, day=game.day, voter=militia, action='check').first()
    # perform check
    # if militia's check target is barman, then he checks both barman and barman's target
    if (check_vote and barman and check_vote.target == barman) and (spoil_vote and spoil_vote.target.role != 'dead'):
        check_result = ' Проверка: игрок ' + spoil_vote.target.mask.username + ' - ' + roles_dict[
            spoil_vote.target.role] + '.'
        check_result = 'Ночь ' + str(game.day) + ': Проверка: игрок ' + check_vote.target.mask.username + ' - ' \
                       + roles_dict[check_vote.target.role] + '.' + check_result
        if spoil_vote.target.role in militia_roles:
            spoil_vote.target.see_mil_q = True
            spoil_vote.target.checked_by_mil = True
            spoil_vote.target.save()
            check_result += '\nВы дали доступ в явочную каюту милиции игроку ' + spoil_vote.target.mask + '.'
            spoil_target_post = GamePost.objects.get(game=game, tags__contains=['private',
                                                                                spoil_vote.target.user.nickname])
            spoil_target_result = 'Ночь ' + str(game.day) + ': Милиция дала вам доступом в их явочную каюту.'
            spoil_target_inform = GameComment(post=spoil_target_post, text=spoil_target_result, author=bot)
            spoil_target_inform.save()
    # militia's check target is barman's target. no one checked
    elif spoil_vote and check_vote and spoil_vote.target == check_vote.target:
        check_result = 'Ночь ' + str(
            game.day) + ': Вам не удалось проверить игрока ' + check_vote.target.mask.username + '.'
    elif check_vote:
        check_result = 'Ночь ' + str(game.day) + ': Проверка: игрок ' + check_vote.target.mask.username + ' - ' \
                       + roles_dict[check_vote.target.role] + '.' + check_result
        check_vote.target.checked_by_mil = True
        check_vote.target.save()
        if check_vote.target.role in militia_roles:
            check_vote.target.see_mil_q = True
            spoil_vote.target.checked_by_mil = True
            check_vote.target.save()
            check_result += '\nВы дали доступ в явочную каюту милиции игроку ' + check_vote.target.mask + '.'
            check_vote_target_post = GamePost.objects.get(game=game, tags__contains=['private',
                                                                                     check_vote.target.user.nickname])
            check_vote_target_result = 'Ночь ' + str(game.day) + ': Милиция дала вам доступом в их явочную каюту.'
            check_vote_target_inform = GameComment(post=check_vote_target_post,
                                                   text=check_vote_target_result, author=bot)
            check_vote_target_inform.save()
    if check_vote:
        inform = GameComment(post=post, text=check_result, author=bot)
        inform.save()
    return ''


def head_militia_arrest(d):
    game = Game.objects.get(number=d['game'])
    militia = GameParticipant.objects.filter(game=game, role='head militia') \
        .first()
    # there is no head militia
    if not militia:
        return ''
    # head militia's quarters
    post = GamePost.objects.get(game=game, tags__contains=['private', militia.user.nickname])
    bot = User.objects.get(nickname='Игровой Бот')
    check_result = ''
    arrest_result = ''
    success_arrest = False
    success_result = ''
    mafia_roles = ['mafia', 'head mafia', 'mafia doctor', 'mafia barman', 'mafia killer', 'mafia recruit', 'maniac']
    militia_roles = ['militia doctor', 'militia barman', 'militia killer', 'militia recruit']
    barman = GameParticipant.objects.filter(game=game, role__in=['neutral barman', 'mafia barman', 'militia barman']) \
        .first()
    spoil_vote = Vote.objects.filter(game=game, day=game.day, voter=barman, action='spoil').first() if barman else None
    # head militia is drunk. no one dies
    if spoil_vote and spoil_vote.target == militia:
        return ''
    # head militia is ok. get his target
    else:
        check_vote = Vote.objects.filter(game=game, day=game.day, voter=militia, action='check').first()
    # perform check
    # if militia's check target is barman, then he checks both barman and barman's target
    if (check_vote and barman and check_vote.target == barman) and (spoil_vote and spoil_vote.target.role != 'dead'):
        check_result = ' Проверка: игрок ' + spoil_vote.target.mask.username + ' - ' + roles_dict[
            spoil_vote.target.role] + '.'
        check_result = 'Ночь ' + str(game.day) + ': Проверка: игрок ' + check_vote.target.mask.username + ' - ' \
                       + roles_dict[check_vote.target.role] + '.' + check_result
        if spoil_vote.target.role in mafia_roles:
            success_result += '\n  ' + spoil_vote.target.mask.username
            success_arrest = True
            spoil_vote.target.role = 'dead'
            spoil_vote.target.checked_by_mil = True
            spoil_vote.target.save()
            arrest_result = ' Вы арестовали игрока ' + spoil_vote.target.mask.username + '.'
            # barman's target quarters
            spoil_target_post = GamePost.objects.get(game=game, tags__contains=['private',
                                                                                spoil_vote.target.user.nickname])
            spoil_target_result = 'Ночь ' + str(game.day) + ': Вы были арестованы в трактире комиссаром милиции. ' \
                                                            'Можете оставить последнее сообщение.'
            spoil_target_inform = GameComment(post=spoil_target_post, text=spoil_target_result, author=bot)
            spoil_target_inform.save()
        if spoil_vote.target.role in militia_roles:
            spoil_vote.target.see_mil_q = True
            spoil_vote.target.checked_by_mil = True
            spoil_vote.target.save()
            check_result += '\nВы дали доступ в явочную каюту милиции игроку ' + spoil_vote.target.mask + '.'
            spoil_target_post = GamePost.objects.get(game=game, tags__contains=['private',
                                                                                spoil_vote.target.user.nickname])
            spoil_target_result = 'Ночь ' + str(game.day) + ': Милиция дала вам доступом в их явочную каюту.'
            spoil_target_inform = GameComment(post=spoil_target_post, text=spoil_target_result, author=bot)
            spoil_target_inform.save()
    # militia's check target is barman's target. no one checked
    elif check_vote and spoil_vote and spoil_vote.target == check_vote.target:
        check_result = 'Ночь ' + str(
            game.day) + ': Вам не удалось проверить игрока ' + check_vote.target.mask.username + '.'
    elif check_vote:
        check_result = 'Ночь ' + str(game.day) + ': Проверка: игрок ' + check_vote.target.mask.username + ' - ' \
                       + roles_dict[check_vote.target.role] + '.' + check_result
        check_vote.target.checked_by_mil = True
        check_vote.target.save()
        if check_vote.target.role in mafia_roles:
            success_result += '\n  ' + check_vote.target.mask.username
            success_arrest = True
            check_vote.target.role = 'dead'
            check_vote.target.save()
            arrest_result = 'Ночь ' + str(game.day) + ': Вы арестовали игрока ' \
                            + spoil_vote.target.mask.username + '.' + arrest_result
            # head mafia's target quarters
            check_target_post = GamePost.objects.get(game=game,
                                                     tags__contains=['private', check_vote.target.user.nickname])
            check_target_result = 'Ночь ' + str(game.day) + ': Вы были арестованы комиссаром милиции. ' \
                                                            'Можете оставить последнее сообщение.'
            check_target_inform = GameComment(post=check_target_post, text=check_target_result, author=bot)
            check_target_inform.save()
        if check_vote.target.role in militia_roles:
            check_vote.target.see_mil_q = True
            check_vote.target.save()
            check_result += '\nВы дали доступ в явочную каюту милиции игроку ' + check_vote.target.mask + '.'
            check_vote_target_post = GamePost.objects.get(game=game, tags__contains=['private',
                                                                                     check_vote.target.user.nickname])
            check_vote_target_result = 'Ночь ' + str(game.day) + ': Милиция дала вам доступом в их явочную каюту.'
            check_vote_target_inform = GameComment(post=check_vote_target_post,
                                                   text=check_vote_target_result, author=bot)
            check_vote_target_inform.save()
    if check_vote:
        inform = GameComment(post=post, text=check_result, author=bot)
        inform.save()
        inform = GameComment(post=post, text=arrest_result, author=bot)
        inform.save()
    return '\n\nАрестованы:' + success_result if success_arrest else ''


def end_game(d):
    game = Game.objects.get(number=d['game'])
    mafia_roles = ['mafia', 'head mafia', 'mafia recruit', 'mafia doctor', 'mafia killer', 'mafia barman']
    militia_roles = ['militia', 'head militia', 'militia recruit', 'militia doctor', 'militia killer', 'militia barman']
    mafia = GameParticipant.objects.filter(game=game, role__in=mafia_roles)
    militia = GameParticipant.objects.filter(game=game, role__in=militia_roles)
    maniac = GameParticipant.objects.filter(game=game, role='maniac')
    participants = GameParticipant.objects.filter(game=game).exclude(Q(role='dead') | Q(mask__username='Игровой Бот'))
    bot = User.objects.get(nickname='Игровой Бот')
    summary_post = GamePost.objects.get(game=game, short='summary')
    report = '<center>Игра окончена</center>'
    if mafia and not militia and not maniac:
        report += '\nПобеду одержала мафия!'
        inform = GameComment(post=summary_post, text=report, author=bot)
        inform.save()
        return True
    if militia and not mafia and not maniac:
        report += '\nПобеду одержала милиция!'
        inform = GameComment(post=summary_post, text=report, author=bot)
        inform.save()
        return True
    if maniac and not militia and not mafia:
        report += '\nПобеду одержал маньяк!'
        inform = GameComment(post=summary_post, text=report, author=bot)
        inform.save()
        return True
    if not participants:
        report += '\nНичья! Все игроки скончались от космической чумы.'
        inform = GameComment(post=summary_post, text=report, author=bot)
        inform.save()
        return True
    return False


def night(d):
    game = Game.objects.get(number=d['game'])
    game_ended = False
    if game.day > 0:
        perform_actions(d)
        game_ended = end_game(d)
    posts = GamePost.objects.filter(game=game, tags__contains=['current'])
    day = str(game.day + 1)
    author = User.objects.get(nickname='Игровой Бот')
    has_mafia_post = False
    has_militia_post = False
    for post in posts:
        post.allow_comment = False
        post.tags.remove('current')
        post.save()
        slug = game.slug + '_general_day' + day
        if 'mafia_day' in post.tags:
            has_mafia_post = True
            slug = game.slug + '_mafia_day' + day
        if 'militia_day' in post.tags:
            has_militia_post = True
            slug = game.slug + '_militia_day' + day
        if not game_ended:
            new_post = GamePost(title='День ' + day, text='День ' + day, short='day' + day, tags=post.tags+['current'],
                                game=game, author=author, allow_role=post.allow_role, slug=slug)
            new_post.save()
        comment = GameComment(post=post, text='День ' + ('' if game.day == 0 else str(game.day)) +
                              ' завершен', author=author)
        comment.save()
    mafia_roles = ['mafia', 'head mafia', 'mafia doctor', 'mafia barman', 'mafia killer']
    militia_roles = ['militia', 'head militia']  # , 'militia doctor', 'militia barman', 'militia killer']
    if not has_mafia_post:
        new_recruit_post = GamePost(title='Явочная', text='Явочная мафии', short='day' + day,
                                    tags=['mafia_day', 'mafia_secret'], game=game, author=author,
                                    allow_role=mafia_roles+['mafia_recruit'], slug=game.slug + '_mafia_secret')
        new_recruit_post.save()
        new_post = GamePost(title='День ' + day, text='Мафия. День ' + day, short='day' + day,
                            tags=['mafia_day', 'current'],
                            game=game, author=author, allow_role=mafia_roles, slug=game.slug + '_mafia_day' + day)
        new_post.save()
    if not has_militia_post:
        new_recruit_post = GamePost(title='Явочная', text='Явочная милиции', short='day' + day,
                                    tags=['militia_day', 'militia_secret'], game=game, author=author,
                                    allow_role=mafia_roles+['militia_recruit'], slug=game.slug + '_militia_secret')
        new_recruit_post.save()
        new_post = GamePost(title='День ' + day, text='Милиция. День ' + day, short='day' + day,
                            tags=['militia_day', 'current', 'militia_secret'],
                            game=game, author=author, allow_role=militia_roles, slug=game.slug + '_militia_day' + day)
        new_post.save()
    if not game_ended:
        game.day += 1
        game.save()
    else:
        game.state = 'past'
        game.save()
        posts = GamePost.objects.filter(game=game)
        for post in posts:
            post.allow_role = ['everyone']
            post.allow_comment = False
            post.save()


# not used. kept for debugging purpose
def create_missing_hang_votes(d):
    game = Game.objects.get(number=d['game'])
    # participants' hang votes
    participants = GameParticipant.objects.filter(game=game).exclude(user__nickname='Игровой Бот')
    for participant in participants:
        hang_vote = Vote.objects.filter(game=game, day=game.day, voter=participant, action='hang').first()
        # if no vote, participant receives two votes against himself
        if not hang_vote:
            hang1 = Vote(game=game, day=game.day, voter=participant, action='hang', target=participant)
            hang1.save()
            hang2 = Vote(game=game, day=game.day, voter=participant, action='hang', target=participant)
            hang2.save()


def create_missing_killer_vote(d):
    game = Game.objects.get(number=d['game'])
    # killer's shoot vote
    killer = GameParticipant.objects.filter(game=game, role__in=['neutral killer', 'mafia killer', 'militia killer']) \
        .first()
    if killer:
        shoot_vote = Vote.objects.filter(game=game, day=game.day, action='shoot', voter=killer).first()
        if not shoot_vote:
            shoot_votes = Vote.objects.filter(game=game, day=game.day, action='contract') \
                .exclude(target__role__contains='killer')
            if len(shoot_votes) > 0:
                shoot = random.choice(list(shoot_votes))
                shoot_vote = Vote(game=game, day=game.day, voter=killer, action='shoot', target=shoot.target)
                shoot_vote.save()


# not used. kept for debugging purpose
def create_missing_votes(d):
    game = Game.objects.get(number=d['game'])
    # participants' hang votes
    participants = GameParticipant.objects.filter(game=game).exclude(user__nickname='Игровой Бот')
    for participant in participants:
        hang_vote = Vote.objects.filter(game=game, day=game.day, voter=participant, action='hang').first()
        # if no vote, participant receives two votes against himself
        if not hang_vote:
            hang1 = Vote(game=game, day=game.day, voter=participant, action='hang', target=participant)
            hang1.save()
            hang2 = Vote(game=game, day=game.day, voter=participant, action='hang', target=participant)
            hang2.save()
    # barman's spoil vote
    barman = GameParticipant.objects.filter(game=game, role__in=['neutral barman', 'mafia barman', 'militia barman']) \
        .first()
    if barman:
        spoil_vote = Vote.objects.filter(game=game, day=game.day, action='spoil', voter=barman).first()
        if not spoil_vote:
            spoil_vote = Vote(game=game, day=game.day, voter=barman, action='spoil', target=None)
            spoil_vote.save()
    # doctor's heal vote
    doctor = GameParticipant.objects.filter(game=game, role__in=['neutral doctor', 'mafia doctor', 'militia doctor']) \
        .first()
    if doctor:
        heal_vote = Vote.objects.filter(game=game, day=game.day, action='heal', voter=doctor).first()
        if not heal_vote:
            heal_vote = Vote(game=game, day=game.day, voter=doctor, action='heal', target=None)
            heal_vote.save()
    # killer's shoot vote
    killer = GameParticipant.objects.filter(game=game, role__in=['neutral killer', 'mafia killer', 'militia killer']) \
        .first()
    if killer:
        shoot_vote = Vote.objects.filter(game=game, day=game.day, action='shoot', voter=killer).first()
        if not shoot_vote:
            shoot_votes = Vote.objects.filter(game=game, day=game.day, action='contract') \
                .exclude(target__role__contains='killer')
            if len(shoot_votes) > 0:
                shoot = random.choice(list(shoot_votes))
                shoot_vote = Vote(game=game, day=game.day, voter=killer, action='shoot', target=shoot.target)
                shoot_vote.save()
    # maniac's shoot and check votes
    maniac = GameParticipant.objects.filter(game=game, role='maniac').first()
    if maniac:
        shoot_vote = Vote.objects.filter(game=game, day=game.day, action='shoot', voter=maniac).first()
        check_vote = Vote.objects.filter(game=game, day=game.day, action='check', voter=maniac).first()
        if not shoot_vote:
            shoot_vote = Vote(game=game, day=game.day, voter=maniac, action='shoot', target=None)
            shoot_vote.save()
        if not check_vote:
            check_vote = Vote(game=game, day=game.day, voter=maniac, action='check', target=None)
            check_vote.save()
    # head militia's check vote
    head_militia = GameParticipant.objects.filter(game=game, role='head militia').first()
    if head_militia:
        check_vote = Vote.objects.filter(game=game, day=game.day, action='check', voter=head_militia).first()
        if not check_vote:
            check_vote = Vote(game=game, day=game.day, voter=head_militia, action='check', target=None)
            check_vote.save()
    # militia's check vote
    militia = GameParticipant.objects.filter(game=game, role='militia').first()
    if militia:
        check_vote = Vote.objects.filter(game=game, day=game.day, action='check', voter=militia).first()
        if not check_vote:
            check_vote = Vote(game=game, day=game.day, voter=militia, action='check', target=None)
            check_vote.save()
    # head mafia's shoot and check votes
    head_mafia = GameParticipant.objects.filter(game=game, role='head mafia').first()
    if head_mafia:
        shoot_vote = Vote.objects.filter(game=game, day=game.day, action='shoot', voter=head_mafia).first()
        if not shoot_vote:
            shoot_vote = Vote(game=game, day=game.day, voter=head_mafia, action='shoot', target=None)
            shoot_vote.save()


def change_side(d):
    game = Game.objects.get(number=d['game'])
    roles_map = {
        'mafia_side': {
            'neutral barman': 'mafia barman',
            'neutral killer': 'mafia killer',
            'neutral doctor': 'mafia doctor',
            'peaceful': 'mafia recruit',
        },
        'militia_side': {
            'neutral barman': 'militia barman',
            'neutral killer': 'militia killer',
            'neutral doctor': 'militia doctor',
            'peaceful': 'militia recruit',
        },
    }
    bot = User.objects.get(nickname='Игровой Бот')
    neutral_barman = GameParticipant.objects.filter(game=game, role='neutral barman').first()
    neutral_doctor = GameParticipant.objects.filter(game=game, role='neutral doctor').first()
    neutral_killer = GameParticipant.objects.filter(game=game, role='neutral killer').first()
    neutrals = [neutral_doctor, neutral_killer, neutral_barman]
    side_result = ''
    for neutral in neutrals:
        if neutral:
            side_result += '\n  ' + roles_dict[neutral.role] + ' - '
            side_vote = Vote.objects.filter(Q(action='mafia_side') | Q(action='militia_side'),
                                            game=game, voter=neutral).first()
            if side_vote:
                neutral.role = roles_map[side_vote.action][neutral.role]
                neutral.save()
            else:
                random.seed(time.time())
                random_side = random.choice(['mafia_side', 'militia_side'])
                neutral.role = roles_map[random_side][neutral.role]
                neutral.save()
                post = GamePost.objects.get(game=game, tags__contains=['private', neutral.user.nickname])
                inform = GameComment(post=post, author=bot, text='Ночь ' + str(game.day) + ': ' + neutral.mask.username
                    + ' наугад выбрал сторону ' + ('мафии.' if 'mafia' in neutral.role else 'милиции.'))
                inform.save()
            side_result += roles_dict[neutral.role] + '.'
            neutral.can_choose_side = False
            neutral.save()
            # post = GamePost.objects.get(game=game, tags__contains=['private', neutral.user.nickname])
            # inform = GameComment(post=post, author=bot, text=roles_description[neutral.role])
            # inform.save()
            if 'mafia' in neutral.role:
                neutral.sees_maf_q = True
                neutral.save()
            elif ('militia' in neutral.role) and neutral.checked_by_mil:
                neutral.sees_mil_q = True
                neutral.save()
    # recruitment by mafia is the last block of code anyway, so just return if game.hasRecruit
    if game.hasRecruit:
        return ('\n\nВыбор стороны:' + side_result) if len(side_result) > 0 else ''
    # check if head mafia tried to recruit somebody
    vote_recruit = Vote.objects.filter(game=game, action='recruit', day=game.day).first()
    if vote_recruit:
        # mafia did try recruit. check if recruiter chose side
        side_vote = Vote.objects.filter(Q(action='mafia_side') | Q(action='militia_side'),
                                        game=game, voter=vote_recruit.target).first()
        head_mafia = GameParticipant.objects.filter(game=game, role='head mafia').first()
        vote_recruit.target.can_choose_side = False
        vote_recruit.target.save()
        if side_vote:
            # recruiter did chose side. change his role
            vote_recruit.target.role = roles_map[side_vote.action][vote_recruit.target.role]
            vote_recruit.target.sees_maf_q = True
            vote_recruit.target.can_choose_side = False
            vote_recruit.target.save()
            game.hasRecruit = True
            game.save()
            recruit_result = 'Ночь ' + str(game.day) + ': Вербовка: игрок ' + vote_recruit.target.mask.username + \
                             ' принимает вербовку. Завербованный теперь имеет доступ к явочной каюте мафии.'
        else:
            # recruiter did not choose side. head mafia can recruit again
            if head_mafia:
                head_mafia.can_recruit = True
                head_mafia.save()
            recruit_result = 'Ночь ' + str(game.day) + ': Вербовка: игрок ' + vote_recruit.target.mask.username + \
                             ' отказывается от вербовки.'
        recruited_post = GamePost.objects.get(game=game, tags__contains=['private', vote_recruit.target.user.nickname])
        inform = GameComment(post=recruited_post, text=recruit_result, author=bot)
        inform.save()
        if head_mafia:
            head_mafia_post = GamePost.objects.get(game=game, tags__contains=['private',
                                                                              vote_recruit.voter.user.nickname])
            inform = GameComment(post=head_mafia_post, text=recruit_result, author=bot)
            inform.save()
    return ('\n\nВыбор стороны:' + side_result) if len(side_result) > 0 else ''


def refresh_participants_states(d):
    game = Game.objects.get(number=d['game'])
    participants = GameParticipant.objects.filter(game=game).exclude(Q(mask__username='Игровой Бот') | Q(
        role__in=['dead', 'mafia killer', 'militia killer', 'neutral killer']))
    for participant in participants:
        participant.can_ask_killer = True
        participant.save()


def perform_actions(d):
    """
    priority of moves
    hang +
    barman +
    doctor +
    killer +
    maniac +
    head militia +
    head mafia +
    militia +
    change side +
    """
    game = Game.objects.get(number=d['game'])
    report = '<center>Ночь ' + str(game.day) + '</center><span class="monospace">'
    report += vote_hang(d)
    report += barman_spoil(d)
    report += doctor_heal(d)
    create_missing_killer_vote(d)
    report += killer_kill(d)
    report += maniac_kill_check(d)
    report += head_militia_arrest(d)
    report += mafia_kill(d)
    report += militia_check(d)
    report += change_side(d)
    report += '</span>'
    refresh_participants_states(d)
    bot = User.objects.get(nickname='Игровой Бот')
    summary_post = GamePost.objects.get(game=game, short='summary')
    inform = GameComment(post=summary_post, text=report, author=bot)
    inform.save()


class DisplayGamesView(generic.ListView):
    template_name = 'mafiaapp/display_games.html'
    model = Game


class DisplayCurrentGameView(generic.ListView):
    template_name = 'mafiaapp/current/current_game.html'

    def get_queryset(self):
        game = get_object_or_404(Game, state='current')
        return GamePost.objects.filter(Q(tags__contains=['day']) | Q(tags__contains=['general']), game=game) \
            .exclude(Q(tags__contains=['mafia']) | Q(tags__contains=['militia'])).order_by('-date')

    def get_context_data(self, **kwargs):
        context = super(DisplayCurrentGameView, self).get_context_data(**kwargs)
        game = Game.objects.filter(state='current')
        if isinstance(self.request.user, AnonymousUser):
            context['registered'] = False
            return context
        participant = GameParticipant.objects.filter(game=game, user=self.request.user).first()
        if participant is None:
            context['registered'] = False
        else:
            role = participant.role
            # mafia quarters
            if role in ['mafia', 'head mafia', 'mafia doctor', 'mafia barman'] or participant.sees_maf_q:
                context['mafia'] = True
            # militia quarters
            if role in ['militia', 'head militia', 'militia doctor', 'militia barman'] or participant.sees_mil_q:
                context['militia'] = True
            # morgue quarters
            if role in ['dead']:
                context['dead'] = True
            context['registered'] = True
        return context

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        context = self.get_context_data()
        return render(request, self.template_name, context)


class DisplayUpcomingGameView(generic.ListView):
    template_name = 'mafiaapp/upcoming/upcoming_game_description.html'

    def get_queryset(self):
        game = get_object_or_404(Game, state='upcoming')
        return game  # Game.objects.get(state='upcoming')

    def get_context_data(self, **kwargs):
        game = kwargs.pop('object_list', self.object_list)
        registered = True if GameParticipant.objects.filter(game=game, user=self.request.user).first() else False
        post = GamePost.objects.get(game=game, tags__contains=['description'])
        comments = GameComment.objects.filter(post=post).order_by('date')
        participants = GameParticipant.objects.filter(game=game).exclude(user__nickname='Игровой Бот')
        paginator = Paginator(comments, 10)
        page = self.request.GET.get('page')
        try:
            pages = paginator.page(page)
        except PageNotAnInteger:
            pages = paginator.page(1)
        except EmptyPage:
            pages = paginator.page(paginator.num_pages)
        context = {
            'paginator': paginator,
            'page_obj': pages,
            'is_paginated': pages.has_other_pages(),
            'game': game,
            'registered': registered,
            'post': post,
            #'comments': comments,
            'participants': participants
        }
        return context

    def post(self, request):
        self.object_list = self.get_queryset()
        action = request.POST.get('action', '')
        context = self.get_context_data()
        user = User.objects.get(username=request.user)
        if action == 'Участвовать':
            participant = GameParticipant(game=context['game'], user=user, mask=None)
            participant.save()
            private_quarters = GamePost(title='Своя каюта', text='Каюта игрока %s' % request.user.user.nickname,
                                        game=context['game'], tags=['current', 'private', request.user.user.nickname],
                                        short='private', author=user)
            private_quarters.save()
            context['registered'] = True
            return render(request, self.template_name, context)
        elif action == 'Отменить участие':
            participant = GameParticipant.objects.get(game=context['game'], user=user)
            participant.delete()
            private_quarters = GamePost.objects.get(game=context['game'], author=user, tags__contains=['private'])
            private_quarters.delete()
            context['registered'] = False
            return render(request, self.template_name, context)
        elif action == 'Опубликовать':
            post = GamePost.objects.get(game=context['game'], tags__contains=['description'])
            #comment = GameComment(post=post, author=user, text=request.POST['comment'])
            #comment.save()

            user = User.objects.get(username=request.user)
            text = request.POST['comment']
            if request.session.get('last_comment_time', ''):
                if int(time.time()) - request.session['last_comment_time'] < 15:
                    messages.add_message(request, messages.ERROR, 'Комментарии можно оставлять не чаще одного раза '
                                                                  'в 15 секунд. Подождите еще %s сек.' %
                                         (15-(int(time.time()) - request.session['last_comment_time'])))
                    return render(request, self.template_name, context)
            if text.count('\r') >= 25 or len(text) >= 2000:
                messages.add_message(request, messages.ERROR, 'Комментарий должен быть в пределах 25 строк и 2000 знаков.')
                return render(request, self.template_name, context)
            split = re.split('(?is)(\[\[.*?\]\])', text)
            for i, item in enumerate(split):
                if re.search('(?is)\[\[.+\(\d+\):\s.+\]\]', item):
                    author = re.sub('(?is)\[\[(.*?)\(.*', '\\1', item)
                    comment_id = re.sub('(?is)\[\[.*?\(([\d]+)\).*', '\\1', item)
                    if not author or not comment_id:
                        messages.add_message(request, messages.ERROR, '#1 Не найдено цитируемое сообщение %s' % item)
                        return render(request, 'mafiaapp/current/current_game_description.html', context)
                    #participant = get_object_or_404(GameParticipant, game=context['game'], mask__username=author)
                    quote = get_object_or_404(GameComment, id=int(comment_id))
                    if quote.author != user:
                        print(quote.author, user.nickname)
                        messages.add_message(request, messages.ERROR, '#2 Не найдено цитируемое сообщение %s' % item)
                        return render(request, 'mafiaapp/current/current_game_description.html', context)
                    comment_text = re.sub('(?is)\[\[.*?\):\s*(.*)\]\]$', '\\1', item)
                    if comment_text not in re.sub('(?is)<div.*?</div>', '', quote.text):
                        messages.add_message(request, messages.ERROR, '#3 Не найдено цитируемое сообщение %s' % item)
                        return render(request, 'mafiaapp/current/current_game_description.html', context)
                    split[i] = '<div class="section comment-quote"><h4>'+author+'(<a href="#'+comment_id + \
                               '">#</a>):</h4><br>'+comment_text+'</div>'
            text = ''.join([x for x in split])
            comment = GameComment(post=post, author=user, text=text)
            comment.save()
            user.comments_number += 1
            user.save()
            context = self.get_context_data()
            request.session['last_comment_time'] = int(time.time())

            return render(request, self.template_name, context)


class DisplayCurrentGamePostView(generic.ListView):
    template_name = 'mafiaapp/current/current_game_post.html'

    def get_queryset(self):
        game = get_object_or_404(Game, state='current')
        return game  # Game.objects.get(state='current')

    @staticmethod
    def allowed_actions(game, user):
        participant = GameParticipant.objects.get(game=game, user=user)
        dead = True if participant.role == 'dead' else False
        can_hang = True if participant.role != 'dead' else False
        can_shoot = True if participant.role in \
            ['head mafia', 'neutral killer', 'mafia killer', 'militia killer', 'maniac'] else False
        can_check = True if participant.role in \
            ['mafia recruit', 'head militia', 'militia', 'maniac'] else False
        can_heal = True if participant.role in \
            ['neutral doctor', 'mafia doctor', 'militia doctor'] else False
        can_spoil = True if participant.role in \
            ['neutral barman', 'mafia barman', 'militia barman'] else False
        can_choose_leader = True if not game.hasHeadMafia and participant.role == 'mafia' else False
        can_recruit = True if not game.hasRecruit and participant.role == 'head mafia' and participant.can_recruit \
            else False
        can_ask_killer = True if participant.can_ask_killer and participant.role \
            not in ['neutral killer', 'mafia killer', 'militia killer'] else False
        can_choose_side = participant.can_choose_side
        allowed_actions = {
            'dead': dead,
            'can_hang': can_hang,
            'can_shoot': can_shoot,
            'can_check': can_check,
            'can_heal': can_heal,
            'can_spoil': can_spoil,
            'can_choose_leader': can_choose_leader,
            'can_recruit': can_recruit,
            'can_ask_killer': can_ask_killer,
            'can_choose_side': can_choose_side,
        }
        return allowed_actions

    def get_context_data(self, **kwargs):
        game = kwargs.pop('object_list', self.object_list)
        short = self.kwargs.get('short', '')
        side = self.kwargs.get('side', '')
        context = {
            'paginator': None,
            'page_obj': None,
            'is_paginated': False,
            'game': game
        }
        anonymous = isinstance(self.request.user, AnonymousUser)
        participant = GameParticipant.objects.filter(game=game, user=self.request.user).first() if not anonymous else None
        registered = True if participant else False
        context['registered'] = registered
        # serve posts for dashboard/game/(mafia|militia)/
        if short in ['mafia', 'militia']:
            if anonymous or not registered or (short not in participant.role and participant.role not in
                    ['mafia recruit', 'militia recruit']) or (short == 'militia' and not participant.sees_mil_q):
                raise Http404()
            if 'recruit' in participant.role:
                post_list = GamePost.objects.filter(game=game, tags__contains=[short], short='secret')
            else:
                post_list = GamePost.objects.filter(game=game, tags__contains=[short]).order_by('-date')
            context['post_list'] = post_list
            # we only need to display post_list, so return here
            return context
        # serve post for dashboard/game/morgue
        elif short == 'morgue':
            if anonymous or not registered or participant.role != 'dead':
                raise Http404()
            post = GamePost.objects.filter(game=game, short=short, tags__contains=[short]).first()
        # serve post for dashboard/game/private/
        elif short == 'private':
            if anonymous or not registered:
                raise Http404()
            post = GamePost.objects.get(game=game, short=short, tags__contains=[self.request.user.user.nickname])
            context.update(self.allowed_actions(game, self.request.user))
            # participants to hang
            if context['can_hang']:
                context['participants'] = GameParticipant.objects.filter(game=game) \
                    .exclude(Q(user__nickname='Игровой Бот') | Q(role='dead'))
            # targets to heal
            if context['can_heal'] or context['can_spoil']:
                if participant.prevTarget:
                    context['heal_spoil_targets'] = GameParticipant.objects.filter(game=game) \
                        .exclude(id=participant.prevTarget.id) \
                        .exclude(Q(user__nickname='Игровой Бот') | Q(role='dead'))
                else:
                    context['heal_spoil_targets'] = GameParticipant.objects.filter(game=game) \
                        .exclude(Q(user__nickname='Игровой Бот') | Q(role='dead'))
            # killer's targets to shoot
            if context['can_shoot'] and participant.role in ['neutral killer', 'mafia killer', 'militia killer']:
                contract_votes = Vote.objects.filter(game=game, day=game.day, action='contract') \
                    .exclude(target__role__contains='killer')
                if len(contract_votes) > 0:
                    shoot_targets = []
                    for vote in contract_votes:
                        shoot_targets.append(vote.target)
                    context['shoot_targets'] = shoot_targets
                    # context['shoot_targets'] = GameParticipant.objects.filter(game=game)\
                    #    .exclude(Q(user__nickname='Игровой Бот') | Q(role='dead'))
            # targets to shoot
            if context['can_shoot'] and participant.role in ['head mafia', 'maniac']:
                context['shoot_targets'] = GameParticipant.objects.filter(game=game) \
                    .exclude(Q(user__nickname='Игровой Бот') | Q(role='dead'))
            # candidates for head mafia
            if context['can_choose_leader']:
                context['leader_targets'] = GameParticipant.objects.filter(game=game, role='mafia')
            # candidates for mafia recruit or militia recruit
            if context['can_recruit']:
                context['recruit_targets'] = GameParticipant.objects.filter(game=game) \
                    .exclude(Q(user__nickname='Игровой Бот') | Q(role='dead'))
            # targets to check
            if context['can_check']:
                context['check_targets'] = GameParticipant.objects.filter(game=game) \
                    .exclude(Q(user__nickname='Игровой Бот') | Q(role='dead'))
        # serve post for dashboard/game/(mafia|militia)/short
        elif side in ['mafia', 'militia']:
            if anonymous or not registered or (side not in participant.role and participant.role not in
                    ['mafia recruit', 'militia recruit']):
                raise Http404()
            post = GamePost.objects.get(game=game, short=short, tags__contains=[side])
        # serve post for dashboard/game/short
        else:
            post = GamePost.objects.exclude(Q(tags__contains=['mafia']) | Q(tags__contains=['militia'])) \
                .get(game=game, short=short)  # .first()
        context['post'] = post

        # serve comments for post
        if short == 'description':
            comments = GameComment.objects.filter(post=post).order_by('date')
            context['registered'] = 'noregister'
        else:
            comments = GameComment.objects.filter(post=post).order_by('date').values()
            for comment in comments:
                participant = GameParticipant.objects.get(user=comment['author_id'], game=game)
                comment['mask'] = participant.mask
                comment['author'] = participant.user
        paginator = Paginator(comments, 10)
        page = self.request.GET.get('page')
        try:
            pages = paginator.page(page)
        except PageNotAnInteger:
            pages = paginator.page(1)
        except EmptyPage:
            pages = paginator.page(paginator.num_pages)
        context['comments'] = comments
        context['paginator'] = paginator
        context['page_obj'] = pages
        context['is_paginated'] = pages.has_other_pages()
        # print('     DisplayCurrentGamePostView context', context)
        return context

    def post(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        context = self.get_context_data()
        action = request.POST.get('action', '')
        short = self.kwargs.get('short', '')
        actions = {
            'Повешать': 'hang',
            'Выбрать': 'leader',
            'Выстрелить': 'shoot',
            'Проверить': 'check',
            'Вылечить': 'heal',
            'Напоить': 'spoil',
            'Присоедениться': 'side',
            'Завербовать': 'recruit',
            'Заказать': 'contract',
        }
        if action == 'Опубликовать':
            user = User.objects.get(username=request.user)
            text = request.POST['comment']
            if request.session.get('last_comment_time', ''):
                if int(time.time()) - request.session['last_comment_time'] < 15:
                    messages.add_message(request, messages.ERROR, 'Комментарии можно оставлять не чаще одного раза '
                                                                  'в 15 секунд. Подождите еще %s сек.' %
                                         (15-(int(time.time()) - request.session['last_comment_time'])))
                    return render(request, self.template_name, context)
            if text.count('\r') >= 25 or len(text) >= 2000:
                messages.add_message(request, messages.ERROR, 'Комментарий должен быть в пределах 25 строк и 2000 знаков.')
                return render(request, self.template_name, context)
            split = re.split('(?is)(\[\[.*?\]\])', text)
            for i, item in enumerate(split):
                if re.search('(?is)\[\[.+\(\d+\):\s.+\]\]', item):
                    author = re.sub('(?is)\[\[(.*?)\(.*', '\\1', item)
                    comment_id = re.sub('(?is)\[\[.*?\(([\d]+)\).*', '\\1', item)
                    if not author or not comment_id:
                        messages.add_message(request, messages.ERROR, '#1 Не найдено цитируемое сообщение %s' % item)
                        return render(request, 'mafiaapp/current/current_game_description.html', context)
                    participant = get_object_or_404(GameParticipant, game=context['game'], mask__username=author)
                    quote = get_object_or_404(GameComment, id=int(comment_id))
                    if quote.author != participant.user:
                        messages.add_message(request, messages.ERROR, '#2 Не найдено цитируемое сообщение %s' % item)
                        return render(request, 'mafiaapp/current/current_game_description.html', context)
                    comment_text = re.sub('(?is)\[\[.*?\):\s*(.*)\]\]$', '\\1', item)
                    if comment_text not in re.sub('(?is)<div.*?</div>', '', quote.text):
                        messages.add_message(request, messages.ERROR, '#3 Не найдено цитируемое сообщение %s' % item)
                        return render(request, 'mafiaapp/current/current_game_description.html', context)
                    split[i] = '<div class="section comment-quote"><h4>'+author+'(<a href="#'+comment_id + \
                               '">#</a>):</h4><br>'+comment_text+'</div>'
            text = ''.join([x for x in split])
            comment = GameComment(post=context['post'], author=user, text=text)
            comment.save()
            participant = get_object_or_404(GameParticipant, game=context['game'], user=user)
            participant.comments_number += 1
            participant.save()
            context = self.get_context_data()
            request.session['last_comment_time'] = int(time.time())
            if short == 'description':
                # To display list of participants
                context['participants'] = GameParticipant.objects.filter(game=context['game']) \
                    .exclude(user__nickname='Игровой Бот')
                return render(request, 'mafiaapp/current/current_game_description.html', context)
        elif action in actions.keys():
            user = User.objects.get(username=request.user)
            voter = GameParticipant.objects.get(user=user, game=context['game'])
            # target = GameParticipant.objects.get(id=int(request.POST['target']), game=context['game'])
            if action == 'Присоедениться':
                side = request.POST['target']
                if side in ['mafia_side', 'militia_side']:
                    vote = Vote.objects.update_or_create(game=context['game'], day=context['game'].day, voter=voter,
                                                         action=side, defaults={'target': voter})
                else:
                    raise Http404()
            else:
                try:
                    target = get_object_or_404(GameParticipant, game=context['game'], id=int(request.POST['target']))
                except KeyError:
                    raise Http404()
                vote = Vote.objects.update_or_create(game=context['game'], day=context['game'].day, voter=voter,
                                                     action=actions[action], defaults={'target': target})

            post = GamePost.objects.get(game=context['game'], short=short, tags__contains=[request.user.user.nickname])
            author = User.objects.get(nickname='Игровой Бот')
            comment = GameComment(post=post, text=str(vote[0]), author=author)
            comment.save()

            if action == 'Заказать':
                voter.can_ask_killer = False
                voter.save()
            if action == 'Присоедениться':
                voter.can_choose_side = False
                voter.save()
            if action == 'Завербовать':
                target_post = GamePost.objects.get(game=context['game'], short=short,
                                                   tags__contains=[target.user.nickname])
                if target.role == 'peaceful':
                    target.can_choose_side = True
                    target.save()
                    recruit_result = 'День ' + str(
                        context['game'].day) + ': Мафия предлагает вам перейти на её сторону.' \
                        '\nВы можете выбрать сторону мафии и раз в день выбирать игрока для проверки его роли.' \
                        '\nВы можете выбрать сторону милиции. ' \
                        '\nЧтобы остаться мирным, проигнорируйте вербовку и не выбирайте сторону.' \
                        ' В таком случае ночью мафия получит уведомление об отказе от вербовки.'
                else:
                    recruit_result = 'День ' + str(
                        context['game'].day) + ': Мафия предлагает вам перейти на её сторону.' \
                                               '\nВы не можете принять вербовку и автоматически отказываетесь от неё.' \
                                               '\nНочью мафия получит уведомление об отказе от вербовки.'
                target_inform = GameComment(post=target_post, text=recruit_result, author=author)
                target_inform.save()
                voter.can_recruit = False
                voter.save()

            # check if we have enough votes to choose head mafia. change role of the chosen one to 'head mafia'
            # and notify others
            if action == 'Выбрать':
                maf_count = GameParticipant.objects.filter(game=context['game'], role='mafia').count()
                half = maf_count / 2
                votes_count = Vote.objects.filter(game=context['game'], action='leader').count()
                top_votes = Vote.objects.filter(game=context['game'], action='leader').values('target') \
                    .annotate(Count('target')).order_by('-target__count')
                if top_votes[0]['target__count'] >= half or votes_count == maf_count:
                    game = context['game']
                    game.hasHeadMafia = True
                    game.save()
                    context['game'] = game
                    head_mafia = GameParticipant.objects.get(id=top_votes[0]['target'])
                    head_mafia.role = 'head mafia'
                    head_mafia.save()
                    head_mafia_post = GamePost.objects.get(game=game, tags__contains=[head_mafia.user.nickname])
                    author = User.objects.get(nickname='Игровой Бот')
                    mafia_current_day_post = GamePost.objects. \
                        get(game=game, tags__contains=['mafia', 'current'])
                    comment = GameComment(post=mafia_current_day_post, author=author,
                                          text='День ' + str(game.day) + ': игрок ' + str(head_mafia) +
                                               ' был выбран главой мафии.')
                    comment.save()
                    comment = GameComment(post=head_mafia_post, author=author,
                                          text='Вы были выбраны главой мафии. '
                                               'Выберите цель для выстрела и цель для вербовки.')
                    comment.save()
            context = self.get_context_data()
        return render(request, 'mafiaapp/current/current_game_post.html', context)

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        context = self.get_context_data()
        short = kwargs['short']
        if short == 'description':
            # To display list of participants
            context['participants'] = GameParticipant.objects.filter(game=context['game']) \
                .exclude(user__nickname='Игровой Бот')
            return render(request, 'mafiaapp/current/current_game_description.html', context)
        elif short in ['mafia', 'militia']:
            return render(request, 'mafiaapp/mafia_militia_quarters.html', context)
        return render(request, 'mafiaapp/current/current_game_post.html', context)


class DisplayPastGamesView(generic.ListView):
    template_name = 'mafiaapp/past_games.html'

    def get_queryset(self):
        game = Game.objects.filter(state='past')
        return GamePost.objects.filter(game=game)


class DisplayPastGameView(generic.ListView):
    template_name = 'mafiaapp/past/past_game.html'

    def get_queryset(self):
        game = get_object_or_404(Game, short=self.kwargs['short'])
        return GamePost.objects.filter(game=game).order_by('-date')


class DisplayPastGamePostView(generic.ListView):
    template_name = 'mafiaapp/past/past_game_post.html'

    def get_queryset(self):
        game = get_object_or_404(Game, short=self.kwargs['short'])
        return game  # GamePost.objects.get(game=game, id=int(self.kwargs['post_short']))

    def get_context_data(self, **kwargs):
        game = kwargs.pop('object_list', self.object_list)
        post_id = self.kwargs.get('post_id', '')
        context = {
            'paginator': None,
            'page_obj': None,
            'is_paginated': False,
            'game': game
        }
        if post_id in ['mafia', 'militia']:
            post_list = GamePost.objects.filter(game=game, tags__contains=[post_id]).order_by('-date')
            context['post_list'] = post_list
            return context
        post = GamePost.objects.get(game=game, id=post_id)
        context['post'] = post
        # serve comments for post
        comments = GameComment.objects.filter(post=post).order_by('date').values()
        for comment in comments:
            participant = GameParticipant.objects.get(user=comment['author_id'], game=game)
            comment['mask'] = participant.mask
            comment['author'] = participant.user
        context['comments'] = comments
        context['comments'] = comments
        return context

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        context = self.get_context_data()
        if self.kwargs['post_id'] in ['mafia', 'militia']:
            return render(request, 'mafiaapp/past/past_mafia_militia_quarters.html', context)
        return render(request, self.template_name, context)


class Profile(generic.DetailView):
    template_name = 'mafiaapp/profile.html'
    context_object_name = 'profile'

    def get_object(self, queryset=None):
        return get_object_or_404(User, nickname=self.kwargs['user'])


def get_game(kwargs):
    return get_object_or_404(Game, slug=kwargs.get('game_slug', ''))


def get_game_post(kwargs):
    return get_object_or_404(GamePost, slug=kwargs.get('post_slug', ''))


def get_post(kwargs):
    return get_object_or_404(Post, slug=kwargs.get('post_slug', ''))


@login_required
def participate(request, kwargs):
    game = get_game(kwargs)
    user = get_user(request)
    participant = GameParticipant(game=game, user=user.user, mask=None)
    participant.save()
    private_quarters = GamePost(title='Своя каюта', text='Каюта игрока %s' % user.user.nickname,
                                game=game, tags=['private', user.user.nickname],
                                short='private', author=user.user, slug=game.slug+'_private_'+user.username,
                                allow_role=['private'])
    private_quarters.save()


@login_required
def cancel_participation(request, kwargs):
    game = get_game(kwargs)
    user = get_user(request)
    participant = GameParticipant.objects.get(game=game, user=user.user)
    participant.delete()
    private_quarters = GamePost.objects.get(game=game, author=user.user, tags__contains=['private'])
    private_quarters.delete()


@login_required
def post_game_comment(request, kwargs):
    print(' post_comment()')
    game = get_game(kwargs)
    print('     game', game)
    post = get_game_post(kwargs)
    print('     post', post)
    user = get_user(request)

    if user.user.nickname not in game.anchor:
        comment_participant = get_object_or_404(GameParticipant, game=game, user=user)
        if post.allow_comment:
            if 'everyone' not in post.allow_role:
                if 'private' in post.allow_role:
                    if user.user.nickname not in post.tags:
                        messages.add_message(request, messages.ERROR, '#1 Вы не можете оставлять сообщения в данной теме.')
                        return
                elif comment_participant.role not in post.allow_role:
                    messages.add_message(request, messages.ERROR, '#2 Вы не можете оставлять сообщения в данной теме.')
                    return
        else:
            messages.add_message(request, messages.ERROR, '#3 Вы не можете оставлять сообщения в данной теме.')
            return

    text = request.POST['comment']
    if request.session.get('last_comment_time', ''):
        if int(time.time()) - request.session['last_comment_time'] < 1:
            messages.add_message(request, messages.ERROR, 'Комментарии можно оставлять не чаще одного раза '
                                                          'в 15 секунд. Подождите еще %s сек.' %
                                 (15 - (int(time.time()) - request.session['last_comment_time'])))
            return
    if text.count('\r') >= 25 or len(text) >= 2000:
        messages.add_message(request, messages.ERROR, 'Комментарий должен быть в пределах 25 строк и 2000 знаков.')
        return
    split = re.split('(?is)(\[\[.*?\]\])', text)
    print('         split', split)
    for i, item in enumerate(split):
        # search for [[<nickname>(id): <comment>]]
        if re.search('(?is)\[\[.+\(\d+\):\s.*\]\]', item):
            author = re.sub('(?is)\[\[(.*?)\(.*', '\\1', item)
            comment_id = re.sub('(?is)\[\[.*?\(([\d]+)\).*', '\\1', item)
            if not author or not comment_id:
                messages.add_message(request, messages.ERROR, '#1 Не найдено цитируемое сообщение %s' % item)
                return
            if user.user.nickname in game.anchor:
                participant = user
            else:
                participant = get_object_or_404(GameParticipant, game=game, mask__username=author)
            quote = get_object_or_404(GameComment, id=int(comment_id))
            if quote.author != participant.user:
                messages.add_message(request, messages.ERROR, '#2 Не найдено цитируемое сообщение %s' % item)
                return
            comment_text = re.sub('(?is)(\[\[.*?\): *)(.*)\]\]$', '\\2', item)
            if comment_text != re.sub('(?is)<div.*?</div>', '\r\n', quote.text):
                print('         comment_text', comment_text)
                print('         re.sub', re.sub('(?is)<div.*?</div>', '\r\n', quote.text))
                messages.add_message(request, messages.ERROR, '#3 Не найдено цитируемое сообщение %s' % item)
                return
            split[i] = '<div class="section comment-quote"><h4>' + author + '(<a href="#' + comment_id + \
                       '">#</a>):</h4><br>' + comment_text + '</div>'

    text = ''.join([x for x in split])
    comment = GameComment(post=post, author=user.user, text=text, mask=comment_participant.mask if user.user.nickname
                                                                                           not in game.anchor else None)
    comment.save()
    if 'description' in post.tags or user.user.nickname in game.anchor:
        user.user.comments_number += 1
        user.user.save()
    else:
        participant = get_object_or_404(GameParticipant, game=game, user=user)
        participant.comments_number += 1
        participant.save()
    request.session['last_comment_time'] = int(time.time())
    print('     post comment success!')


# TODO
@login_required
def post_comment(request, kwargs):
    pass


@login_required
def hang(request, kwargs):
    game = get_game(kwargs)
    post = get_game_post(kwargs)
    user = get_user(request)
    voter = GameParticipant.objects.get(user=user, game=game)
    try:
        target = get_object_or_404(GameParticipant, ~Q(user__nickname='Игровой Бот') | ~Q(role='dead'), game=game,
                                   id=int(request.POST['target']))
    except KeyError:
        raise Http404()
    vote = Vote.objects.update_or_create(game=game, day=game.day, voter=voter,
                                         action='hang', defaults={'target': target})
    author = User.objects.get(nickname='Игровой Бот')
    comment = GameComment(post=post, text=str(vote[0]), author=author)
    comment.save()


@login_required
def shoot(request, kwargs):
    game = get_game(kwargs)
    post = get_game_post(kwargs)
    user = get_user(request)
    voter = GameParticipant.objects.get(user=user, game=game)
    try:
        target = get_object_or_404(GameParticipant, ~Q(user__nickname='Игровой Бот') | ~Q(role='dead'), game=game,
                                   id=int(request.POST['target']))
    except KeyError:
        raise Http404()
    vote = Vote.objects.update_or_create(game=game, day=game.day, voter=voter,
                                         action='shoot', defaults={'target': target})
    author = User.objects.get(nickname='Игровой Бот')
    comment = GameComment(post=post, text=str(vote[0]), author=author)
    comment.save()


@login_required
def choose_leader(request, kwargs):
    game = get_game(kwargs)
    post = get_game_post(kwargs)
    user = get_user(request)
    voter = GameParticipant.objects.get(user=user, game=game)
    try:
        target = get_object_or_404(GameParticipant, ~Q(user__nickname='Игровой Бот') | ~Q(role='dead'), game=game,
                                   id=int(request.POST['target']), role='mafia')
    except KeyError:
        raise Http404()
    vote = Vote.objects.update_or_create(game=game, day=game.day, voter=voter,
                                         action='leader', defaults={'target': target})
    author = User.objects.get(nickname='Игровой Бот')
    comment = GameComment(post=post, text=str(vote[0]), author=author)
    comment.save()
    # check if we have enough votes to choose head mafia
    maf_count = GameParticipant.objects.filter(game=game, role='mafia').count()
    half = maf_count / 2
    votes_count = Vote.objects.filter(game=game, action='leader').count()
    top_votes = Vote.objects.filter(game=game, action='leader').values('target') \
        .annotate(Count('target')).order_by('-target__count')
    if top_votes[0]['target__count'] >= half or votes_count == maf_count:
        game.hasHeadMafia = True
        game.save()
        head_mafia = GameParticipant.objects.get(id=top_votes[0]['target'])
        head_mafia.role = 'head mafia'
        head_mafia.can_recruit = True
        head_mafia.save()
        head_mafia_post = GamePost.objects.get(game=game, tags__contains=[head_mafia.user.nickname])
        author = User.objects.get(nickname='Игровой Бот')
        mafia_current_day_post = GamePost.objects.get(game=game, tags__contains=['mafia_day', 'current'])
        comment = GameComment(post=mafia_current_day_post, author=author,
                              text='День ' + str(game.day) + ': игрок ' + str(head_mafia) +
                                   ' был выбран главой мафии.')
        comment.save()
        comment = GameComment(post=head_mafia_post, author=author,
                              text='Вы были выбраны главой мафии. '
                                   'Выберите цель для выстрела и цель для вербовки.')
        comment.save()


@login_required
def check(request, kwargs):
    game = get_game(kwargs)
    post = get_game_post(kwargs)
    user = get_user(request)
    voter = GameParticipant.objects.get(user=user, game=game)
    try:
        target = get_object_or_404(GameParticipant, ~Q(user__nickname='Игровой Бот') | ~Q(role='dead'), game=game,
                                   id=int(request.POST['target']))
    except KeyError:
        raise Http404()
    vote = Vote.objects.update_or_create(game=game, day=game.day, voter=voter,
                                         action='check', defaults={'target': target})
    author = User.objects.get(nickname='Игровой Бот')
    comment = GameComment(post=post, text=str(vote[0]), author=author)
    comment.save()


@login_required
def heal(request, kwargs):
    game = get_game(kwargs)
    post = get_game_post(kwargs)
    user = get_user(request)
    voter = GameParticipant.objects.get(user=user, game=game)
    try:
        target = get_object_or_404(GameParticipant, ~Q(user__nickname='Игровой Бот') | ~Q(role='dead'), game=game,
                                   id=int(request.POST['target']))
    except KeyError:
        raise Http404()
    vote = Vote.objects.update_or_create(game=game, day=game.day, voter=voter,
                                         action='heal', defaults={'target': target})
    author = User.objects.get(nickname='Игровой Бот')
    comment = GameComment(post=post, text=str(vote[0]), author=author)
    comment.save()


@login_required
def spoil(request, kwargs):
    game = get_game(kwargs)
    post = get_game_post(kwargs)
    user = get_user(request)
    voter = GameParticipant.objects.get(user=user, game=game)
    try:
        target = get_object_or_404(GameParticipant, ~Q(user__nickname='Игровой Бот') | ~Q(role='dead'), game=game,
                                   id=int(request.POST['target']))
    except KeyError:
        raise Http404()
    vote = Vote.objects.update_or_create(game=game, day=game.day, voter=voter,
                                         action='spoil', defaults={'target': target})
    author = User.objects.get(nickname='Игровой Бот')
    comment = GameComment(post=post, text=str(vote[0]), author=author)
    comment.save()


@login_required
def choose_side(request, kwargs):
    game = get_game(kwargs)
    post = get_game_post(kwargs)
    user = get_user(request)
    voter = GameParticipant.objects.get(user=user, game=game)

    side = request.POST['target']
    if side in ['mafia_side', 'militia_side'] and voter.can_choose_side:
        vote = Vote.objects.update_or_create(game=game, day=game.day, voter=voter,
                                             action=side, defaults={'target': voter})
    else:
        raise Http404()
    author = User.objects.get(nickname='Игровой Бот')
    comment = GameComment(post=post, text=str(vote[0]), author=author)
    comment.save()
    voter.can_choose_side = False
    voter.save()


@login_required
def recruit(request, kwargs):
    game = get_game(kwargs)
    post = get_game_post(kwargs)
    user = get_user(request)
    voter = GameParticipant.objects.get(user=user, game=game)
    try:
        target = get_object_or_404(GameParticipant, ~Q(user__nickname='Игровой Бот') | ~Q(role='dead'), game=game,
                                   id=int(request.POST['target']))
    except KeyError:
        raise Http404()
    vote = Vote.objects.update_or_create(game=game, day=game.day, voter=voter,
                                         action='recruit', defaults={'target': target})
    author = User.objects.get(nickname='Игровой Бот')
    comment = GameComment(post=post, text=str(vote[0]), author=author)
    comment.save()

    target_post = GamePost.objects.get(game=game, tags__contains=[target.user.nickname])
    if target.role == 'peaceful':
        target.can_choose_side = True
        target.save()
        recruit_result = 'День ' + str(game.day) + ': Мафия предлагает вам перейти на её сторону.' \
            '\nВы можете выбрать сторону мафии и раз в день выбирать игрока для проверки его роли.' \
            '\nВы можете выбрать сторону милиции. ' \
            '\nЧтобы остаться мирным, проигнорируйте вербовку и не выбирайте сторону.' \
            ' В таком случае ночью мафия получит уведомление об отказе от вербовки.'
    else:
        recruit_result = 'День ' + str(game.day) + ': Мафия предлагает вам перейти на её сторону.' \
            '\nВы не можете принять вербовку и автоматически отказываетесь от неё.' \
            '\nНочью мафия получит уведомление об отказе от вербовки.'
    target_inform = GameComment(post=target_post, text=recruit_result, author=author)
    target_inform.save()
    voter.can_recruit = False
    voter.save()


@login_required
def contract(request, kwargs):
    game = get_game(kwargs)
    post = get_game_post(kwargs)
    user = get_user(request)
    voter = GameParticipant.objects.get(user=user, game=game)
    try:
        target = get_object_or_404(GameParticipant, ~Q(user__nickname='Игровой Бот') | ~Q(role='dead'), game=game,
                                   id=int(request.POST['target']))
    except KeyError:
        raise Http404()
    vote = Vote.objects.update_or_create(game=game, day=game.day, voter=voter,
                                         action='contract', defaults={'target': target})
    author = User.objects.get(nickname='Игровой Бот')
    comment = GameComment(post=post, text=str(vote[0]), author=author)
    comment.save()
    voter.can_ask_killer = False
    voter.save()


class DisplayGame(generic.ListView):
    template_name = 'mafiaapp/display_game.html'

    def get_queryset(self):
        return get_object_or_404(Game, slug=self.kwargs['game_slug'])

    def get_context_data(self, **kwargs):
        game = kwargs.pop('object_list', self.object_list)
        context = super(DisplayGame, self).get_context_data()
        context['game'] = game

        anonymous = isinstance(self.request.user, AnonymousUser)
        participant = GameParticipant.objects.filter(game=game, user=self.request.user).first() if not anonymous else None
        if participant:
            registered = True if participant else False
            context['registered'] = registered
            context['participant'] = participant
            if participant.role:
                if participant.role in ['mafia', 'head mafia', 'mafia doctor', 'mafia barman', 'mafia killer']:
                    context['mafia'] = True
                    context['mafia_core'] = True
                elif participant.role in ['mafia recruit']:
                    context['mafia'] = True
                    context['mafia_recruit'] = True
                elif participant.role in ['militia', 'head militia', 'militia doctor', 'militia barman', 'militia killer']:
                    context['militia'] = True
                    context['militia_core'] = True
                elif participant.role in ['militia recruit']:
                    context['militia'] = True
                    context['militia_recruit'] = True
                context['dead'] = True if participant.role == 'dead' else False

        gamepost_list = GamePost.objects.filter(game=game).order_by('-date')
        context['gamepost_list'] = gamepost_list

        if not anonymous and self.request.user.user.nickname in game.anchor:
            context['registered'] = True
            context['mafia'] = True
            context['mafia_core'] = True
            context['militia'] = True
            context['militia_core'] = True
        return context


class DisplayGamePost(generic.ListView):
    template_name = 'mafiaapp/display_game_post.html'
    paginate_by = 10
    model = GameComment
    context_object_name = 'comments'

    def get_queryset(self):
        return GameComment.objects.filter(post=self.game_post).order_by('date')

    def allowed_actions(self, user):
        participant = GameParticipant.objects.get(game=self.game, user=user)
        dead = True if participant.role == 'dead' else False
        can_hang = True if participant.role != 'dead' else False
        can_shoot = True if participant.role in \
            ['head mafia', 'neutral killer', 'mafia killer', 'militia killer', 'maniac'] else False
        can_check = True if participant.role in \
            ['mafia recruit', 'head militia', 'militia', 'maniac'] else False
        can_heal = True if participant.role in \
            ['neutral doctor', 'mafia doctor', 'militia doctor'] else False
        can_spoil = True if participant.role in \
            ['neutral barman', 'mafia barman', 'militia barman'] else False
        can_choose_leader = True if not self.game.hasHeadMafia and participant.role == 'mafia' else False
        can_recruit = True if not self.game.hasRecruit and participant.role == 'head mafia' and \
            participant.can_recruit else False
        can_ask_killer = True if participant.can_ask_killer and participant.role \
            not in ['neutral killer', 'mafia killer', 'militia killer'] else False
        can_choose_side = participant.can_choose_side
        allowed_actions = {
            'dead': dead,
            'can_hang': can_hang,
            'can_shoot': can_shoot,
            'can_check': can_check,
            'can_heal': can_heal,
            'can_spoil': can_spoil,
            'can_choose_leader': can_choose_leader,
            'can_recruit': can_recruit,
            'can_ask_killer': can_ask_killer,
            'can_choose_side': can_choose_side,
        }

        # participants to hang
        if allowed_actions['can_hang']:
            # check if voted previously this day
            vote = Vote.objects.filter(game=self.game, day=self.game.day, voter=participant, action='hang').first()
            if vote:
                # make order: [target, queryset w/o target]
                allowed_actions['vote_hang'] = True
                allowed_actions['participants'] = [vote.target] + list(GameParticipant.objects.filter(game=self.game)
                    .exclude(Q(user__nickname='Игровой Бот') | Q(role='dead')).exclude(id=vote.target.id))
            else:
                allowed_actions['participants'] = GameParticipant.objects.filter(game=self.game) \
                    .exclude(Q(user__nickname='Игровой Бот') | Q(role='dead'))

        # targets to heal
        if allowed_actions['can_heal']:
            # check if voted previously this day
            vote = Vote.objects.filter(game=self.game, day=self.game.day, voter=participant, action='heal').first()
            # check if we have prev target to exclude it from avail targets
            if participant.prevTarget:
                if vote:
                    # make order: [target, queryset w/o target]
                    allowed_actions['vote_heal'] = True
                    allowed_actions['heal_targets'] = [vote.target] + list(GameParticipant.objects.filter(game=self.game) \
                        .exclude(id=participant.prevTarget.id).exclude(id=vote.target.id) \
                        .exclude(Q(user__nickname='Игровой Бот') | Q(role='dead')))
                else:
                    allowed_actions['heal_targets'] = GameParticipant.objects.filter(game=self.game) \
                        .exclude(id=participant.prevTarget.id) \
                        .exclude(Q(user__nickname='Игровой Бот') | Q(role='dead'))
            else:
                if vote:
                    # make order: [target, queryset w/o target]
                    allowed_actions['vote_heal'] = True
                    allowed_actions['heal_targets'] = [vote.target] + list(GameParticipant.objects\
                        .filter(game=self.game).exclude(Q(user__nickname='Игровой Бот') | Q(role='dead'))\
                        .exclude(id=vote.target.id))
                else:
                    allowed_actions['heal_targets'] = GameParticipant.objects.filter(game=self.game) \
                        .exclude(Q(user__nickname='Игровой Бот') | Q(role='dead'))

        # targets to spoil
        if allowed_actions['can_spoil']:
            # check if voted previously this day
            vote = Vote.objects.filter(game=self.game, day=self.game.day, voter=participant, action='spoil').first()
            if participant.prevTarget:
                if vote:
                    # make order: [target, queryset w/o target]
                    allowed_actions['vote_spoil'] = True
                    allowed_actions['spoil_targets'] = [vote.target] + list(GameParticipant.objects.filter(game=self.game) \
                        .exclude(id=participant.prevTarget.id).exclude(id=vote.target.id) \
                        .exclude(Q(user__nickname='Игровой Бот') | Q(role='dead')))
                else:
                    allowed_actions['spoil_targets'] = GameParticipant.objects.filter(game=self.game) \
                        .exclude(id=participant.prevTarget.id) \
                        .exclude(Q(user__nickname='Игровой Бот') | Q(role='dead'))
            else:
                if vote:
                    # make order: [target, queryset w/o target]
                    allowed_actions['vote_spoil'] = True
                    allowed_actions['spoil_targets'] = [vote.target] + list(GameParticipant.objects\
                        .filter(game=self.game).exclude(Q(user__nickname='Игровой Бот') | Q(role='dead'))\
                        .exclude(id=vote.target.id))
                else:
                    allowed_actions['spoil_targets'] = GameParticipant.objects.filter(game=self.game) \
                        .exclude(Q(user__nickname='Игровой Бот') | Q(role='dead'))

        # killer's targets to shoot
        if allowed_actions['can_shoot'] and participant.role in ['neutral killer', 'mafia killer', 'militia killer']:
            vote = Vote.objects.filter(game=self.game, day=self.game.day, voter=participant, action='shoot').first()
            if vote:
                contract_votes = Vote.objects.filter(game=self.game, day=self.game.day, action='contract') \
                    .exclude(Q(target__role__contains='killer') | Q(target__role__contains='dead'))\
                    .exclude(target=vote.target)
            else:
                contract_votes = Vote.objects.filter(game=self.game, day=self.game.day, action='contract') \
                    .exclude(Q(target__role__contains='killer') | Q(target__role__contains='dead'))
            if len(contract_votes) > 0:
                allowed_actions['vote_shoot'] = True if vote else None
                shoot_targets = [vote.target] if vote else []
                for contract_vote in contract_votes:
                    shoot_targets.append(contract_vote.target)
                allowed_actions['shoot_targets'] = shoot_targets

        # targets to shoot
        if allowed_actions['can_shoot'] and participant.role in ['head mafia', 'maniac']:
            # check if voted previously this day
            vote = Vote.objects.filter(game=self.game, day=self.game.day, voter=participant, action='shoot').first()
            if vote:
                allowed_actions['vote_shoot'] = True
                allowed_actions['shoot_targets'] = [vote.target] + list(GameParticipant.objects.filter(game=self.game)
                    .exclude(Q(user__nickname='Игровой Бот') | Q(role='dead')).exclude(id=vote.target.id))
            else:
                allowed_actions['shoot_targets'] = GameParticipant.objects.filter(game=self.game) \
                    .exclude(Q(user__nickname='Игровой Бот') | Q(role='dead'))

        # candidates for head mafia
        if allowed_actions['can_choose_leader']:
            # check if voted previously this day
            vote = Vote.objects.filter(game=self.game, day=self.game.day, voter=participant, action='leader').first()
            if vote:
                # make order: [target, queryset w/o target]
                allowed_actions['vote_leader'] = True
                allowed_actions['leader_targets'] = [vote.target] + list(GameParticipant.objects.filter(game=self.game,
                    role='mafia').exclude(id=vote.target.id))
            else:
                allowed_actions['leader_targets'] = GameParticipant.objects.filter(game=self.game, role='mafia')

        # candidates for mafia recruit or militia recruit
        if allowed_actions['can_recruit']:
            allowed_actions['recruit_targets'] = GameParticipant.objects.filter(game=self.game) \
                .exclude(Q(user__nickname='Игровой Бот') | Q(role='dead'))

        # targets to check
        if allowed_actions['can_check']:
            # check if voted previously this day
            vote = Vote.objects.filter(game=self.game, day=self.game.day, voter=participant, action='check').first()
            if vote:
                # make order: [target, queryset w/o target]
                allowed_actions['vote_check'] = True
                allowed_actions['check_targets'] = [vote.target] + list(GameParticipant.objects.filter(game=self.game) \
                    .exclude(Q(user__nickname='Игровой Бот') | Q(role='dead')).exclude(id=vote.target.id))
            else:
                allowed_actions['check_targets'] = GameParticipant.objects.filter(game=self.game) \
                    .exclude(Q(user__nickname='Игровой Бот') | Q(role='dead'))
        return allowed_actions

    def get_context_data(self, **kwargs):
        context = super(DisplayGamePost, self).get_context_data()
        context['game'] = self.game
        context['post'] = self.game_post
        if 'description' in self.game_post.tags:
            self.template_name = 'mafiaapp/display_post.html'
            participants = GameParticipant.objects.filter(game=self.game).exclude(user__nickname='Игровой Бот')
            context['participants'] = participants
        if self.request.user.is_authenticated():
            participant = GameParticipant.objects.filter(game=self.game, user=self.request.user).first()
            context['registered'] = True if participant else False
            context['participant'] = participant if participant else None
        if 'private' in self.game_post.tags and self.request.user.user.nickname in self.game_post.tags:
            context.update(self.allowed_actions(self.request.user))
        return context

    dispatcher = {
        'Участвовать': participate,
        'Отменить участие': cancel_participation,
        'Опубликовать': post_game_comment,
        'Повешать': hang,
        'Выбрать': choose_leader,
        'Выстрелить': shoot,
        'Проверить': check,
        'Вылечить': heal,
        'Напоить': spoil,
        'Присоедениться': choose_side,
        'Завербовать': recruit,
        'Заказать': contract,
    }

    def allow_access(self, request):
        if 'everyone' in self.game_post.allow_role:
            return True
        user = get_user(request)
        if user.is_authenticated():
            if user.user.nickname in self.game.anchor:
                return True
            participant = GameParticipant.objects.filter(game=self.game, user=self.request.user).first()
            if participant:
                if 'private' in self.game_post.allow_role and user.user.nickname in self.game_post.tags:
                    return True
                if participant.role in self.game_post.allow_role:
                    return True
        return False

    def post(self, request, *args, **kwargs):
        self.game = get_game(kwargs)
        self.game_post = get_game_post(kwargs)
        if not self.allow_access(request):
            raise Http404
        if request.POST.get('action', '') in self.dispatcher.keys():
            self.dispatcher[request.POST['action']](request, self.kwargs)
        else:
            raise Http404
        self.object_list = self.get_queryset()
        context = self.get_context_data()
        return render(request, self.template_name, context=context)

    def get(self, request, *args, **kwargs):
        self.game = get_game(kwargs)
        self.game_post = get_game_post(kwargs)
        if not self.allow_access(request):
            raise Http404
        self.object_list = self.get_queryset()
        context = self.get_context_data()
        return render(request, self.template_name, context=context)


class DisplayPost(generic.ListView):
    template_name = 'mafiaapp/display_post.html'
    paginate_by = 10
    model = Comment
    context_object_name = 'comments'

    def get_queryset(self):
        return Comment.objects.filter(post=self.post)

    def get_context_data(self, **kwargs):
        context = super(DisplayGamePost, self).get_context_data()
        context['post'] = self.post
        return context

    dispatcher = {
        'Участвовать': participate,
        'Отменить участие': cancel_participation,
        'Опубликовать': post_comment,
    }

    def post(self, request, *args, **kwargs):
        print('DisplayPost POST')
        self.post = get_post(kwargs)
        print(' action', request.POST.get('action', ''))
        if request.POST.get('action', '') in self.dispatcher.keys():
            print(' action in keys!')
            self.dispatcher[request.POST['action']](request, self.kwargs)
        else:
            raise Http404
        self.object_list = self.get_queryset()
        context = self.get_context_data()
        print(' context', context)
        return render(request, self.template_name, context=context)

    def get(self, request, *args, **kwargs):
        self.post = get_post(kwargs)
        self.object_list = self.get_queryset()
        context = self.get_context_data()
        return render(request, self.template_name, context=context)


flood = [
    "Широкополосный шум может генерироваться с помощью указанных ранее эффектов, а именно за счет теплового и дробового шума.",
    "Дробовой шум вакуумного диода является классическим источником широкополосного шума, который особенно удобен в работе, поскольку напряжение шума можно точно предсказать.",
    "У розового шума равные мощности на каждой октаве, а не на каждой частоте.",
    "Для точного измерения шума необходимо знать эквивалентную «полосу шума», т. е. ширину полосы совершенного «прямоугольного» фильтра нижних частот, через который бы проходило такое же напряжение шума.",
    "Другой способ изготовить полосовой фильтр для измерения шума-это использовать RLC-схему.",
    "Наиболее точный способ измерения выходного шума - использование выверенного вольтметра среднеквадратичного (эффективного) напряжения.",
    "Если входной каскад имеет недостаточно высокий коэффициент ослабления флуктуации питания, то это может привести к возникновению автоколебаний.",
    "Комментарии играют важную роль в ассемблере, потому что без них программа непонятна даже ее создателю.",
    "После инструкции scasb необходимо проверить, есть ли какие-нибудь символы между пробелом и завершающим нулем.",
    "mov stdout, eax",
    "int 21h",
    "mov ah, 4ch",
    "Писать lock-free код не просто.",
    "Допустим, что в стеке сейчас два элемента, A -> C.",
    "Стандарт С++ не гарантирует, что new и delete являются lock-free.",
    "В чем смысл разрабатывать lock-free алгоритм, если он вызывает библиотечные функции, которые не lock-free?",
    "Хорошо известно, что как компилятор, так и процессор могут поменять порядок выполнения команд.",
    "Итак, Вы собираетесь создать новый [] функциональный, [] императивный, [] объектно-ориентированный, [] процедурный, [] стековый, [] мультипарадигменный, [] быстрый, [] статически-типизированный, [] динамически-типизированный, [] чистый, [] богатый, [] не-искусственный, [] наглядный, [] простой для новичков, [] простой даже для не-программистов, [] абсолютно непостижимый язык программирования.",
    "Сборка мусора бесплатна",
    "Компьютеры имеют бесконечную память",
    "Весь мир общается в 7-битном ASCII",
    "Масштабирование для больших проектов будет простым",
    "Все программисты любят шаблоны",
    "Вам не аукнется обозначение некоторого поведения как «неопределенного»",
    "А еще у Вас нет никаких спецификаций",
    "Ваша система типов дефектна",
    "Название Вашего языка делает невозможным его поиск в Гугле",
    "Для компиляции Вашего языка требуется искусственный интеллект",
    "Конфликты «сдвиг-свертка» по ходу парсинга решаются методом rand()",
    "Ошибки, выдаваемые Вашим компилятором, загадочны и непостижимы",
    "Компилятор падает даже от брошенного на него косого взгляда",
    "Вам зачем-то понадобилось присутствие компилятора в рантайме",
    "Уже существует небезопасный императивный язык",
    "Вы переизобрели PHP, только хуже",
    "Вы переизобрели Brainfuck, вот только в отличии от его авторов — на полном серьёзе",
    "Получился плохой язык и Вам должно быть стыдно за него.",
    "Программирование на этом языке — самое адекватное наказание Вам за его изобретение. ",
    "В связи с событиями на Кипре народ оживился и разволновался.",
    "Вот как бывает,\n"
    "Как происходит:\n"
    "Кто-то теряет,\n"
    "Кто-то находит.",
    "Ниже приводится коротенький экономический ликбез по трудовой теории стоимости (в авторской интерпретации).",
    "Труд – движитель экономики.",
    "Труд завершается потреблением.",
    "Труд предполагает конечную цель.",
    "Адепты трудовой теории стоимости полагали, будто все продукты должны возмещаться по продолжительности изготовления.",
    "Не хлебом единым – так сказано в умной книжке.",
    "Обмен должен осуществляться на эквивалентной основе. В связи с этим организуется денежное обращение.",
    "Как в апланате, так и в объективе Петцваля и передний, и задний компоненты представляют собой ахроматические линзы.",
    "Как у апланатов, так и у объективов Петцваля кривизна поля изображения не исправлена.",
    "Добавление к схеме плосковогнутой рассеивающей линзы позволяет, в значительной степени, исправить кривизну поля изображения.",
    "В нашей сфере деятельности нам доступны огромные объёмы знаний, в особенности тех, которые позволяют разработчику стать эффективным.",
    "Но так всё-таки, что для нас значит быть „ведущим“?",
    "Осмысленное запоминание в 9 раз быстрее механического заучивания.",
    "Осмысленность на порядок снижает затраты на усвоение материала.",
    "Регулярность использования нового материала может быть решающим фактором.",
    "При изучении любого языка начинайте пополнять свой словарный запас с заучивания стоп-слов.",
    "Безусловно, компиляция — довольно экзотичное занятие для программиста, где-нибудь в одном ряду с программированием огромных боевых человекоподобных роботов. Однако у всего этого есть практические применения, в отличие от многих других экстравагантных программистских хобби.",
    "Когда начинающий программист пытается написать парсер текста, его естественный подход — рекурсивное углубление: найти начало конструкции (например, {); найти её конец (например, } на том же уровне вложенности); выделить содержимое конструкции, и пропарсить её рекурсивно.",
    "ДКА (детерминированный конечный автомат) — штука, которая может находиться в одном из N состояний",
    "Как регэкспом обозначить условие «на том же уровне вложенности»?\n"
    "Математики и тут постарались: доказали, что невозможно.",
    "Значит, для парсинга языков, поддерживающих вложенные конструкции (а это все языки сложнее BAT-файлов), нам потребуется более мощный инструмент, чем регэкспы."
]
