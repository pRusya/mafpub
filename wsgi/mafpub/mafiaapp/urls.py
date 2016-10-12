from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required

from . import views

urlpatterns = [
    url(r'^$', views.IndexView.as_view(), name='index'),
    url(r'^ajax_register', views.AjaxRegister.as_view(), name='ajax_register'),
    url(r'^ajax_login', views.AjaxLogin.as_view(), name='ajax_login'),
    url(r'^register/(?P<code>[a-zA-Z0-9]+)$', views.RegisterView.as_view(), name='register'),

    # password reset links
    url(r'^p/$', views.wrap_password_reset, name='password_reset'),
    url(r'^p/confirm/(?P<uidb64>[0-9A-Za-z_-]+)/(?P<token>[0-9A-Za-z]+-[0-9A-Za-z]+)/$',
        views.wrap_password_reset_confirm, name='password_reset_confirm'),
    url(r'^p/complete/$', views.wrap_password_reset_complete, name='password_reset_complete'),
    url(r'^p/done/$', views.wrap_password_reset_done, name='password_reset_done'),

    url(r'^u/(?P<user>.*?)/$', views.Profile.as_view(), name='profile'),
    url(r'^life/$', staff_member_required(views.UsersActivity.as_view()), name='users_activity'),
    url(r'^logout/$', views.Logout.as_view(), name='logout'),

    url(r'^users/$', staff_member_required(views.DisplayUsersView.as_view()), name='display_users'),
    url(r'^masks/$', staff_member_required(views.DisplayMasksView.as_view()), name='display_masks'),
    url(r'^users/delete/(?P<pk>[0-9]+)/$', staff_member_required(views.DeleteUser.as_view()), name='delete_user'),

    url(r'^dashboard/$', views.Dashboard.as_view(), name='dashboard'),
    # game urls
    url(r'^dashboard/g/games/$', staff_member_required(views.DisplayGamesView.as_view()), name='display_games'),
    url(r'^dashboard/g/games/delete/(?P<pk>[0-9]+)/$', staff_member_required(views.DeleteGameView.as_view()), name='delete_game'),
    url(r'^dashboard/g/games/edit/(?P<pk>[0-9]+)/$', staff_member_required(views.EditGameView.as_view()), name='edit_game'),

    url(r'^dashboard/g/(?P<game_slug>game[0-9]+)/$', views.DisplayGame.as_view(), name='display_game'),
    url(r'^dashboard/g/(?P<game_slug>game[0-9]+)/(?P<post_slug>[a-z0-9A-Z_.а-яА-Я]+)/$',
        views.DisplayGamePost.as_view(), name='display_game_post'),
    url(r'^dashboard/g/(?P<game_slug>game[0-9]+)/(?P<post_slug>[a-z0-9A-Z_.а-яА-Я]+)/deletecomment/(?P<pk>[0-9]+)/$',
        staff_member_required(views.DeleteGameComment.as_view()), name='delete_game_comment'),
    # post urls
    url(r'^dashboard/p/(?P<post_slug>[a-z0-9A-Z_.а-яА-Я]+)/$', views.DisplayPost.as_view(), name='display_post'),
    url(r'^dashboard/p/(?P<post_slug>[a-z0-9A-Z_.а-яА-Я]+)/deletecomment/(?P<pk>[0-9]+)/$',
        staff_member_required(views.DeleteComment.as_view()), name='delete_comment'),

    url(r'^dashboard/creategame/$', staff_member_required(views.CreateGame.as_view()), name='create_game'),
    url(r'^dashboard/creategamepost/$', staff_member_required(views.CreateGamePost.as_view()), name='create_game_post'),
    url(r'^dashboard/creategamemask/$', staff_member_required(views.CreateGameMask.as_view()), name='create_game_mask'),

    url(r'^dashboard/gameparticipant/(?P<pk>[0-9]+)/$', staff_member_required(views.GameParticipantUpdate.as_view()),
        name='participant_update'),
    url(r'^dashboard/like_gc/(?P<pk>[0-9]+)/$', views.LikeGameComment.as_view(), name='like_game_comment'),
    url(r'^dashboard/like_c/(?P<pk>[0-9]+)/$', views.LikeComment.as_view(), name='like_comment'),

    # test login do not expose
    url(r'^login_as/(?P<username>[a-z0-9A-Z_.а-яА-Я]+)/$', staff_member_required(views.LoginAs.as_view()),
        name='login_as')
]

"""
from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
"""
