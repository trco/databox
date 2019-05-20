import requests
from requests_oauthlib import OAuth2Session

from django.contrib import messages
from django.http import HttpResponseRedirect, HttpResponseBadRequest
from django.shortcuts import redirect
from django.urls import reverse

from setup.settings import CLIENT_ID_GA, CLIENT_SECRET_GA

from .models import GoogleOAuth2Token

REDIRECT_URI = 'http://127.0.0.1:8000/callback/google'
SCOPE = 'https://www.googleapis.com/auth/analytics.readonly'
AUTHORIZATION_URL = 'https://accounts.google.com/o/oauth2/auth'
TOKEN_URL = 'https://accounts.google.com/o/oauth2/token'
SUMMARIES_URL = 'https://www.googleapis.com/analytics/v3/management/accountSummaries'


# Authorize access to Google Analytics account
def authorize_google(request):
    # Check if GoogleOAuth2Token for user already exists
    authorized = GoogleOAuth2Token.objects.filter(user=request.user)

    if not authorized:
        oauth = OAuth2Session(
            CLIENT_ID_GA,
            redirect_uri=REDIRECT_URI,
            scope=[SCOPE]
        )

        authorization_url, state = oauth.authorization_url(
            AUTHORIZATION_URL,
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
        CLIENT_ID_GA,
        state=oauth_state,
        redirect_uri=REDIRECT_URI
    )
    token = oauth.fetch_token(
        TOKEN_URL,
        authorization_response=request.build_absolute_uri(),
        client_secret=CLIENT_SECRET_GA
    )
    headers = {'Authorization': 'Bearer ' + token['access_token']}
    response = requests.get(
        SUMMARIES_URL,
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
