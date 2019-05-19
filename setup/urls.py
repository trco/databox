from django.contrib import admin
from django.urls import path, include

from integrations import views as integrations_views
from integrations import github_integration
from pages import views as pages_views

urlpatterns = [
    # App urls
    path('', pages_views.Index.as_view(), name='index'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/signup/', pages_views.SignUp.as_view(), name='signup'),
    path('login/redirection/', pages_views.login_redirection, name='login_redirection'),
    path('profile/<str:username>', pages_views.user_profile,
         name='user_profile'),
    path('admin/', admin.site.urls),

    # Google Analytics integration urls
    path('authorize/google',
         integrations_views.authorize_google,
         name='authorize_google'),
    path('callback/google',
         integrations_views.callback_google,
         name='callback_google'),
    path('fetch/', integrations_views.google_analytics_fetch_push, name='google_analytics_fetch_push'),

    # Github integration urls
    path('authorize/github',
         github_integration.authorize_github,
         name='authorize_github'),
    path('callback/github',
         github_integration.callback_github,
         name='callback_github'),
    path('select-repository/github',
         pages_views.select_github_repository,
         name='select_github_repository'),
    path('activate-another-repository/github',
         pages_views.activate_another_github_repository,
         name='activate_another_github_repository'),
    # path('fetch/', integrations_views.google_analytics_fetch_push, name='google_analytics_fetch_push'),
]
