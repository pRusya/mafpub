from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.IndexView.as_view(), name='index'),
    url(r'^register/(?P<code>[a-zA-Z0-9]+)$', views.RegisterView.as_view(), name='register'),

    # TODO
    url(r'^profile/(?P<user>.*?)/$', views.Profile.as_view(), name='profile'),
    url(r'^logout/$', views.Logout.as_view(), name='logout'),

    url(r'^users/$', views.DisplayUsersView.as_view(), name='display_users'),
    url(r'^masks/$', views.DisplayMasksView.as_view(), name='display_masks'),
    url(r'^users/delete/(?P<pk>[0-9]+)/$', views.DeleteUser.as_view(), name='delete_user'),

    url(r'^dashboard/$', views.Dashboard.as_view(), name='dashboard'),
    # game urls
    url(r'^dashboard/games/$', views.DisplayGamesView.as_view(), name='display_games'),
    url(r'^dashboard/games/delete/(?P<pk>[0-9]+)/$', views.DeleteGameView.as_view(), name='delete_game'),
    url(r'^dashboard/games/edit/(?P<pk>[0-9]+)/$', views.EditGameView.as_view(), name='edit_game'),

    url(r'^dashboard/games/(?P<game_slug>game[0-9]+)/$', views.DisplayGame.as_view(), name='display_game'),
    url(r'^dashboard/games/(?P<game_slug>game[0-9]+)/(?P<post_slug>[a-z0-9A-Z_.а-яА-Я]+)/$',
        views.DisplayGamePost.as_view(), name='display_game_post'),
    url(
        r'^dashboard/games/(?P<game_slug>game[0-9]+)/(?P<post_slug>[a-z0-9A-Z_.а-яА-Я]+)/deletecomment/(?P<pk>[0-9]+)/$',
        views.DeleteGameComment.as_view(), name='delete_game_comment'),
    # post urls
    url(r'^dashboard/posts/(?P<post_slug>)[a-z0-9_]+/$', views.DisplayPost.as_view(), name='display_post'),

    url(r'^dashboard/creategame/$', views.CreateGame.as_view(), name='create_game'),
    url(r'^dashboard/creategamepost/$', views.CreateGamePost.as_view(), name='create_game_post'),
    url(r'^dashboard/creategamemask/$', views.CreateGameMask.as_view(), name='create_game_mask'),

    url(r'^dashboard/gameparticipant/(?P<pk>[0-9]+)/$', views.GameParticipantUpdate.as_view(),
        name='participant_update'),

]

"""
from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
"""
