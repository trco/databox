import requests
from requests_oauthlib import OAuth2Session

from django.contrib import messages
from django.http import HttpResponseRedirect, HttpResponseBadRequest
from django.shortcuts import redirect
from django.urls import reverse

from .models import GoogleOAuth2Token

client_id = '305201098664-3ve83l14nr1grpd0iejhr0ua32n4r4ks.apps.googleusercontent.com'
client_secret = 'KbaxLRkzXiLktyyeLo1rMIey'
redirect_uri = 'http://127.0.0.1:8000/callback/google'


# Authorize access to Google Analytics account
def authorize_google(request):
    # Check if GoogleOAuth2Token for user already exists
    authorized = GoogleOAuth2Token.objects.filter(user=request.user)

    if not authorized:
        oauth = OAuth2Session(
            client_id,
            redirect_uri=redirect_uri,
            scope=['https://www.googleapis.com/auth/analytics.readonly']
        )

        authorization_url, state = oauth.authorization_url(
            'https://accounts.google.com/o/oauth2/auth',
            access_type="offline",
            prompt="select_account"
        )

        request.session['oauth_state'] = state

        return redirect(authorization_url)
    else:
        messages.warning(request, 'Google Analytics already connected!')
        return HttpResponseRedirect(reverse(
                'user_profile',
                args=[request.user.username]
            )
        )


def get_token_and_profile_id(oauth_state, request):
    oauth = OAuth2Session(
        client_id,
        state=oauth_state,
        redirect_uri=redirect_uri
    )
    token = oauth.fetch_token(
        'https://accounts.google.com/o/oauth2/token',
        authorization_response=request.build_absolute_uri(),
        client_secret=client_secret
    )
    headers = {'Authorization': 'Bearer ' + token['access_token']}
    response = requests.get(
        'https://www.googleapis.com/analytics/v3/management/accountSummaries',
        headers=headers).json()
    profile_id = response['items'][0]['webProperties'][0]['profiles'][0]['id']
    return token, profile_id


# Get & create access token
def callback_google(request):
    try:
        oauth_state = request.session['oauth_state']
    except KeyError:
        return HttpResponseBadRequest('Missing OAuth2 state.')

    token, profile_id = get_token_and_profile_id(oauth_state, request)

    GoogleOAuth2Token.objects.create(
        user=request.user,
        profile_id=profile_id,
        access_token=token['access_token'],
        expires=token['expires_at'],
        refresh_token=token['refresh_token']
    )

    messages.success(request, 'Google Analytics succesfully connected.')

    return HttpResponseRedirect(reverse(
            'user_profile',
            args=[request.user.username]
        )
    )
