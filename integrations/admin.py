from django.contrib import admin

from .models import GoogleOAuth2Token, GithubOAuth2Token, GithubRepository

admin.site.register(GoogleOAuth2Token)
admin.site.register(GithubOAuth2Token)
admin.site.register(GithubRepository)
