from django.contrib import admin
from django.urls import path, include

from integrations import views as integrations_views
from pages import views as pages_views

urlpatterns = [
    path('', pages_views.Index.as_view(), name='index'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/signup/', pages_views.SignUp.as_view(), name='signup'),
    path('login/redirection/', pages_views.login_redirection, name='login_redirection'),
    path('profile/<str:username>', pages_views.user_profile,
         name='user_profile'),
    path('admin/', admin.site.urls),
    path('authorize/google',
         integrations_views.authorize_google,
         name='authorize_google'),
    path('callback/google',
         integrations_views.callback_google,
         name='callback_google'),
    path('fetch/', integrations_views.google_analytics_fetch_push_data, name='google_analytics_fetch_push_data'),
]
