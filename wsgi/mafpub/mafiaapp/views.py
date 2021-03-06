import logging
import random
import string
import time
import json
from itertools import islice

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.views import (
    password_reset_done,
    password_reset_confirm,
    password_reset_complete,
    password_reset
)
from django.core.mail import send_mail
from django.core.urlresolvers import reverse_lazy, reverse
from django.db.models import Q, Count
from django.http import Http404, JsonResponse
from django.http.request import HttpRequest
from django.test import RequestFactory, Client
from django.shortcuts import get_object_or_404, redirect, HttpResponseRedirect
from django.shortcuts import render
from django.views import generic
from django.conf import settings
from django.utils.importlib import import_module

from .forms import *
from .models import User as mafpub_user

logger = logging.getLogger(__name__)


def wrap_password_reset(request):
    return password_reset(request,
                          template_name='mafiaapp/password_reset_form.html',
                          post_reset_redirect=reverse('mafiaapp:password_reset_done'),
                          email_template_name='mafiaapp/password_reset_email.html')


def wrap_password_reset_done(request):
    return password_reset_done(request,
                               template_name='mafiaapp/password_reset_done.html')


def wrap_password_reset_confirm(request, uidb64, token):
    return password_reset_confirm(request, uidb64=uidb64, token=token,
                                  template_name='mafiaapp/password_reset_confirm.html',
                                  post_reset_redirect=reverse('mafiaapp:password_reset_complete'))


def wrap_password_reset_complete(request):
    return password_reset_complete(request,
                                   template_name='mafiaapp/password_reset_complete.html')


class IndexView(generic.ListView):
    template_name = 'mafiaapp/index.html'

    def get_queryset(self):
        return None

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated():
            return redirect('mafiaapp:dashboard')
        else:
            return render(request, 'mafiaapp/index.html')


class AjaxRegister(generic.View):
    def post(self, request, *args, **kwargs):
        form = EmailValidationForm(request.POST)
        if form.is_valid():
            email = request.POST['email']
            registered_emails = EmailValidation.objects.all().values('email')
            for record in registered_emails:
                if email == record['email']:
                    message = 'Данный адрес уже зарегистророван. Укажите другой.'
                    status = 'FAIL'
                    return JsonResponse({'status': status, 'message': message})
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
                         'После активации учетной записи вы сможете авторизоваться используя выбранные вами ' \
                         'электронный адрес и пароль.\r' \
                         '\r' \
                         'С этого момента вы сможете оставлять сообщения и принимать участие в играх.\r' \
                         '\r' \
                         'Благодарим за регистрацию!'
            send_mail('Галамафия 2.0: Регистрация учетной записи', email_body % code,
                      'Галамафия 2.0 <noreply@maf.pub>',
                      [email], fail_silently=False)
            message = 'Проверьте указанный почтовый ящик для завершения регистрации.'
            status = 'OK'
            return JsonResponse({'status': status, 'message': message})
        else:
            message = 'Укажите корректный электронный адрес.'
            status = 'FAIL'
            return JsonResponse({'status': status, 'message': message})


class AjaxLogin(generic.View):
    def post(self, request, *args, **kwargs):
        form = LoginForm(request.POST)
        next = request.GET.get('next', reverse_lazy('mafiaapp:index'))
        if form.is_valid():
            email = form.cleaned_data['email']
            user = get_object_or_404(User, email__iexact=email)
            password = form.cleaned_data['password']
            user = authenticate(username=user.username, password=password)
            if user is not None:
                login(request, user)
                message = 'Добро пожаловать, %s' % str(user)
                status = 'OK'
                return JsonResponse({'status': status, 'message': message, 'next': next})
            else:
                message = 'Проверьте правильность логина и пароля.'
                status = 'FAIL'
                return JsonResponse({'status': status, 'message': message, 'next': next})
        else:
            message = 'Проверьте правильность логина и пароля.'
            status = 'FAIL'
            return JsonResponse({'status': status, 'message': message, 'next': next})


class FormRegister(generic.TemplateView):
    template_name = 'mafiaapp/form_register.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        form = EmailValidationForm(request.POST)
        if form.is_valid():
            email = request.POST['email']
            registered_emails = EmailValidation.objects.all().values('email')
            for record in registered_emails:
                if email == record['email']:
                    message = 'Данный адрес уже зарегистророван. Проверьте почту или укажите другой адрес.'
                    return render(request, self.template_name, context={'form': form, 'message': message})
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
                         'После активации учетной записи вы сможете авторизоваться используя выбранные вами ' \
                         'электронный адрес и пароль.\r' \
                         '\r' \
                         'С этого момента вы сможете оставлять сообщения и принимать участие в играх.\r' \
                         '\r' \
                         'Благодарим за регистрацию!'
            send_mail('Галамафия 2.0: Регистрация учетной записи', email_body % code,
                      'Галамафия 2.0 <noreply@maf.pub>',
                      [email], fail_silently=False)
            message = 'Проверьте указанный почтовый ящик для завершения регистрации.'
            return render(request, self.template_name, context={'form': form, 'message': message})
        else:
            message = 'Укажите корректный электронный адрес.'
            return render(request, self.template_name, context={'form': form, 'message': message})


class FormLogin(generic.TemplateView):
    template_name = 'mafiaapp/form_login.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        form = LoginForm(request.POST)
        message = 'Проверьте правильность логина и пароля.'
        if form.is_valid():
            email = form.cleaned_data['email']
            # user = get_object_or_404(User, email__iexact=email)
            user = User.objects.filter(email__iexact=email).first()
            if not user:
                return render(request, self.template_name, context={'form': form, 'message': message})
            password = form.cleaned_data['password']
            user = authenticate(username=user.username, password=password)
            if user is not None:
                login(request, user)
                return redirect('/')
            else:
                return render(request, self.template_name, context={'form': form, 'message': message})
        else:
            return render(request, self.template_name, context={'form': form, 'message': message})


class LoginAs(generic.View):
    def get(self, request, *args, **kwargs):
        user = User.objects.get(username=kwargs['username'])
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        original_username = request.user.username
        login(request, user)
        request.session['restore_user'] = True
        request.session['username'] = original_username
        #participant = GameParticipant.objects.filter(user=user).first()
        #game = get_game(kwargs)
        #private_q = GamePost.objects.get(game=game, tags__contains=[participant.user.nickname])
        #return redirect(reverse_lazy('mafiaapp:display_game_post', kwargs={'game_slug': participant.game.slug,
        #                                                                   'post_slug': private_q.slug}))
        return redirect('/')


class RegisterView(generic.CreateView):
    model = User
    success_url = '/'
    template_name = 'mafiaapp/register_user.html'
    form_class = UserCreateForm

    def get_initial(self):
        email = get_object_or_404(EmailValidation, code=self.kwargs['code'])
        return {'email': email.email}

    def form_valid(self, form):
        messages.add_message(self.request, messages.INFO, 'Registration successful. You may now login using your '
                                                          'credentials')
        email = get_object_or_404(EmailValidation, code=self.kwargs['code'])
        email.code = ''
        email.save()
        return super(RegisterView, self).form_valid(form)


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

    def get_context_data(self, **kwargs):
        context = super(Dashboard, self).get_context_data(**kwargs)
        post_list = Post.objects.all().order_by('date')
        context['post_list'] = post_list
        return context


class Logout(generic.View):
    def get(self, request):
        if request.session.get('restore_user', ''):
            user = User.objects.get(username=request.session['username'])
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            request.session['restore_user'] = None
            login(request, user)
        else:
            logout(request)
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
        description = GamePost(title='Регистрация', game=self.object, text=self.request.POST['description'],
                               author=user,
                               tags=['general', 'description'], short='description',
                               slug=self.object.slug + '_description', allow_role=['everyone'])
        description.save()
        summary = GamePost(title='Итоги ночей', game=self.object, text='Итоги обновляются каждую игровую ночь.',
                           author=bot, tags=['general', 'summary'], short='summary', slug=self.object.slug + '_summary',
                           allow_comment=False, allow_role=['everyone'])
        summary.save()
        morgue = GamePost(title='Морг', game=self.object, text='Здесь уют.',
                          author=bot, tags=['morgue'], short='morgue', slug=self.object.slug + '_morgue',
                          allow_role=['dead'])
        morgue.save()
        bot_mask = Mask(game=self.object, avatar=bot.avatar, username=bot.nickname, taken=True)
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
        return super(CreateGamePost, self).post(request, *args, **kwargs)


class CreateGameMask(generic.CreateView):
    model = Mask
    form_class = CreateGameMaskForm
    success_url = '/dashboard/creategamemask/'
    template_name = 'mafiaapp/create_game_mask.html'


class DeleteGameView(generic.DeleteView):
    model = Game
    success_url = reverse_lazy('mafiaapp:display_games')


class DeleteGameComment(generic.DeleteView):
    model = GameComment

    def get_success_url(self):
        return reverse_lazy('mafiaapp:display_game_post', kwargs={'game_slug': self.kwargs.get('game_slug', ''),
                                                                  'post_slug': self.kwargs.get('post_slug', '')})


class DeleteComment(generic.DeleteView):
    model = Comment

    def get_success_url(self):
        return reverse_lazy('mafiaapp:display_post', kwargs={'post_slug': self.kwargs.get('post_slug', '')})


class GameParticipantUpdate(generic.UpdateView):
    model = GameParticipant
    fields = ['role', 'prevTarget', 'can_ask_killer', 'can_choose_side', 'sees_maf_q', 'sees_mil_q',
              'can_recruit', 'checked_by_mil']
    success_url = reverse_lazy('mafiaapp:display_games')

    """
    def get_success_url(self):
        next_url = self.request.GET.get('next', None)
        if next_url:
            return redirect(next_url)
        else:
            return reverse_lazy('mafiaapp:display_games')
    """


class EditGameView(generic.ListView, generic.edit.UpdateView):
    model = Game
    template_name = 'mafiaapp/edit_game.html'
    form_class = CreateGameForm
    context_object_name = 'game'

    def get_object(self, queryset=None):
        game = get_object_or_404(Game, number=self.kwargs['pk'])
        return game  # Game.objects.get(number=self.kwargs['pk'])

    def get_queryset(self):
        game = get_object_or_404(Game, number=self.kwargs['pk'])
        return game  # Game.objects.get(number=self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        context = super(EditGameView, self).get_context_data(**kwargs)
        # game = kwargs.pop('object_list', self.object_list)
        participants = GameParticipant.objects.filter(game=context['game']).exclude(user__nickname='Игровой Бот')
        masks = Mask.objects.filter(game=context['game']).exclude(username='Игровой Бот')
        description = GamePost.objects.get(game=context['game'], tags__contains=['description'])
        users = mafpub_user.objects.all()
        role_choices = GameParticipant.ROLE_CHOICES
        context['participants'] = participants
        context['masks'] = masks
        context['description'] = description
        context['users'] = users
        context['roles'] = role_choices
        participants_form = []
        for participant in participants:
            participants_form.append(UpdateGameParticipantForm(instance=participant))
        context['participants_form'] = participants_form
        return context

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
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
            # masks = random.sample(list(context['masks']), len(context['masks']))
            masks = Mask.objects.filter(game=context['game'], taken=False)
            masks = random.sample(list(masks), len(masks))
            # roles = ['head militia', 'neutral doctor', 'neutral barman', 'maniac']
            roles = ['head militia', 'neutral doctor', 'maniac']
            mafia = ['mafia']
            killer = ['neutral killer']
            militia = ['militia']
            if len(participants) >= 15:
                roles = roles + killer
            if len(participants) >= 12:
                roles = roles + militia
            if len(participants) <= 18:
                # roles = roles + mafia * 3
                roles = roles + mafia * 2
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
        elif action == 'Dump':
            votes = Vote.objects.filter(game=context['game'])
            game_posts = GamePost.objects.filter(game=context['game'])
            game_comments = GameComment.objects.filter(post__game=context['game'])
            game_participants = GameParticipant.objects.filter(game=context['game'])
            dump = GameDump()
            dump.game = context['game']
            dump.day = context['game'].day
            dump.state = context['game'].state
            dump.status = context['game'].status
            dump.hasHeadMafia = context['game'].hasHeadMafia
            dump.hasRecruit = context['game'].hasRecruit
            dump.votes = ','.join(str(vote.id) for vote in votes)
            dump.game_posts = ','.join(str(post.id) for post in game_posts)
            dump.game_comments = ','.join(str(comment.id) for comment in game_comments)
            d = {}
            for participant in game_participants:
                d[str(participant.id)] = {'role': participant.role, 
                    'prevRole': participant.prevRole, 
                    'prevTarget': participant.prevTarget,
                    'can_ask_killer': participant.can_ask_killer,
                    'can_choose_side': participant.can_choose_side,
                    'sees_maf_q': participant.sees_maf_q,
                    'sees_mil_q': participant.sees_mil_q,
                    'can_recruit': participant.can_recruit,
                    'checked_by_mil': participant.checked_by_mil}
            dump.game_participants = json.dumps(d)
            dump.save()
        elif action == 'Restore Dump':
            dump = GameDump.objects.filter(game=context['game']).last()
            context['game'].day = dump.day
            context['game'].state = dump.state
            context['game'].status = dump.status
            context['game'].hasHeadMafia = dump.hasHeadMafia
            context['game'].hasRecruit = dump.hasRecruit
            context['game'].save()
            context['game'] = Game.objects.filter(number=context['game'].number)

            if dump.votes:
                dump_votes = list(map(int, dump.votes.split(',')))
                votes = Vote.objects.filter(game=context['game'])
                for vote in votes:
                    if vote.id not in dump_votes:
                        vote.delete()
            else:
                votes = Vote.objects.filter(game=context['game']).delete()

            if dump.game_comments:
                dump_comments = list(map(int, dump.game_comments.split(',')))
                game_comments = GameComment.objects.filter(post__game=context['game'])
                for comment in game_comments:
                    if comment.id not in dump_comments:
                        comment.delete()
            else:
                game_comments = GameComment.objects.filter(post__game=context['game']).delete()

            if dump.game_posts:
                dump_posts = list(map(int, dump.game_posts.split(',')))
                game_posts = GamePost.objects.filter(game=context['game'])
                for post in game_posts:
                    if post.id not in dump_posts:
                        post.delete()
            else:
                game_posts = GamePost.objects.filter(game=context['game']).delete()

            d = json.loads(dump.game_participants)
            if len(d) > 0:
                game_participants = GameParticipant.objects.filter(game=context['game'])
                for p in game_participants:
                    p.role = d[str(p.id)]['role']
                    p.prevRole = d[str(p.id)]['prevRole']
                    p.prevTarget = d[str(p.id)]['prevTarget']
                    p.can_ask_killer = d[str(p.id)]['can_ask_killer']
                    p.can_choose_side = d[str(p.id)]['can_choose_side']
                    p.sees_maf_q = d[str(p.id)]['sees_maf_q']
                    p.sees_mil_q = d[str(p.id)]['sees_mil_q']
                    p.can_recruit = d[str(p.id)]['can_recruit']
                    p.checked_by_mil = d[str(p.id)]['checked_by_mil']
                    p.save()
            else:
                game_participants = GameParticipant.objects.filter(game=context['game']).delete()
        elif action == 'Раздать':
            masks = Mask.objects.filter(game=context['game'], taken=False)
            masks = random.sample(list(masks), len(masks))
            participants = random.sample(list(context['participants']), len(context['participants']))
            for participant in participants:
                if not participant.mask:
                    if len(masks) > 0:
                        mask = masks.pop()
                    else:
                        temp = NamedTemporaryFile()
                        temp.write(urllib.request.urlopen('http://www.maf.pub/identicon/').read())
                        temp.flush()
                        mask = Mask(game=context['game'], username='Маска ' + participant.user.nickname)
                        mask.avatar.save(os.path.basename(save_path_avatar(mask, 'avatar.png')), File(temp))
                        mask.save()
                    participant.mask = mask
                    participant.save()
                    participant = GameParticipant.objects.get(id=participant.id)
                    private = GamePost.objects.filter(game=context['game'], tags__contains=['private', participant.user.nickname]).first()
                    private.title = participant.mask.username + '(' + participant.user.nickname + ')'
                    private.save()
                    mask.taken = True
                    mask.save()
        elif action == 'Зал Ожидания':
            bot = User.objects.get(nickname='Игровой Бот')
            departure_area = GamePost(title='Зал Ожидания', text='Зал Ожидания', game=context['game'],
                                      slug=str(context['game'].slug)+'_departure', allow_role=['everyone'],
                                      author=bot, tags=['general_day', 'current'], short=str(context['game'].slug)+'_departure')
            departure_area.save()
        elif action == 'Сохранить':
            form = self.get_form()
            if form.is_valid():
                context['game'] = form.save()
                description = GamePost.objects.get(game=context['game'], tags__contains=['description'])
                description.text = request.POST['description']
                if context['game'].state != 'upcoming':
                    description.allow_comment = False
                if context['game'].state == 'past':
                    gamepost_list = GamePost.objects.filter(game=context['game'])
                    for gamepost in gamepost_list:
                        gamepost.allow_comment = False
                        gamepost.allow_role = ['everyone']
                        gamepost.save()
                if context['game'].state == 'current':
                    private_gamepost_list = GamePost.objects.filter(game=context['game'], tags__contains=['private'])
                    for gamepost in private_gamepost_list:
                        gamepost.allow_comment = True
                        gamepost.save()
                description.save()
                context['description'] = description
            else:
                context['form'] = form
                return render(request, self.template_name, context)
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
        elif action == 'Новый день':
            # t = Timer(1.0, night, args=(request.POST.dict(),))
            # t.start()
            night(request.POST.dict())
        elif action == 'Голосовать':
            simulate_vote(request.POST.dict())
            # vote_hang(request.POST.dict())
        elif action == 'Зарегистрировать':
            register_bots(request.POST.dict())
        elif action == 'Флудить':
            simulate_flood(request.POST.dict())
        elif action == 'Создать':
            create_random_masks(request.POST.dict())
        context = self.get_context_data()
        return HttpResponseRedirect(reverse('mafiaapp:edit_game', kwargs={'pk': context['game'].number}))
        # return render(request, self.template_name, context)


def create_random_masks(d):
    game = Game.objects.get(number=d['game'])
    bot = Mask.objects.get(game=game, username='Игровой Бот')
    participants = GameParticipant.objects.exclude(mask=bot).filter(game=game, mask=None)
    for participant in participants:
        temp = NamedTemporaryFile()
        identicon_url = os.environ.get('IDENTICON_URL', '')
        if identicon_url:
            temp.write(urllib.request.urlopen(identicon_url).read())
        else:
            temp.write(urllib.request.urlopen('http://www.maf.pub/identicon/').read())
        temp.flush()

        mask = Mask(game=game, username='Маска ' + participant.user.nickname, taken=True)
        mask.avatar.save(os.path.basename(save_path_avatar(mask, 'avatar.png')), File(temp))
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
            comment = GameComment(post=mafia_post, text=flood[random.randint(0, len(flood) - 1)], author=maf.user,
                                  mask=maf.mask)
            comment.save()
        for mil in militia:
            comment = GameComment(post=militia_post, text=flood[random.randint(0, len(flood) - 1)], author=mil.user,
                                  mask=mil.mask)
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
            rand = str(random.randint(1, 999999))
            name = 'Бот ' + rand
            available = False if User.objects.filter(nickname=name).first() else True
        user = User.objects.create_user(nickname=name, username=re.sub(r'[^\w.@+-]', '_', name), password='123',
                                        email=rand+'@maf.pub')
        temp = NamedTemporaryFile()
        identicon_url = os.environ.get('IDENTICON_URL', '')
        if identicon_url:
            temp.write(urllib.request.urlopen(identicon_url).read())
        else:
            temp.write(urllib.request.urlopen('http://www.maf.pub/identicon/').read())
        #temp.write(urllib.request.urlopen('http://localhost/identicon/').read())
        temp.flush()
        user.avatar.save(os.path.basename(save_path_avatar(user, 'avatar.png')), File(temp))
        user.save()

        mask = Mask(game=game, username=user.nickname + 'm', taken=True)
        mask.avatar.save(os.path.basename(save_path_avatar(mask, 'avatar.png')), File(temp))
        mask.save()

        participant = GameParticipant(game=game, user=user, mask=mask)
        participant.save()

        private_quarters = GamePost(title='Своя каюта', text='%s' % user.nickname,
                                    game=game, tags=['private', user.nickname],
                                    short='private', author=user, slug=game.slug + '_private_' + user.username,
                                    allow_role=['private'], allow_comment=False)
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
            votes_result += '\n  ' + participant.mask.username + '.' * (
                longest - len(participant.mask.username)) + '.....' \
                            + vote.target.mask.username
        else:
            hang1 = Vote(game=game, day=game.day, voter=participant, action='hang', target=participant)
            hang1.save()
            hang2 = Vote(game=game, day=game.day, voter=participant, action='hang', target=participant)
            hang2.save()
            votes_result += '\n  ' + participant.mask.username + '.' * (longest - len(participant.mask.username)) \
                            + '.....Не голосовал'
    all_votes = Vote.objects.filter(game=game, day=game.day, action='hang')
    # there are no votes for current day, so everybody dies of space plague
    if not all_votes:
        for participant in participants:
            participant.prevRole = participant.role
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
        if participant.role == 'head mafia':
            game.hasHeadMafia = False
            game.save()
        participant.prevRole = participant.role
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
    barman.prevTarget = spoil_vote.target
    barman.save()
    # barman's quarters
    post = GamePost.objects.get(game=game, tags__contains=['private', barman.user.nickname])
    bot = User.objects.get(nickname='Игровой Бот')
    # success_spoil = False
    # barman's target is dead
    if spoil_vote.target.role == 'dead':
        # spoil_vote always shown in night's summary
        success_spoil = True
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
            success_result += '\n  ' + spoil_vote.target.mask.username + ' спасён доктором'
        else:
            success_result += '\n    ' + spoil_vote.target.mask.username + ' убит'
            if spoil_vote.target.role == 'head mafia':
                game.hasHeadMafia = False
                game.save()
            spoil_vote.target.prevRole = spoil_vote.target.role
            spoil_vote.target.role = 'dead'
            spoil_vote.target.save()
            shoot_result = ' Вы убили игрока ' + str(spoil_vote.target.mask.username) + '.'
            # barman's target quarters
            spoil_target_post = GamePost.objects.get(game=game,
                                                     tags__contains=['private', spoil_vote.target.user.nickname])
            spoil_target_result = 'Ночь ' + str(game.day) + ': Вы были убиты в трактире киллером. ' \
                                                            'Можете оставить последнее сообщение.'
            spoil_target_inform = GameComment(post=spoil_target_post, text=spoil_target_result, author=bot)
            spoil_target_inform.save()
        success_shoot = True
    # killer's target is already dead
    if shoot_vote and shoot_vote.target.role == 'dead':
        # shoot_vote always shown in night's summary
        success_result += '\n  ' + shoot_vote.target.mask.username + ' был найден киллером уже мёртвым'
        success_shoot = True
        shoot_result = 'Ночь ' + str(
            game.day) + ': Вам не удалось убить игрока ' + shoot_vote.target.mask.username + '.' + shoot_result
    # killer's target barman's target. no one dies
    elif shoot_vote and spoil_vote and spoil_vote.target == shoot_vote.target:
        # shoot_vote always shown in night's summary
        success_result += '\n  ' + shoot_vote.target.mask.username + ' избежал встречи с киллером'
        success_shoot = True
        shoot_result = 'Ночь ' + str(
            game.day) + ': Вам не удалось убить игрока ' + shoot_vote.target.mask.username + '.' + shoot_result
    # killer's shoot target is doctor's target. doctor heals target.
    elif shoot_vote and heal_vote and heal_vote.target == shoot_vote.target:
        success_result += '\n  ' + shoot_vote.target.mask.username + ' спасён доктором'
        success_shoot = True
        shoot_result = 'Ночь ' + str(
            game.day) + ': Вам не удалось убить игрока ' + shoot_vote.target.mask.username + '.' + shoot_result
        # killer's target quarters
        shoot_target_post = GamePost.objects.get(game=game, tags__contains=['private', shoot_vote.target.user.nickname])
        shoot_target_result = 'Ночь ' + str(game.day) + ': На вас совершил покушение киллер. Доктор спас вам жизнь.'
        shoot_target_inform = GameComment(post=shoot_target_post, text=shoot_target_result, author=bot)
        shoot_target_inform.save()
    elif shoot_vote:
        success_result = '\n  ' + shoot_vote.target.mask.username + ' убит'
        success_shoot = True
        if shoot_vote.target.role == 'head mafia':
            game.hasHeadMafia = False
            game.save()
        shoot_vote.target.prevRole = shoot_vote.target.role
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
            success_result += '\n  ' + spoil_vote.target.mask.username + ' спасён доктором'
        else:
            success_result += '\n  ' + spoil_vote.target.mask.username + ' убит'
            if spoil_vote.target.role == 'head mafia':
                game.hasHeadMafia = False
                game.save()
            spoil_vote.target.prevRole = spoil_vote.target.role
            spoil_vote.target.role = 'dead'
            spoil_vote.target.save()
            shoot_result = ' Вы убили игрока ' + str(spoil_vote.target.mask.username) + '.'
            # barman's target quarters
            spoil_target_post = GamePost.objects.get(game=game,
                                                     tags__contains=['private', spoil_vote.target.user.nickname])
            spoil_target_result = 'Ночь ' + str(game.day) + ': Вы были убиты в трактире мафией. ' \
                                                            'Можете оставить последнее сообщение.'
            spoil_target_inform = GameComment(post=spoil_target_post, text=spoil_target_result, author=bot)
            spoil_target_inform.save()
        success_shot = True
    # head mafia's target is already dead
    if shoot_vote and shoot_vote.target.role == 'dead':
        # shoot_vote always shown in night's summary
        success_result += '\n  ' + shoot_vote.target.mask.username + ' был найден мафией уже мёртвым'
        success_shot = True
        shoot_result = 'Ночь ' + str(
            game.day) + ': Вам не удалось убить игрока ' + shoot_vote.target.mask.username + '.' + shoot_result
    # head mafia's target barman's target. no one dies
    elif shoot_vote and spoil_vote and spoil_vote.target == shoot_vote.target:
        # shoot_vote always shown in night's summary
        success_result += '\n  ' + shoot_vote.target.mask.username + ' избежал встречи с мафией'
        success_shot = True
        shoot_result = 'Ночь ' + str(
            game.day) + ': Вам не удалось убить игрока ' + shoot_vote.target.mask.username + '.' + shoot_result
    # head mafia's target is doctor's target, so doctor heals target. Or, head mafia's target is already dead
    elif shoot_vote and heal_vote and heal_vote.target == shoot_vote.target:
        success_result += '\n  ' + shoot_vote.target.mask.username + ' спасён доктором'
        success_shot = True
        shoot_result = 'Ночь ' + str(
            game.day) + ': Вам не удалось убить игрока ' + shoot_vote.target.mask.username + '.' + shoot_result
        # maniac's target quarters
        shoot_target_post = GamePost.objects.get(game=game, tags__contains=['private', shoot_vote.target.user.nickname])
        shoot_target_result = 'Ночь ' + str(game.day) + ': На вас совершила покушение мафия. Доктор спас вам жизнь.'
        shoot_target_inform = GameComment(post=shoot_target_post, text=shoot_target_result, author=bot)
        shoot_target_inform.save()
    elif shoot_vote:
        success_result += '\n  ' + shoot_vote.target.mask.username + ' убит'
        success_shot = True
        if shoot_vote.target.role == 'head mafia':
            game.hasHeadMafia = False
            game.save()
        shoot_vote.target.prevRole = shoot_vote.target.role
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
            success_result += '\n  ' + spoil_vote.target.mask.username + 'спасён доктором'
        else:
            success_result += '\n  ' + spoil_vote.target.mask.username + ' убит'
            if spoil_vote.target.role == 'head mafia':
                game.hasHeadMafia = False
                game.save()
            spoil_vote.target.prevRole = spoil_vote.target.role
            spoil_vote.target.role = 'dead'
            spoil_vote.target.save()
            shoot_result = ' Вы убили игрока ' + str(spoil_vote.target.mask.username) + '.'
            # barman's target quarters
            spoil_target_post = GamePost.objects.get(game=game,
                                                     tags__contains=['private', spoil_vote.target.user.nickname])
            spoil_target_result = 'Ночь ' + str(game.day) + ': Вы были убиты в трактире маньяком. ' \
                                                            'Можете оставить последнее сообщение.'
            spoil_target_inform = GameComment(post=spoil_target_post, text=spoil_target_result, author=bot)
            spoil_target_inform.save()
        success_shoot = True
    # maniac's target is already dead
    if shoot_vote and shoot_vote.target.role == 'dead':
        # shoot_vote always shown in night's summary
        success_result += '\n  ' + shoot_vote.target.mask.username + ' был найден маньяком уже мёртвым'
        success_shoot = True
        shoot_result = 'Ночь ' + str(
            game.day) + ': Вам не удалось убить игрока ' + shoot_vote.target.mask.username + '.' + shoot_result
    # maniac's target is barman's target. no one dies
    elif shoot_vote and spoil_vote and spoil_vote.target == shoot_vote.target:
        # shoot_vote always shown in night's summary
        success_result += '\n  ' + shoot_vote.target.mask.username + ' избежал встречи с маньяком'
        success_shoot = True
        shoot_result = 'Ночь ' + str(
            game.day) + ': Вам не удалось убить игрока ' + shoot_vote.target.mask.username + '.' + shoot_result
    # maniac's shoot target is doctor's target. doctor heals target.
    elif shoot_vote and heal_vote and heal_vote.target == shoot_vote.target:
        success_result += '\n  ' + shoot_vote.target.mask.username + ' спасён доктором'
        success_shoot = True
        shoot_result = 'Ночь ' + str(
            game.day) + ': Вам не удалось убить игрока ' + shoot_vote.target.mask.username + '.' + shoot_result
        # maniac's target quarters
        shoot_target_post = GamePost.objects.get(game=game, tags__contains=['private', shoot_vote.target.user.nickname])
        shoot_target_result = 'Ночь ' + str(game.day) + ': На вас совершил покушение маньяк. Доктор спас вам жизнь.'
        shoot_target_inform = GameComment(post=shoot_target_post, text=shoot_target_result, author=bot)
        shoot_target_inform.save()
    elif shoot_vote:
        success_result += '\n  ' + shoot_vote.target.mask.username + ' убит'
        success_shoot = True
        if shoot_vote.target.role == 'head mafia':
            game.hasHeadMafia = False
            game.save()
        shoot_vote.target.prevRole = shoot_vote.target.role
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
    return '\n\nПокушение маньяка:' + success_result if success_shoot else ''


def mafia_recruit_check(d):
    game = Game.objects.get(number=d['game'])
    mafia_recruit = GameParticipant.objects.filter(game=game, role='mafia recruit').first()
    # there is no mafia_recruit
    if not mafia_recruit:
        return ''
    # mafia_recruit's quarters
    post = GamePost.objects.get(game=game, tags__contains=['private', mafia_recruit.user.nickname])
    bot = User.objects.get(nickname='Игровой Бот')
    check_result = ''
    barman = GameParticipant.objects.filter(game=game, role__in=['neutral barman', 'mafia barman', 'militia barman']) \
        .first()
    spoil_vote = Vote.objects.filter(game=game, day=game.day, voter=barman, action='spoil').first() if barman else None
    # mafia_recruit is drunk. no one checked
    if spoil_vote and spoil_vote.target == mafia_recruit:
        return ''
    # mafia_recruit is ok. get his target
    else:
        check_vote = Vote.objects.filter(game=game, day=game.day, voter=mafia_recruit, action='check').first()
    # perform check
    # if mafia_recruit's check target is barman, then he checks both barman and barman's target
    if (check_vote and barman and check_vote.target == barman) and (spoil_vote and spoil_vote.target.role != 'dead'):
        check_result = ' Проверка: игрок ' + spoil_vote.target.mask.username + ' - ' + roles_dict[
            spoil_vote.target.role] + '.'
        check_result = 'Ночь ' + str(game.day) + ': Проверка: игрок ' + check_vote.target.mask.username + ' - ' \
                       + roles_dict[check_vote.target.role] + '.' + check_result
    # mafia_recruit's check target is barman's target. no one checked
    elif spoil_vote and check_vote and spoil_vote.target == check_vote.target:
        check_result = 'Ночь ' + str(
            game.day) + ': Вам не удалось проверить игрока ' + check_vote.target.mask.username + '.'
    elif check_vote:
        check_result = 'Ночь ' + str(game.day) + ': Проверка: игрок ' + check_vote.target.mask.username + ' - ' \
                       + roles_dict[check_vote.target.role] + '.' + check_result
    if check_vote:
        inform = GameComment(post=post, text=check_result, author=bot)
        inform.save()
    return ''


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
            # spoil_vote.target.sees_mil_q = True
            spoil_vote.target.checked_by_mil = True
            spoil_vote.target.save()
            # check_result += '\nВы дали доступ в явочную каюту милиции игроку ' + spoil_vote.target.mask.username + '.'
            # spoil_target_post = GamePost.objects.get(game=game, tags__contains=['private',
            #                                                                     spoil_vote.target.user.nickname])
            # spoil_target_result = 'Ночь ' + str(game.day) + ': Милиция дала вам доступом в их явочную каюту.'
            # spoil_target_inform = GameComment(post=spoil_target_post, text=spoil_target_result, author=bot)
            # spoil_target_inform.save()
        if barman.role in militia_roles:
            # barman.sees_mil_q = True
            barman.checked_by_mil = True
            barman.save()
            # check_result += '\nВы дали доступ в явочную каюту милиции игроку ' + barman.mask.username + '.'
            # barman's quarters
            # barman_post = GamePost.objects.get(game=game, tags__contains=['private', barman.user.nickname])
            # barman_result = 'Ночь ' + str(game.day) + ': Милиция дала вам доступом в их явочную каюту.'
            # barman_inform = GameComment(post=barman_post, text=barman_result, author=bot)
            # barman_inform.save()
    # militia's check target is barman's target. no one checked
    elif spoil_vote and check_vote and spoil_vote.target == check_vote.target:
        check_result = 'Ночь ' + str(
            game.day) + ': Вам не удалось проверить игрока ' + check_vote.target.mask.username + '.'
    elif check_vote:
        check_result = 'Ночь ' + str(game.day) + ': Проверка: игрок ' + check_vote.target.mask.username + ' - ' \
                       + roles_dict[check_vote.target.role] + '.' + check_result
        check_vote.target.checked_by_mil = True
        check_vote.target.save()
        """
        if check_vote.target.role in militia_roles:
            check_vote.target.sees_mil_q = True
            check_vote.target.save()
            check_result += '\nВы дали доступ в явочную каюту милиции игроку ' + check_vote.target.mask.username + '.'
            check_vote_target_post = GamePost.objects.get(game=game, tags__contains=['private',
                                                                                     check_vote.target.user.nickname])
            check_vote_target_result = 'Ночь ' + str(game.day) + ': Милиция дала вам доступом в их явочную каюту.'
            check_vote_target_inform = GameComment(post=check_vote_target_post,
                                                   text=check_vote_target_result, author=bot)
            check_vote_target_inform.save()
        """
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
            if spoil_vote.target.role == 'head mafia':
                game.hasHeadMafia = False
                game.save()
            spoil_vote.target.prevRole = spoil_vote.target.role
            spoil_vote.target.role = 'dead'
            spoil_vote.target.checked_by_mil = True
            spoil_vote.target.save()
            arrest_result = 'Ночь ' + str(game.day) + ': Вы арестовали игрока ' + spoil_vote.target.mask.username + '.'
            # barman's target quarters
            spoil_target_post = GamePost.objects.get(game=game, tags__contains=['private',
                                                                                spoil_vote.target.user.nickname])
            spoil_target_result = 'Ночь ' + str(game.day) + ': Вы были арестованы в трактире комиссаром милиции. ' \
                                                            'Можете оставить последнее сообщение.'
            spoil_target_inform = GameComment(post=spoil_target_post, text=spoil_target_result, author=bot)
            spoil_target_inform.save()
        if barman.role in mafia_roles:
            success_result += '\n  ' + barman.mask.username
            success_arrest = True
            barman.prevRole = barman.role
            barman.role = 'dead'
            barman.checked_by_mil = True
            barman.save()
            if arrest_result:
                arrest_result = arrest_result + ' Вы арестовали игрока ' + barman.mask.username + '.'
            else:
                arrest_result = 'Ночь ' + str(game.day) + ': Вы арестовали игрока ' + barman.mask.username + '.'
            # barman's quarters
            barman_post = GamePost.objects.get(game=game, tags__contains=['private', barman.user.nickname])
            barman_result = 'Ночь ' + str(game.day) + \
                            ': Вы были арестованы в трактире комиссаром милиции. Можете оставить последнее сообщение.'
            barman_inform = GameComment(post=barman_post, text=barman_result, author=bot)
            barman_inform.save()
        if spoil_vote.target.role in militia_roles:
            # spoil_vote.target.sees_mil_q = True
            spoil_vote.target.checked_by_mil = True
            spoil_vote.target.save()
            # check_result += '\nВы дали доступ в явочную каюту милиции игроку ' + spoil_vote.target.mask.username + '.'
            # barman's target quarters
            # spoil_target_post = GamePost.objects.get(game=game, tags__contains=['private',
            #                                                                     spoil_vote.target.user.nickname])
            # spoil_target_result = 'Ночь ' + str(game.day) + ': Милиция дала вам доступом в их явочную каюту.'
            # spoil_target_inform = GameComment(post=spoil_target_post, text=spoil_target_result, author=bot)
            # spoil_target_inform.save()
        if barman.role in militia_roles:
            # barman.sees_mil_q = True
            barman.checked_by_mil = True
            barman.save()
            # check_result += '\nВы дали доступ в явочную каюту милиции игроку ' + barman.mask.username + '.'
            # barman's quarters
            # barman_post = GamePost.objects.get(game=game, tags__contains=['private', barman.user.nickname])
            # barman_result = 'Ночь ' + str(game.day) + ': Милиция дала вам доступом в их явочную каюту.'
            # barman_inform = GameComment(post=barman_post, text=barman_result, author=bot)
            # barman_inform.save()
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
            # logger.info('check_vote')
            if check_vote.target.role == 'head mafia':
                # logger.info('check_vote.target.role == "head mafia"')
                game.hasHeadMafia = False
                game.save()
                # logger.info(game.hasHeadMafia)
            check_vote.target.prevRole = check_vote.target.role
            check_vote.target.role = 'dead'
            check_vote.target.save()
            arrest_result = 'Ночь ' + str(game.day) + ': Вы арестовали игрока ' \
                            + check_vote.target.mask.username + '.' + arrest_result
            # head mafia's target quarters
            check_target_post = GamePost.objects.get(game=game,
                                                     tags__contains=['private', check_vote.target.user.nickname])
            check_target_result = 'Ночь ' + str(game.day) + ': Вы были арестованы комиссаром милиции. ' \
                                                            'Можете оставить последнее сообщение.'
            check_target_inform = GameComment(post=check_target_post, text=check_target_result, author=bot)
            check_target_inform.save()
        """
        if check_vote.target.role in militia_roles:
            check_vote.target.sees_mil_q = True
            check_vote.target.save()
            check_result += '\nВы дали доступ в явочную каюту милиции игроку ' + check_vote.target.mask.username + '.'
            check_vote_target_post = GamePost.objects.get(game=game, tags__contains=['private',
                                                                                     check_vote.target.user.nickname])
            check_vote_target_result = 'Ночь ' + str(game.day) + ': Милиция дала вам доступом в их явочную каюту.'
            check_vote_target_inform = GameComment(post=check_vote_target_post,
                                                   text=check_vote_target_result, author=bot)
            check_vote_target_inform.save()
        """
    if check_vote:
        inform = GameComment(post=post, text=check_result, author=bot)
        inform.save()
        if arrest_result:
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
    peaceful = GameParticipant.objects.filter(game=game, role='peaceful')
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
    if maniac and not militia and not mafia or maniac and not peaceful:
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
    quicks = GameParticipant.objects.filter(game=game).exclude(Q(role='dead') | Q(user=author))
    departed = GameParticipant.objects.filter(game=game, role='dead')
    # quicks for general_day and mafia_day
    quicks_info = '\nЖивые:'
    # quicks for militia_day
    checked_quicks_info = '\nЖивые:'
    # departed for general_day and mafia_day
    departed_info = '\nМертвые:'
    # departed for militia_day
    checked_departed_info = '\nМертвые:'
    for x in range(0, len(quicks), 3):
        line = islice(quicks, x, x+3)
        quicks_info += '\n    ' + ', '.join(quick.mask.username for quick in line)
        line = islice(quicks, x, x + 3)
        checked_quicks_info += '\n    ' + ', '.join(
            quick.mask.username+"("+quick.get_literary_role()+")" if quick.checked_by_mil else quick.mask.username
            for quick in line)
    for x in range(0, len(departed), 3):
        line = islice(departed, x, x+3)
        departed_info += '\n    ' + ', '.join(dead.mask.username for dead in line)
        line = islice(departed, x, x + 3)
        checked_departed_info += '\n    ' + ', '.join(
            dead.mask.username + "(" + dead.get_literary_prev_role() + ")" if dead.checked_by_mil else
            dead.mask.username
            for dead in line)
    # logger.info('quicks_info %s', quicks_info)
    # logger.info('checked_quicks_info %s', checked_quicks_info)
    # logger.info('departed_info %s', departed_info)
    # logger.info('checked_departed_info %s', checked_departed_info)
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
            if 'militia_day' in post.tags:
                new_post = GamePost(title='День ' + day, text='МИЛИЦИЯ. День ' + day + checked_quicks_info +
                                                              checked_departed_info, short='day' + day,
                                    tags=post.tags + ['current'],
                                    game=game, author=author, allow_role=post.allow_role, slug=slug)
                new_post.save()
            elif 'mafia_day' in post.tags:
                new_post = GamePost(title='День ' + day, text='МАФИЯ. День ' + day + quicks_info +
                                                              departed_info, short='day' + day,
                                    tags=post.tags + ['current'],
                                    game=game, author=author, allow_role=post.allow_role, slug=slug)
                new_post.save()
            else:
                new_post = GamePost(title='День ' + day, text='День ' + day + quicks_info +
                                                              departed_info, short='day' + day,
                                    tags=post.tags + ['current'],
                                    game=game, author=author, allow_role=post.allow_role, slug=slug)
                new_post.save()
        comment = GameComment(post=post, text='День ' + ('' if game.day == 0 else str(game.day)) +
                                              ' завершен', author=author)
        comment.save()
    mafia_roles = ['mafia', 'head mafia', 'mafia doctor', 'mafia barman', 'mafia killer']
    militia_roles = ['militia', 'head militia', 'militia doctor', 'militia barman', 'militia killer']
    if not has_mafia_post:
        new_recruit_post = GamePost(title='Явочная', text='Явочная мафии', short='day' + day,
                                    tags=['mafia_day', 'mafia_secret'], game=game, author=author,
                                    allow_role=['mafia', 'head mafia', 'mafia recruit', 'militia recruit'],
                                    slug=game.slug + '_mafia_secret')
        new_recruit_post.save()
        new_post = GamePost(title='День ' + day, text='МАФИЯ. День ' + day + quicks_info, short='day' + day,
                            tags=['mafia_day', 'current'],
                            game=game, author=author, allow_role=mafia_roles, slug=game.slug + '_mafia_day' + day)
        new_post.save()
    if not has_militia_post:
        new_recruit_post = GamePost(title='Явочная', text='Явочная милиции', short='day' + day,
                                    tags=['militia_day', 'militia_secret'], game=game, author=author,
                                    allow_role=['militia', 'head militia', 'militia recruit'],
                                    slug=game.slug + '_militia_secret')
        new_recruit_post.save()
        new_post = GamePost(title='День ' + day, text='МИЛИЦИЯ. День ' + day + quicks_info, short='day' + day,
                            tags=['militia_day', 'current'],
                            game=game, author=author, allow_role=militia_roles, slug=game.slug + '_militia_day' + day)
        new_post.save()
    # game may have been updated by performing actions. get actual game
    game = Game.objects.get(number=d['game'])
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
        participants = GameParticipant.objects.filter(game=game)
        for participant in participants:
            for comment in participant.user.gamecomment_set.exclude(post__tags__contains=['description']):
                participant.user.like_number += comment.like
            participant.user.game_number += 1
            participant.user.save()


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
                shoot_choice = random.choice(list(shoot_votes))
                shoot_vote = Vote(game=game, day=game.day, voter=killer, action='shoot', target=shoot_choice.target)
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
                shoot_choice = random.choice(list(shoot_votes))
                shoot_vote = Vote(game=game, day=game.day, voter=killer, action='shoot', target=shoot_choice.target)
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


def neutrals_change_side(d):
    game = Game.objects.get(number=d['game'])
    # side change only performed on the first day(night)
    if game.day > 1:
        return ''
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
    # neutral_killer = GameParticipant.objects.filter(game=game, role='neutral killer').first()
    # neutrals = [neutral_doctor, neutral_killer, neutral_barman]
    neutrals = [neutral_doctor]
    side_result = ''
    for neutral in neutrals:
        if neutral:
            side_result += '\n  ' + roles_dict[neutral.role] + ' - '
            side_vote = Vote.objects.filter(Q(action='mafia_side') | Q(action='militia_side'),
                                            game=game, voter=neutral).first()
            if side_vote:
                neutral.role = roles_map[side_vote.action][neutral.role]
                neutral.save()
                post = GamePost.objects.get(game=game, tags__contains=['private', neutral.user.nickname])
                text = 'Ночь ' + str(game.day) + ': ' + roles_description[neutral.role]
                inform = GameComment(post=post, author=bot, text=text)
                inform.save()
            else:
                random.seed(time.time())
                # repeat mafia_side/militia_side to make it more random
                random_side = random.choice(['mafia_side', 'militia_side', 'mafia_side', 'militia_side',
                                             'mafia_side', 'militia_side', 'mafia_side', 'militia_side'])
                neutral.role = roles_map[random_side][neutral.role]
                neutral.save()
                post = GamePost.objects.get(game=game, tags__contains=['private', neutral.user.nickname])
                inform = GameComment(post=post, author=bot, text='Ночь ' + str(game.day) + ': ' +
                                                                 neutral.mask.username + ' наугад выбрал сторону ' +
                                                                 ('мафии.' if 'mafia' in neutral.role else 'милиции.'))
                inform.save()
            side_result += roles_dict[neutral.role] + '.'
            neutral.can_choose_side = False
            neutral.save()
            # post = GamePost.objects.get(game=game, tags__contains=['private', neutral.user.nickname])
            # inform = GameComment(post=post, author=bot, text=roles_description[neutral.role])
            # inform.save()
            """
            if 'mafia' in neutral.role:
                neutral.sees_maf_q = True
                neutral.save()
            elif ('militia' in neutral.role) and neutral.checked_by_mil:
                neutral.sees_mil_q = True
                neutral.save()
            """
    """
    if not neutral_barman:
        voter = GameParticipant.objects.filter(game=game, prevRole='neutral barman')
        side_vote = Vote.objects.filter(Q(action='mafia_side') | Q(action='militia_side'),
                                        game=game, voter=voter).first()
        if side_vote:
            role = roles_map[side_vote.action]['neutral barman']
        else:
            random.seed(time.time())
            # repeat mafia_side/militia_side to make it more random
            role = random.choice(['mafia barman', 'militia barman', 'mafia barman', 'militia barman',
                                  'mafia barman', 'militia barman', 'mafia barman', 'militia barman'])
        side_result += '\n  ' + roles_dict['neutral barman'] + ' - ' + roles_dict[role] + '.'
    """
    if not neutral_doctor:
        voter = GameParticipant.objects.filter(game=game, prevRole='neutral doctor')
        side_vote = Vote.objects.filter(Q(action='mafia_side') | Q(action='militia_side'),
                                        game=game, voter=voter).first()
        if side_vote:
            role = roles_map[side_vote.action]['neutral doctor']
        else:
            random.seed(time.time())
            # repeat mafia_side/militia_side to make it more random
            role = random.choice(['mafia doctor', 'militia doctor', 'mafia doctor', 'militia doctor',
                                  'mafia doctor', 'militia doctor', 'mafia doctor', 'militia doctor'])
        side_result += '\n  ' + roles_dict['neutral doctor'] + ' - ' + roles_dict[role] + '.'
    """
    if not neutral_killer:
        voter = GameParticipant.objects.filter(game=game, prevRole='neutral killer')
        side_vote = Vote.objects.filter(Q(action='mafia_side') | Q(action='militia_side'),
                                        game=game, voter=voter).first()
        if side_vote:
            role = roles_map[side_vote.action]['neutral killer']
        else:
            random.seed(time.time())
            # repeat mafia_side/militia_side to make it more random
            role = random.choice(['mafia killer', 'militia killer', 'mafia killer', 'militia killer',
                                  'mafia killer', 'militia killer', 'mafia killer', 'militia killer'])
        side_result += '\n  ' + roles_dict['neutral killer'] + ' - ' + roles_dict[role] + '.'
    """
    return ('\n\nВыбор стороны:' + side_result) if len(side_result) > 0 else ''


def recruit_change_side(d):
    game = Game.objects.get(number=d['game'])
    if game.hasRecruit:
        return ''
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
    # check if head mafia tried to recruit somebody
    vote_recruit = Vote.objects.filter(game=game, action='recruit', day=game.day).first()
    # logger.info('======RECRUIT')
    # logger.info(vote_recruit)
    if vote_recruit:
        # mafia did try recruit. check if recruiter chose side
        side_vote = Vote.objects.filter(Q(action='mafia_side') | Q(action='militia_side'),
                                        game=game, voter=vote_recruit.target).first()
        # logger.info(side_vote)
        head_mafia = GameParticipant.objects.filter(game=game, role='head mafia').first()
        vote_recruit.target.can_choose_side = False
        vote_recruit.target.save()
        if vote_recruit.target.role == 'dead':
            vote_recruit.target.can_choose_side = False
            vote_recruit.target.save()
            if head_mafia:
                head_mafia.can_recruit = True
                head_mafia.save()
            recruit_result = 'Ночь ' + str(game.day) + ': Вербовка: игрок ' + vote_recruit.target.mask.username + \
                             ' мёртв. Вербовка не удалась.'
        elif side_vote:
            # recruiter did chose side. change his role
            vote_recruit.target.role = roles_map[side_vote.action][vote_recruit.target.role]
            vote_recruit.target.sees_maf_q = True
            vote_recruit.target.can_choose_side = False
            vote_recruit.target.save()
            game.hasRecruit = True
            game.save()
            recruit_result = 'Ночь ' + str(game.day) + ': Вербовка: игрок ' + vote_recruit.target.mask.username + \
                             ' принимает вербовку. Завербованный теперь имеет доступ к явочной каюте мафии.'
            # logger.info('result %s', recruit_result)
        else:
            # logger.info('no side vote')
            # recruiter did not choose side. head mafia can recruit again
            if head_mafia:
                head_mafia.can_recruit = True
                head_mafia.save()
            recruit_result = 'Ночь ' + str(game.day) + ': Вербовка: игрок ' + vote_recruit.target.mask.username + \
                             ' отказывается от вербовки.'
            # logger.info('recruit result %s', recruit_result)
        recruited_post = GamePost.objects.get(game=game,
                                              tags__contains=['private', vote_recruit.target.user.nickname])
        # logger.info('recruited post %s', recruited_post)
        inform = GameComment(post=recruited_post, text=recruit_result, author=bot)
        inform.save()
        if head_mafia:
            # logger.info('head mafia %s', head_mafia)
            head_mafia_post = GamePost.objects.get(game=game, tags__contains=['private',
                                                                              vote_recruit.voter.user.nickname])
            # logger.info('head mafia psot %s', head_mafia_post)
            inform = GameComment(post=head_mafia_post, text=recruit_result, author=bot)
            inform.save()
    return ''


def change_side(d):
    change_side_result = ''
    change_side_result += neutrals_change_side(d)
    change_side_result += recruit_change_side(d)
    return change_side_result


def refresh_participants_states(d):
    game = Game.objects.get(number=d['game'])
    bot = User.objects.get(nickname='Игровой Бот')
    participants = GameParticipant.objects.filter(game=game).exclude(Q(mask__username='Игровой Бот') | Q(
        role__in=['dead', 'mafia killer', 'militia killer', 'neutral killer']))
    for participant in participants:
        participant.can_ask_killer = True
        participant.save()
    head_militia = GameParticipant.objects.filter(game=game, role='head militia').first()
    if not head_militia:
        militia = GameParticipant.objects.filter(game=game, role='militia').first()
        if militia:
            militia.role = 'head militia'
            militia.save()
            post = GamePost.objects.get(game=game, tags__contains=['private', militia.user.nickname])
            text = 'Ночь ' + str(game.day) + ': ' + roles_description[militia.role]
            inform = GameComment(post=post, author=bot, text=text)
            inform.save()


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
    # report += barman_spoil(d)
    report += doctor_heal(d)
    # create_missing_killer_vote(d)
    # report += killer_kill(d)
    report += maniac_kill_check(d)
    report += head_militia_arrest(d)
    report += mafia_kill(d)
    report += militia_check(d)
    report += mafia_recruit_check(d)
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


class Profile(generic.DetailView):
    template_name = 'mafiaapp/profile.html'
    context_object_name = 'profile'

    def get_object(self, queryset=None):
        return get_object_or_404(User, nickname=self.kwargs['user'])


class UsersActivity(generic.ListView):
    template_name = 'mafiaapp/users_activity.html'
    context_object_name = 'users_list'

    def get_queryset(self):
        return User.objects.all()


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
    if user.user.nickname in game.black_list:
        messages.add_message(request, messages.ERROR, 'Вы не можете принять участие в текущей игре так как находитесь'
                                                      ' в черном списке.')
        return
    participant = GameParticipant(game=game, user=user.user, mask=None)
    participant.save()
    private_quarters = GamePost(title='Своя каюта', text='%s' % user.user.nickname,
                                game=game, tags=['private', user.user.nickname],
                                short='private', author=user.user, slug=game.slug + '_private_' + user.username,
                                allow_role=['private'], allow_comment=False)
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
    game = get_game(kwargs)
    post = get_game_post(kwargs)
    user = get_user(request)

    if 'tales' not in post.tags:
        if user.user.nickname not in game.anchor and 'description' not in post.tags:
            comment_participant = get_object_or_404(GameParticipant, game=game, user=user)
            if post.allow_comment:
                if comment_participant.role == 'dead' and 'private' not in post.tags and 'morgue' not in post.tags:
                    messages.add_message(request, messages.ERROR, '#1 Мёртвых здесь не слышат.')
                    return False
                if 'everyone' not in post.allow_role:
                    if 'private' in post.allow_role:
                        if user.user.nickname not in post.tags:
                            messages.add_message(request, messages.ERROR,
                                                 '#1 Вы не можете оставлять сообщения в данной теме.')
                            return False
                    elif comment_participant.role not in post.allow_role:
                        messages.add_message(request, messages.ERROR, '#2 Вы не можете оставлять сообщения в данной теме.')
                        return False
            else:
                messages.add_message(request, messages.ERROR, '#3 Вы не можете оставлять сообщения в данной теме.')
                return False

    text = request.POST['comment']
    if request.session.get('last_comment_time', ''):
        if int(time.time()) - request.session['last_comment_time'] < 15:
            messages.add_message(request, messages.ERROR, 'Комментарии можно оставлять не чаще одного раза '
                                                          'в 15 секунд. Подождите еще %s сек.' %
                                 (15 - (int(time.time()) - request.session['last_comment_time'])))
            return False
    if not user.is_staff:
        if text.count('\r') >= 25 or len(text) >= 2000:
            messages.add_message(request, messages.ERROR, 'Комментарий должен быть в пределах 25 строк и 2000 знаков.')
            return False

    if 'description' in post.tags or 'tales' in post.tags or user.user.nickname in game.anchor:
        comment = GameComment(post=post, author=user.user, text=text, mask=None)
        comment.save()
        user.user.comments_number += 1
        user.user.save()
    else:
        comment = GameComment(post=post, author=user.user, text=text,
                              mask=comment_participant.mask if user.user.nickname not in game.anchor else None)
        # logger.info(comment.mask)
        comment.save()
        participant = get_object_or_404(GameParticipant, game=game, user=user)
        participant.comments_number += 1
        participant.save()
    request.session['last_comment_time'] = int(time.time())
    return True


@login_required
def post_comment(request, kwargs):
    post = get_post(kwargs)
    user = get_user(request)
    if not post.allow_comment:
        messages.add_message(request, messages.ERROR,
                             '#1 Вы не можете оставлять сообщения в данной теме.')
        return False
    text = request.POST['comment']
    if request.session.get('last_comment_time', ''):
        if int(time.time()) - request.session['last_comment_time'] < 15:
            messages.add_message(request, messages.ERROR, 'Комментарии можно оставлять не чаще одного раза '
                                                          'в 15 секунд. Подождите еще %s сек.' %
                                 (15 - (int(time.time()) - request.session['last_comment_time'])))
            return False
    if not user.is_staff:
        if text.count('\r') >= 25 or len(text) >= 2000:
            messages.add_message(request, messages.ERROR, 'Комментарий должен быть в пределах 25 строк и 2000 знаков.')
            return False
    malformed = ['script', 'onmouseover', 'onerror']
    if any(el in text.lower() for el in malformed):
        return False
    comment = Comment(post=post, author=user.user, text=text)
    comment.save()
    user.user.comments_number += 1
    user.user.save()
    request.session['last_comment_time'] = int(time.time())
    return True


@login_required
def hang(request, kwargs):
    game = get_game(kwargs)
    post = get_game_post(kwargs)
    user = get_user(request)
    voter = GameParticipant.objects.get(user=user, game=game)
    if voter.role == 'dead':
        messages.add_message(request, messages.ERROR, 'Мертвые не выбирают.')
        return False
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
    # though action is success, return False to not scroll to last comment
    return False


@login_required
def dismiss_vote(request, kwargs):
    game = get_game(kwargs)
    post = get_game_post(kwargs)
    user = get_user(request)
    voter = GameParticipant.objects.get(user=user, game=game)
    if voter.role == 'dead':
        messages.add_message(request, messages.ERROR, 'Мертвые не выбирают.')
        return False
    action = request.POST.get('vote_action', '')
    if not action or action not in ['hang', 'shoot', 'spoil', 'check', 'heal',
                                    'mafia_side', 'militia_side', 'contract']:
        messages.add_message(request, messages.ERROR, 'Такой голос не найден.')
        return False
    vote = Vote.objects.filter(game=game, day=game.day, voter=voter, action=action).first()
    if not vote:
        messages.add_message(request, messages.ERROR, 'Такой голос не найден.')
        return False
    vote.delete()
    d = {
        'hang': ' отменяет повешение игрока ',
        'shoot': ' отменяет выстрел в игрока ',
        'spoil': ' отменяет спаивание игрока ',
        'check': ' отменяет проверку игрока ',
        'heal': ' отменяет лечение игрока ',
        # 'mafia_side': ' отменяет выбор стороны мафии игроком ',
        # 'militia_side': ' отменяет выбор стороны милиции игроком ',
        # 'contract': ' отменяет заказ киллеру игрока ',
    }
    text = 'День ' + str(game.day) + ': ' + str(voter.mask) + d[str(action)] + str(vote.target.mask) + '.'
    author = User.objects.get(nickname='Игровой Бот')
    comment = GameComment(post=post, text=text, author=author)
    comment.save()
    # though action is success, return False to not scroll to last comment
    return False


@login_required
def shoot(request, kwargs):
    game = get_game(kwargs)
    post = get_game_post(kwargs)
    user = get_user(request)
    voter = GameParticipant.objects.get(user=user, game=game)
    if voter.role == 'dead':
        messages.add_message(request, messages.ERROR, 'Мертвые не выбирают.')
        return False
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
    # though action is success, return False to not scroll to last comment
    return False


@login_required
def choose_leader(request, kwargs):
    game = get_game(kwargs)
    post = get_game_post(kwargs)
    user = get_user(request)
    voter = GameParticipant.objects.get(user=user, game=game)
    if voter.role == 'dead':
        messages.add_message(request, messages.ERROR, 'Мертвые не выбирают.')
        return False
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
        head_mafia.prevRole = head_mafia.role
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
                              text='День ' + str(game.day) + ': Вы были выбраны главой мафии. '
                                   'Выберите цель для выстрела и цель для вербовки.')
        comment.save()
        # delete 'leader' votes so they wont appear in new voting when head mafia dies
        Vote.objects.filter(game=game, action='leader').delete()
    # though action is success, return False to not scroll to last comment
    return False


@login_required
def check(request, kwargs):
    game = get_game(kwargs)
    post = get_game_post(kwargs)
    user = get_user(request)
    voter = GameParticipant.objects.get(user=user, game=game)
    if voter.role == 'dead':
        messages.add_message(request, messages.ERROR, 'Мертвые не выбирают.')
        return False
    try:
        target = get_object_or_404(GameParticipant, ~Q(user__nickname='Игровой Бот') | ~Q(role='dead'), game=game,
                                   id=int(request.POST['target']))
    except KeyError:
        raise Http404()
    # role with check not allowed to check self
    if voter.id == target.id:
        messages.add_message(request, messages.ERROR, 'Нельзя проверить самого себя.')
        return False
    # militia also can't check head militia
    if voter.role == 'militia':
        head_militia = GameParticipant.objects.filter(game=game, role='head militia').first()
        if head_militia and head_militia.id == target.id:
            messages.add_message(request, messages.ERROR, 'Нельзя проверить своего напарника.')
            return False
    # head militia also can't check militia
    if voter.role == 'head militia':
        militia = GameParticipant.objects.filter(game=game, role='militia').first()
        if militia and militia.id == target.id:
            messages.add_message(request, messages.ERROR, 'Нельзя проверить своего напарника.')
            return False
    vote = Vote.objects.update_or_create(game=game, day=game.day, voter=voter,
                                         action='check', defaults={'target': target})
    author = User.objects.get(nickname='Игровой Бот')
    comment = GameComment(post=post, text=str(vote[0]), author=author)
    comment.save()
    # though action is success, return False to not scroll to last comment
    return False


@login_required
def heal(request, kwargs):
    game = get_game(kwargs)
    post = get_game_post(kwargs)
    user = get_user(request)
    voter = GameParticipant.objects.get(user=user, game=game)
    if voter.role == 'dead':
        messages.add_message(request, messages.ERROR, 'Мертвые не выбирают.')
        return False
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
    # though action is success, return False to not scroll to last comment
    return False


@login_required
def spoil(request, kwargs):
    game = get_game(kwargs)
    post = get_game_post(kwargs)
    user = get_user(request)
    voter = GameParticipant.objects.get(user=user, game=game)
    if voter.role == 'dead':
        messages.add_message(request, messages.ERROR, 'Мертвые не выбирают.')
        return False
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
    # though action is success, return False to not scroll to last comment
    return False


@login_required
def choose_side(request, kwargs):
    game = get_game(kwargs)
    post = get_game_post(kwargs)
    user = get_user(request)
    voter = GameParticipant.objects.get(user=user, game=game)
    if voter.role == 'dead':
        messages.add_message(request, messages.ERROR, 'Мертвые не выбирают.')
        return False

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
    # though action is success, return False to not scroll to last comment
    return False


@login_required
def recruit(request, kwargs):
    game = get_game(kwargs)
    post = get_game_post(kwargs)
    user = get_user(request)
    voter = GameParticipant.objects.get(user=user, game=game)
    if voter.role == 'dead':
        messages.add_message(request, messages.ERROR, 'Мертвые не выбирают.')
        return False
    try:
        target = get_object_or_404(GameParticipant, ~Q(user__nickname='Игровой Бот') | ~Q(role='dead'), game=game,
                                   id=int(request.POST['target']))
    except KeyError:
        raise Http404()
    # head mafia not allowed recruit neither self nor allies, so exclude
    exclude_participants = GameParticipant.objects.filter(game=game, sees_maf_q=True)
    forbidden_ids = [ally.id for ally in exclude_participants]
    if target.id in forbidden_ids:
        messages.add_message(request, messages.ERROR, 'Нельзя проверить себя или союзника.')
        return False
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
    # though action is success, return False to not scroll to last comment
    return False


@login_required
def contract(request, kwargs):
    game = get_game(kwargs)
    post = get_game_post(kwargs)
    user = get_user(request)
    voter = GameParticipant.objects.get(user=user, game=game)
    if voter.role == 'dead':
        messages.add_message(request, messages.ERROR, 'Мертвые не выбирают.')
        return False
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
    # though action is success, return False to not scroll to last comment
    return False


@login_required
def invite(request, kwargs):
    game = get_game(kwargs)
    post = get_game_post(kwargs)
    user = get_user(request)
    voter = GameParticipant.objects.get(user=user, game=game)
    if voter.role == 'dead':
        messages.add_message(request, messages.ERROR, 'Мертвые не выбирают.')
        return False
    author = User.objects.get(nickname='Игровой Бот')
    try:
        target = get_object_or_404(GameParticipant, ~Q(user__nickname='Игровой Бот') | ~Q(role='dead'), game=game,
                                   id=int(request.POST['target']))
    except KeyError:
        raise Http404()
    vote = Vote.objects.update_or_create(game=game, day=game.day, voter=voter,
                                         action='invite', defaults={'target': target})
    comment = GameComment(post=post, text=str(vote[0]), author=author)
    comment.save()
    if 'mafia' in target.role:
        target.sees_maf_q = True
    if 'militia' in target.role:
        target.sees_mil_q = True
    target.save()
    target_post = GamePost.objects.get(game=game, tags__contains=[target.user.nickname])
    invite_result = 'День ' + str(game.day) + ': Вы были добавлены в каюты ' + \
                    ('мафии.' if 'mafia' in target.role else 'милиции.')
    target_inform = GameComment(post=target_post, text=invite_result, author=author)
    target_inform.save()
    # though action is success, return False to not scroll to last comment
    return False


class LikeGameComment(generic.View):
    def get(self, request, *args, **kwargs):
        user = get_user(request)
        comment = get_object_or_404(GameComment, id=kwargs['pk'])
        if user.is_authenticated():
            if comment.id not in request.user.user.liked:
                comment.like += 1
                comment.save()
                user.user.liked += [comment.id]
                user.user.save()
                if comment.post.game.state == 'past' \
                        or 'description' in comment.post.tags \
                        or comment.author.nickname in comment.post.game.anchor:
                    comment.author.like_number += 1
                    comment.author.save()
            else:
                comment.like -= 1
                comment.save()
                request.user.user.liked.remove(comment.id)
                request.user.user.save()
                if comment.post.game.state == 'past' \
                        or 'description' in comment.post.tags \
                        or comment.author.nickname in comment.post.game.anchor:
                    comment.author.like_number -= 1
                    comment.author.save()
        return JsonResponse({'number': comment.like})


class LikeComment(generic.View):
    def get(self, request, *args, **kwargs):
        user = get_user(request)
        comment = get_object_or_404(Comment, id=kwargs['pk'])
        if user.is_authenticated():
            if comment.id not in request.user.user.liked:
                comment.like += 1
                comment.save()
                user.user.liked += [comment.id]
                user.user.save()
                comment.author.like_number += 1
                comment.author.save()
            else:
                comment.like -= 1
                comment.save()
                request.user.user.liked.remove(comment.id)
                request.user.user.save()
                comment.author.like_number -= 1
                comment.author.save()
        return JsonResponse({'number': comment.like})


def preserve_error_messages(request):
    mstore = messages.get_messages(request)
    for m in mstore:
        messages.add_message(request, m.level, m.message, extra_tags=m.extra_tags)


class DisplayGame(generic.ListView):
    template_name = 'mafiaapp/display_game.html'

    def get_queryset(self):
        return get_object_or_404(Game, slug=self.kwargs['game_slug'])

    def get_context_data(self, **kwargs):
        game = kwargs.pop('object_list', self.object_list)
        context = super(DisplayGame, self).get_context_data(**kwargs)
        context['game'] = game

        anonymous = isinstance(self.request.user, AnonymousUser)
        participant = GameParticipant.objects.filter(game=game,
                                                     user=self.request.user).first() if not anonymous else None
        if game.state == 'past':
            context['mafia'] = True
            context['mafia_core'] = True
            context['militia'] = True
            context['militia_core'] = True
        if participant:
            registered = True if participant else False
            context['registered'] = registered
            context['participant'] = participant
            if participant.role:
                if participant.role in ['mafia', 'head mafia', 'mafia doctor', 'mafia barman', 'mafia killer']\
                        and participant.sees_maf_q:
                    context['mafia'] = True
                    context['mafia_core'] = True
                elif participant.role in ['mafia recruit', 'militia recruit']:
                    context['mafia'] = True
                    context['mafia_recruit'] = True
                elif participant.role in ['militia', 'head militia', 'militia doctor', 'militia barman',
                                          'militia killer']\
                        and participant.sees_mil_q:
                    context['militia'] = True
                    context['militia_core'] = True
                elif participant.role in ['militia recruit']:
                    context['militia'] = True
                    context['militia_recruit'] = True
                context['dead'] = True if participant.role == 'dead' else False
        if participant:
            if participant.role in ['mafia doctor', 'mafia barman', 'mafia killer']:
                gamepost_list = GamePost.objects.filter(game=game).exclude(tags__contains=['mafia_secret'])\
                    .order_by('-date')
            elif participant.role in ['militia doctor', 'militia barman', 'militia killer']:
                gamepost_list = GamePost.objects.filter(game=game).exclude(tags__contains=['militia_secret']) \
                    .order_by('-date')
            else:
                gamepost_list = GamePost.objects.filter(game=game).order_by('-date')
        else:
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
                                                                not in ['neutral killer', 'mafia killer',
                                                                        'militia killer'] else False
        can_invite = True if participant.role in ['head mafia', 'head militia'] else False
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
            'can_invite': can_invite,
        }

        # participants to hang
        if allowed_actions['can_hang']:
            # check if voted previously this day
            vote = Vote.objects.filter(game=self.game, day=self.game.day, voter=participant, action='hang').first()
            if vote:
                # make order: [target, queryset w/o target]
                allowed_actions['vote_hang'] = True
                allowed_actions['participants'] = [vote.target] + list(GameParticipant.objects.filter(game=self.game)
                                                                       .exclude(
                    Q(user__nickname='Игровой Бот') | Q(role='dead')).exclude(id=vote.target.id))
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
                    allowed_actions['heal_targets'] = [vote.target] + list(
                        GameParticipant.objects.filter(game=self.game) \
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
                    allowed_actions['heal_targets'] = [vote.target] + list(GameParticipant.objects
                                                                           .filter(game=self.game)
                        .exclude(Q(user__nickname='Игровой Бот') | Q(role='dead'))
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
                    allowed_actions['spoil_targets'] = [vote.target] + list(
                        GameParticipant.objects.filter(game=self.game) \
                            .exclude(id=participant.prevTarget.id).exclude(id=vote.target.id) \
                            .exclude(Q(user__nickname='Игровой Бот') | Q(role='dead')) \
                            .exclude(id=participant.id))
                else:
                    allowed_actions['spoil_targets'] = GameParticipant.objects.filter(game=self.game) \
                        .exclude(id=participant.prevTarget.id) \
                        .exclude(Q(user__nickname='Игровой Бот') | Q(role='dead')) \
                        .exclude(id=participant.id)
            else:
                if vote:
                    # make order: [target, queryset w/o target]
                    allowed_actions['vote_spoil'] = True
                    allowed_actions['spoil_targets'] = [vote.target] + list(GameParticipant.objects
                                                                            .filter(game=self.game)
                        .exclude(Q(user__nickname='Игровой Бот') | Q(role='dead'))
                        .exclude(id=vote.target.id)
                        .exclude(id=participant.id))
                else:
                    allowed_actions['spoil_targets'] = GameParticipant.objects.filter(game=self.game) \
                        .exclude(Q(user__nickname='Игровой Бот') | Q(role='dead')) \
                        .exclude(id=participant.id)

        # killer's targets to shoot
        if allowed_actions['can_shoot'] and participant.role in ['neutral killer', 'mafia killer', 'militia killer']:
            vote = Vote.objects.filter(game=self.game, day=self.game.day, voter=participant, action='shoot').first()
            if vote:
                contract_votes = Vote.objects.filter(game=self.game, day=self.game.day, action='contract') \
                    .exclude(Q(target__role__contains='killer') | Q(target__role__contains='dead')) \
                    .exclude(target=vote.target)
            else:
                contract_votes = Vote.objects.filter(game=self.game, day=self.game.day, action='contract') \
                    .exclude(Q(target__role__contains='killer') | Q(target__role__contains='dead'))
            allowed_actions['vote_shoot'] = True if vote else None
            if len(contract_votes) > 0:
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
                                                                                                        role='mafia')
                    .exclude(id=vote.target.id))
            else:
                allowed_actions['leader_targets'] = GameParticipant.objects.filter(game=self.game, role='mafia')

        # candidates for mafia recruit or militia recruit
        if allowed_actions['can_recruit']:
            # head mafia not allowed recruit neither self nor allies, so exclude
            exclude_participants = GameParticipant.objects.filter(game=self.game, sees_maf_q=True)
            exclude_id_list = []
            for ally in exclude_participants:
                exclude_id_list.append(ally.id)
            allowed_actions['recruit_targets'] = GameParticipant.objects.filter(game=self.game) \
                .exclude(Q(user__nickname='Игровой Бот') | Q(role='dead')).exclude(id__in=exclude_id_list)

        # targets to check
        if allowed_actions['can_check']:
            # check if voted previously this day
            vote = Vote.objects.filter(game=self.game, day=self.game.day, voter=participant, action='check').first()
            # role with check not allowed to check self, so exclude self from check_targets
            exclude_id_list = [participant.id]
            # militia also can't check head militia
            if participant.role == 'militia':
                head_militia = GameParticipant.objects.filter(game=self.game, role='head militia').first()
                if head_militia:
                    exclude_id_list.append(head_militia.id)
            # head militia also can't check militia
            if participant.role == 'head militia':
                militia = GameParticipant.objects.filter(game=self.game, role='militia').first()
                if militia:
                    exclude_id_list.append(militia.id)
            if vote:
                # make order: [target, queryset w/o target]
                allowed_actions['vote_check'] = True
                allowed_actions['check_targets'] = [vote.target] + list(GameParticipant.objects.filter(game=self.game)
                    .exclude(Q(user__nickname='Игровой Бот') | Q(role='dead')).exclude(id=vote.target.id)
                                                                        .exclude(id__in=exclude_id_list))
            else:
                allowed_actions['check_targets'] = GameParticipant.objects.filter(game=self.game) \
                    .exclude(Q(user__nickname='Игровой Бот') | Q(role='dead')).exclude(id__in=exclude_id_list)

        # targets to invite
        if allowed_actions['can_invite']:
            invitees = None
            # invitees for head mafia
            if participant.role == 'head mafia':
                invitees = GameParticipant.objects.filter(game=self.game, sees_maf_q=False)\
                    .filter(Q(role='mafia barman') | Q(role='mafia killer') | Q(role='mafia doctor'))
            # invitees for head militia
            if participant.role == 'head militia':
                invitees = GameParticipant.objects.filter(game=self.game, sees_mil_q=False, checked_by_mil=True) \
                    .filter(Q(role='militia barman') | Q(role='militia killer') | Q(role='militia doctor'))
            allowed_actions['invitees'] = invitees
        return allowed_actions

    def get_context_data(self, **kwargs):
        context = super(DisplayGamePost, self).get_context_data(**kwargs)
        context['game'] = self.game
        context['post'] = self.game_post
        if 'description' in self.game_post.tags:
            #self.template_name = 'mafiaapp/display_post.html'
            participants = GameParticipant.objects.filter(game=self.game).exclude(user__nickname='Игровой Бот')
            context['participants'] = participants
        if self.game.state != 'past':
            if self.request.user.is_authenticated():
                participant = GameParticipant.objects.filter(game=self.game, user=self.request.user).first()
                context['registered'] = True if participant else False
                context['participant'] = participant if participant else None
                context['dead'] = True if participant and participant.role == 'dead' else False
            if 'private' in self.game_post.tags and self.request.user.user.nickname in self.game_post.tags:
                context.update(self.allowed_actions(self.request.user))
        msgs = messages.get_messages(self.request)
        error_messages = [m for m in msgs if 'error' in m.tags]
        if error_messages:
            context['game_comment_form'] = GameCommentForm(initial={'number': self.request.POST.get('number',
                                                                                                    self.game.number),
                                                                    'comment': self.request.session.get('comment', '')})
        else:
            context['game_comment_form'] = GameCommentForm(initial={'number': self.game.number})
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
        'Пригласить': invite,
        'Удалить голос': dismiss_vote,
    }

    def allow_access(self, request):
        if 'everyone' in self.game_post.allow_role or self.game.state == 'past':
            return True
        user = get_user(request)
        if user.is_authenticated():
            if user.user.nickname in self.game.anchor:
                return True
            participant = GameParticipant.objects.filter(game=self.game, user=self.request.user).first()
            if participant:
                if 'private' in self.game_post.allow_role and user.user.nickname in self.game_post.tags:
                    return True
                mafia_core = ['mafia', 'head mafia', 'mafia doctor', 'mafia barman', 'mafia killer']
                militia_core = ['militia', 'head militia', 'militia doctor', 'militia barman', 'militia killer']
                if participant.role == 'militia recruit':
                    if 'mafia_secret' in self.game_post.tags \
                            or 'militia_secret ' in self.game_post.tags and participant.sees_mil_q:
                        return True
                if participant.role == 'mafia recruit' and 'mafia_secret' in self.game_post.tags:
                    return True
                if participant.role in mafia_core:
                    if 'mafia_secret' in self.game_post.tags:
                        # logger.info('mafia secret')
                        if participant.role in ['mafia', 'head mafia', 'mafia recruit', 'militia recruit']:
                            # logger.info(participant.role)
                            return True
                        else:
                            return False
                    if participant.sees_maf_q:
                        return True
                    else:
                        return False
                if participant.role in militia_core:
                    if 'militia_secret' in self.game_post.tags:
                        if participant.role in ['militia', 'head militia', 'militia recruit']:
                            return True
                        else:
                            return False
                    if participant.sees_mil_q:
                        return True
                    else:
                        return False
                if participant.role in self.game_post.allow_role:
                    return True
        return False

    def post(self, request, *args, **kwargs):
        self.game = get_game(kwargs)
        self.game_post = get_game_post(kwargs)
        if not self.allow_access(request):
            raise Http404
        if request.POST.get('action', '') in self.dispatcher.keys():
            result = self.dispatcher[request.POST['action']](request, self.kwargs)
        else:
            raise Http404
        self.object_list = self.get_queryset()
        preserve_error_messages(request)
        request.session['comment'] = request.POST.get('comment', '')
        return HttpResponseRedirect(reverse('mafiaapp:display_game_post',
                                            kwargs={'game_slug': kwargs['game_slug'],
                                                    'post_slug': kwargs['post_slug']}) +
                                    "?page=last" if result else "")

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
        return Comment.objects.filter(post=self.post).order_by('date')

    def get_context_data(self, **kwargs):
        context = super(DisplayPost, self).get_context_data(**kwargs)
        context['post'] = self.post
        msgs = messages.get_messages(self.request)
        error_messages = [m for m in msgs if 'error' in m.tags]
        if error_messages:
            context['comment_form'] = CommentForm(initial={'comment': self.request.session.get('comment', '')})
        else:
            context['comment_form'] = CommentForm()
        return context

    dispatcher = {
        'Опубликовать': post_comment,
    }

    def post(self, request, *args, **kwargs):
        self.post = get_post(kwargs)
        if request.POST.get('action', '') in self.dispatcher.keys():
            result = self.dispatcher[request.POST['action']](request, self.kwargs)
        else:
            raise Http404
        self.object_list = self.get_queryset()
        preserve_error_messages(request)
        request.session['comment'] = request.POST.get('comment', '')
        return HttpResponseRedirect(reverse('mafiaapp:display_post',
                                            kwargs={'post_slug': kwargs['post_slug']}) +
                                    "?page=last" if result else "")

    def get(self, request, *args, **kwargs):
        self.post = get_post(kwargs)
        self.object_list = self.get_queryset()
        context = self.get_context_data()
        return render(request, self.template_name, context=context)


flood = [
    "Широкополосный шум может генерироваться с помощью указанных ранее эффектов, а именно за счет теплового и "
    "дробового шума.",

    "Дробовой шум вакуумного диода является классическим источником широкополосного шума, который особенно удобен "
    "в работе, поскольку напряжение шума можно точно предсказать.",

    "У розового шума равные мощности на каждой октаве, а не на каждой частоте.",
    "Для точного измерения шума необходимо знать эквивалентную «полосу шума», т. е. ширину полосы совершенного "
    "«прямоугольного» фильтра нижних частот, через который бы проходило такое же напряжение шума.",

    "Другой способ изготовить полосовой фильтр для измерения шума-это использовать RLC-схему.",
    "Наиболее точный способ измерения выходного шума - использование выверенного вольтметра среднеквадратичного "
    "(эффективного) напряжения.",

    "Если входной каскад имеет недостаточно высокий коэффициент ослабления флуктуации питания, то это может привести "
    "к возникновению автоколебаний.",

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

    "Итак, Вы собираетесь создать новый [] функциональный, [] императивный, [] объектно-ориентированный, "
    "[] процедурный, [] стековый, [] мультипарадигменный, [] быстрый, [] статически-типизированный, "
    "[] динамически-типизированный, [] чистый, [] богатый, [] не-искусственный, [] наглядный, "
    "[] простой для новичков, [] простой даже для не-программистов, [] абсолютно непостижимый язык программирования.",

    "Задача классификации изображений — это приём начального изображения и вывод его класса (кошка, собака и т.д.) "
    "или группы вероятных классов, которая лучше всего характеризует изображение. Для людей это один из первых "
    "навыков, который они начинают осваивать с рождения.",

    "Первый слой в СНС всегда свёрточный. Вы же помните, какой ввод у этого свёрточного слоя? Как уже говорилось "
    "ранее, вводное изображение — это матрица 32 х 32 х 3 с пиксельными значениями. Легче всего понять, что такое "
    "свёрточный слой, если представить его в виде фонарика, который светит на верхнюю левую часть изображения. "
    "Допустим свет, который излучает этот фонарик, покрывает площадь 5 х 5. А теперь давайте представим, что фонарик "
    "движется по всем областям вводного изображения. В терминах компьютерного обучения этот фонарик называется "
    "фильтром (иногда нейроном или ядром), а области, на которые он светит, называются рецептивным полем "
    "(полем восприятия).",

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

    "Как и в большинстве устройств от Cisco, в межсетевых экранах задачу загрузки выполняет некоторый bootstrap-код, "
    "называемый ROMMON (ROM Monitor). ROMMON в самом начале своей работы выполняет задачи по инициализации аппаратных "
    "компонентов, после чего считывает текущую конфигурацию из NVRAM. В случае отсутствия необходимости перехода в "
    "режим ROM Monitor mode (confreg 0x00), использует GRUB для загрузки образа (загрузочного образа с расширением "
    ".bin) операционной системы, для чего передает ему имя считанного из NVRAM файла.",

    "Ниже приводится коротенький экономический ликбез по трудовой теории стоимости (в авторской интерпретации).",
    "Труд – движитель экономики.",
    "Труд завершается потреблением.",
    "Труд предполагает конечную цель.",
    "Адепты трудовой теории стоимости полагали, будто все продукты должны возмещаться по продолжительности "
    "изготовления.",

    "Если детально не вдаваться в подробности работы данного загрузчика, то можно сказать, что он используется только "
    "в случае загрузки ROMMON'ом образа по протоколу tftp. ROMMON располагает загружаемый образ в физической памяти "
    "с учетом смещения SecondLdr и его заголовка по адресу 0x13FE0, и передает на него управление (1*). Основная "
    "задача этого загрузчика – проверка целостности загружаемого образа, проверка поддержки целевой платформы, "
    "релокация остальной части образа, начиная с BootLdr по адресу 0x100000 и передача управления на его точку входа "
    "(2*).",

    "Не хлебом единым – так сказано в умной книжке.",
    "Обмен должен осуществляться на эквивалентной основе. В связи с этим организуется денежное обращение.",
    "Как в апланате, так и в объективе Петцваля и передний, и задний компоненты представляют собой ахроматические "
    "линзы.",

    "Как у апланатов, так и у объективов Петцваля кривизна поля изображения не исправлена.",
    "Добавление к схеме плосковогнутой рассеивающей линзы позволяет, в значительной степени, исправить кривизну поля "
    "изображения.",

    "В нашей сфере деятельности нам доступны огромные объёмы знаний, в особенности тех, которые позволяют разработчику "
    "стать эффективным.",

    "Последний слой, хоть и находится в конце, один из важных — мы перейдём к нему позже. Давайте подытожим то, в "
    "чём мы уже разобрались. Мы говорили о том, что умеют определять фильтры первого свёрточного слоя. Они "
    "обнаруживают свойства базового уровня, такие как границы и кривые. Как можно себе представить, чтобы предположить "
    "какой тип объекта изображён на картинке, нам нужна сеть, способная распознавать свойства более высокого уровня, "
    "как например руки, лапы или уши. Так что давайте подумаем, как выглядит выходной результат сети после первого "
    "свёрточного слоя. Его размер 28 х 28 х 3 (при условии, что мы используем три фильтра 5 х 5 х 3).  Когда картинка "
    "проходит через один свёрточный слой, выход первого слоя становится вводным значением 2-го слоя.",

    "Но так всё-таки, что для нас значит быть „ведущим“?",
    "Осмысленное запоминание в 9 раз быстрее механического заучивания.",
    "Осмысленность на порядок снижает затраты на усвоение материала.",
    "Регулярность использования нового материала может быть решающим фактором.",
    "При изучении любого языка начинайте пополнять свой словарный запас с заучивания стоп-слов.",
    "Безусловно, компиляция — довольно экзотичное занятие для программиста, где-нибудь в одном ряду с "
    "программированием огромных боевых человекоподобных роботов. Однако у всего этого есть практические применения, "
    "в отличие от многих других экстравагантных программистских хобби.",

    "Когда начинающий программист пытается написать парсер текста, его естественный подход — рекурсивное углубление: "
    "найти начало конструкции (например, {); найти её конец (например, } на том же уровне вложенности); выделить "
    "содержимое конструкции, и пропарсить её рекурсивно.",

    "ДКА (детерминированный конечный автомат) — штука, которая может находиться в одном из N состояний",
    "Как регэкспом обозначить условие «на том же уровне вложенности»?\n"
    "Математики и тут постарались: доказали, что невозможно.",
    "Значит, для парсинга языков, поддерживающих вложенные конструкции (а это все языки сложнее BAT-файлов), нам "
    "потребуется более мощный инструмент, чем регэкспы."
]
