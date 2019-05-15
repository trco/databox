from requests_oauthlib import OAuth2Session

from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages

from .models import GoogleOAuth2Token

client_id = '305201098664-3ve83l14nr1grpd0iejhr0ua32n4r4ks.apps.googleusercontent.com'
client_secret = 'KbaxLRkzXiLktyyeLo1rMIey'
redirect_uri = 'http://127.0.0.1:8000/callback/google'


def authorize_google(request):
    # Check if authorization already saved
    authorization = GoogleOAuth2Token.objects.filter(user=request.user)

    if not authorization:
        scope = [
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile'
        ]

        oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scope)

        authorization_url, state = oauth.authorization_url(
            'https://accounts.google.com/o/oauth2/auth',
            access_type="offline",
            prompt="select_account"
        )

        request.session['oauth_state'] = state

        return redirect(authorization_url)
    else:
        return render(request, 'integrations/already_authorized.html')


def callback_google(request):
    oauth = OAuth2Session(
        client_id,
        state=request.session['oauth_state'],
        redirect_uri=redirect_uri
    )

    token = oauth.fetch_token(
        'https://accounts.google.com/o/oauth2/token',
        authorization_response=request.build_absolute_uri(),
        client_secret=client_secret
    )

    GoogleOAuth2Token.objects.create(
        user=request.user, access_token=token['access_token'],
        expires=token['expires_at'], refresh_token=token['refresh_token'])

    messages.success(request, 'Google Analytics succesfully connected.')

    return HttpResponseRedirect(reverse(
            'user_profile',
            args=[request.user.username]
        )
    )
