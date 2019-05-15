from django.db import models
from django.conf import settings


class GoogleOAuth2Token(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    access_token = models.TextField()
    refresh_token = models.TextField()
    expires = models.FloatField()
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
