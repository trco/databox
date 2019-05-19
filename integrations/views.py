from databox import Client
import requests
from requests_oauthlib import OAuth2Session

from django.contrib import messages
from django.http import HttpResponseRedirect, JsonResponse, HttpResponseBadRequest
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


def google_analytics_fetch_push(request):
    # Get user's GoogleOAuth2Token
    user_token = GoogleOAuth2Token.objects.get(user=request.user)
    headers = {'Authorization': 'Bearer ' + user_token.access_token}

    # Construct fetch_url
    base = 'https://www.googleapis.com/analytics/v3/data/ga?'
    profile = 'ids=ga:' + str(user_token.profile_id)
    metrics = '&start-date=today&end-date=today&metrics=ga:users,ga:sessions,ga:pageviewsPerSession,ga:bounces,ga:bounceRate'
    fetch_url = '{0}{1}{2}'.format(base, profile, metrics)

    # Fetch data from user's Google Analytic profile
    print(type(requests.get(fetch_url, headers=headers)))
    data = requests.get(fetch_url, headers=headers).json()
    totals = data['totalsForAllResults']

    # Push data to Databox
    # TODO: Set today's date
    client = Client('sjq01fw3zq95c1aeuj6yw')
    client.insert_all([
        {'key': 'GA Users', 'value': totals['ga:users'], 'date': '2019-02-16'},
        {'key': 'GA Sessions', 'value': totals['ga:sessions'], 'date': '2019-02-16'},
        {'key': 'GA Page Views Per Session', 'value': totals['ga:pageviewsPerSession'], 'date': '2019-02-16'},
        {'key': 'GA Bounces', 'value': totals['ga:bounces'], 'date': '2019-02-16'},
        {'key': 'GA Bounce Rate', 'value': totals['ga:bounceRate'], 'date': '2019-02-16'},
    ])

    return JsonResponse(data, safe=False)
