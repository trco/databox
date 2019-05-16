from django.db import models
from django.conf import settings


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
