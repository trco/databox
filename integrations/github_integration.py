from databox import Client
import requests
from requests_oauthlib import OAuth2Session

from django.contrib import messages
from django.http import HttpResponseRedirect, JsonResponse, HttpResponseBadRequest
from django.shortcuts import redirect
from django.urls import reverse

from .models import GithubOAuth2Token

client_id = '389a66a5bc2dbc0dac13'
client_secret = 'e72e1fd84e79b145845320f7250240c60db918e8'
token_url = 'https://github.com/login/oauth/access_token'
redirect_uri = 'http://127.0.0.1:8000/callback/github'
authorization_base_url = 'https://github.com/login/oauth/authorize'


# Authorize access to Github account
def authorize_github(request):
    # Check if GithubOAuth2Token for user already exists
    authorized = GithubOAuth2Token.objects.filter(user=request.user)

    if not authorized:
        oauth = OAuth2Session(client_id)

        authorization_url, state = oauth.authorization_url(
            authorization_base_url
        )

        request.session['oauth_state'] = state

        return redirect(authorization_url)
    else:
        messages.warning(request, 'Github already connected!')
        return HttpResponseRedirect(reverse(
                'user_profile',
                args=[request.user.username]
            )
        )


def get_token(oauth_state, request):
    oauth = OAuth2Session(
        client_id,
        state=oauth_state,
        redirect_uri=redirect_uri
    )
    token = oauth.fetch_token(
        token_url,
        authorization_response=request.build_absolute_uri(),
        client_secret=client_secret
    )

    return token


# Get & create access token
def callback_github(request):
    try:
        oauth_state = request.session['oauth_state']
    except KeyError:
        return HttpResponseBadRequest('Missing OAuth2 state.')

    token = get_token(oauth_state, request)

    # Get Github username
    headers = {'Authorization': 'Bearer ' + token['access_token']}
    USER_URL = 'https://api.github.com/user'
    response = requests.get(USER_URL, headers=headers).json()
    username = response['login']

    # Get user repositories
    REPOS_URL = response['repos_url']
    repos = requests.get(REPOS_URL, headers=headers).json()
    repos_list = [repo['name'] for repo in repos]
    request.session['repos_list'] = repos_list

    GithubOAuth2Token.objects.create(
        user=request.user,
        username=username,
        access_token=token['access_token'],
        token_type=token['token_type']
    )

    messages.success(request, 'Github succesfully connected.')

    return HttpResponseRedirect(reverse('select_github_repository'))
