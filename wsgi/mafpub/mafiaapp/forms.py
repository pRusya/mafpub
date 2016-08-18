import os
import re
import urllib
import urllib.request

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from django.forms import ModelForm, Form
from django.db import models

from pagedown.widgets import PagedownWidget

from .models import *


class EmailValidationForm(ModelForm):
    class Meta:
        model = EmailValidation
        fields = ['email']


class UserCreateForm(UserCreationForm):
    custom_error_messages = {
        'invalid': 'Не верное значение',
        'required': 'Заполните это поле',
        'password_mismatch': 'Пароли не совпадают',
        'unique': "Пользователь с таким именем уже существует",
    }
    #email = forms.EmailField(required=True, disabled=True, label='Электропочта')
    email = forms.EmailField(required=True, label='Электропочта')
    avatar = forms.ImageField(label='Аватар(не обязательно)', required=False)
    nickname = forms.CharField(label="Форумное имя", error_messages=custom_error_messages)
    password1 = forms.CharField(label="Пароль", widget=forms.PasswordInput, required=True,
                                error_messages=custom_error_messages)
    password2 = forms.CharField(label="Пароль еще раз", widget=forms.PasswordInput, required=True,
                                error_messages=custom_error_messages)

    class Meta:
        model = User
        fields = ('nickname', 'password1', 'password2', 'avatar', 'email')

    def save(self, commit=True):
        user = super(UserCreateForm, self).save(commit=False)
        user.email = self.cleaned_data['email']
        user.username = re.sub(r'[^\w.@+-]', '_', user.nickname)
        #user.username = user.username.encode('utf-8')
        if self.cleaned_data['avatar'] is None:
            temp = NamedTemporaryFile()
            temp.write(urllib.request.urlopen('http://www.maf.pub/identicon/').read())
            temp.flush()
            user.avatar.save(os.path.basename(save_path_avatar(user, 'avatar.png')), File(temp))
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField()


class CreateGameForm(ModelForm):
    description = forms.CharField(widget=forms.Textarea, label='Описание')
    anchor = forms.MultipleChoiceField(choices=[(user.nickname, user.nickname) for user in User.objects.all()],
                                       label='Ведущие')
    black_list = forms.MultipleChoiceField(choices=[(user.nickname, user.nickname) for user in User.objects.all()],
                                           label='Бан', required=False)
    widgets = {
        'anchor': forms.SelectMultiple(attrs={'class': 'form-control'}),
        'black_list': forms.SelectMultiple(attrs={'class': 'form-control'}),
    }

    class Meta:
        model = Game
        anchor = forms.MultipleChoiceField(choices=[(user.nickname, user.nickname) for user in User.objects.all()],
                                           label='Ведущие')
        black_list = forms.MultipleChoiceField(choices=[(user.nickname, user.nickname) for user in User.objects.all()],
                                               label='Бан', required=False)
        fields = ['number', 'title', 'description', 'status', 'state', 'day', 'hasHeadMafia', 'hasRecruit', 'anchor',
                  'slug', 'black_list']  # '__all__'
        widgets = {
            'anchor': forms.SelectMultiple(attrs={'class': 'form-control'}),
            'black_list': forms.SelectMultiple(attrs={'class': 'form-control'}),
        }


class CreateGamePostForm(ModelForm):
    allow_role = forms.MultipleChoiceField(choices=GamePost.ALLOW_ROLE_CHOICES)
    tags = forms.MultipleChoiceField(choices=GamePost.TAGS_CHOICES)
    widgets = {
            'allow_role': forms.SelectMultiple(attrs={'class': 'form-control'}),
            'tags': forms.SelectMultiple(attrs={'class': 'form-control'})
        }

    class Meta:
        model = GamePost
        #allow_role = forms.MultipleChoiceField(choices=GamePost.ALLOW_ROLE_CHOICES)
        #tags = forms.MultipleChoiceField(choices=GamePost.TAGS_CHOICES)
        fields = ['title', 'text', 'game', 'tags', 'short', 'slug', 'allow_role']  # '__all__'
        #widgets = {
        #    'allow_role': forms.SelectMultiple(attrs={'class': 'form-control'}),
        #    'tags': forms.SelectMultiple(attrs={'class': 'form-control'})
        #}




class CreateGameMaskForm(ModelForm):
    class Meta:
        model = Mask
        fields = '__all__'


class UpdateGameParticipantForm(ModelForm):
    class Meta:
        model = GameParticipant
        fields = ['user', 'mask', 'role', 'prevTarget', 'can_ask_killer', 'can_choose_side', 'sees_maf_q',
                  'sees_mil_q', 'can_recruit', 'checked_by_mil']


class GameCommentForm(Form):
    number = forms.CharField(widget=forms.HiddenInput)
    comment = forms.CharField(label='Сообщение', widget=PagedownWidget)
