from django.conf import settings
from django.db import models


class GoogleOAuth2Token(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    profile_id = models.IntegerField(null=True)
    access_token = models.TextField(null=True)
    refresh_token = models.TextField(null=True)
    expires = models.FloatField(null=True)
    created_on = models.DateTimeField(auto_now_add=True, null=True)
    updated_on = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return 'Google Analytics token for: {0}'.format(self.user)


class GithubOAuth2Token(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    username = models.TextField(null=True)
    access_token = models.TextField(null=True)
    token_type = models.TextField(null=True)
    created_on = models.DateTimeField(auto_now_add=True, null=True)
    updated_on = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return 'Github token for: {0}'.format(self.user)


class GithubRepository(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    name = models.TextField(null=True)

    def __str__(self):
        return 'Repository: {0} / User: {1}'.format(self.name, self.user)
