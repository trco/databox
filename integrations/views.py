from requests_oauthlib import OAuth2Session
from databox import Client

import requests

from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect, JsonResponse
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

    print(oauth.get('https://www.googleapis.com/oauth2/v1/userinfo'))

    GoogleOAuth2Token.objects.create(
        user=request.user, access_token=token['access_token'],
        expires=token['expires_at'], refresh_token=token['refresh_token'])

    messages.success(request, 'Google Analytics succesfully connected.')

    return HttpResponseRedirect(reverse(
            'user_profile',
            args=[request.user.username]
        )
    )


def fetch_push_data(request):
    token = GoogleOAuth2Token.objects.get(user=request.user)
    headers = {'Authorization': 'Bearer ' + token.access_token}
    user_info = requests.get('https://www.googleapis.com/oauth2/v1/userinfo', headers=headers).json()

    data = int(user_info['id'])

    client = Client('sjq01fw3zq95c1aeuj6yw')
    test = client.push('data4', 180)

    print(test)

    return JsonResponse(user_info, safe=False)
