import requests
from requests_oauthlib import OAuth2Session

from django.contrib import messages
from django.http import HttpResponseRedirect, HttpResponseBadRequest
from django.shortcuts import redirect
from django.urls import reverse

from setup.settings import CLIENT_ID_GITHUB, CLIENT_SECRET_GITHUB

from .models import GithubOAuth2Token

TOKEN_URL = 'https://github.com/login/oauth/access_token'
REDIRECT_URI = 'http://127.0.0.1:8000/callback/github'
AUTHORIZATION_URL = 'https://github.com/login/oauth/authorize'
USER_URL = 'https://api.github.com/user'


# Authorize access to Github account
def authorize_github(request):
    # Check if GithubOAuth2Token for user already exists
    authorized = GithubOAuth2Token.objects.filter(user=request.user)

    if not authorized:
        oauth = OAuth2Session(CLIENT_ID_GITHUB)

        authorization_url, state = oauth.authorization_url(
            AUTHORIZATION_URL
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
        CLIENT_ID_GITHUB,
        state=oauth_state,
        redirect_uri=REDIRECT_URI
    )
    token = oauth.fetch_token(
        TOKEN_URL,
        authorization_response=request.build_absolute_uri(),
        client_secret=CLIENT_SECRET_GITHUB
    )

    return token


def get_github_username(token):
    """ Get user's username at Github """
    headers = {'Authorization': 'Bearer ' + token['access_token']}
    response = requests.get(USER_URL, headers=headers).json()
    username = response['login']
    repos_url = response['repos_url']
    return username, repos_url, headers


def get_user_repositories(token, repos_url, headers, request):
    """ Get all user repositories at Github """
    repos = requests.get(repos_url, headers=headers).json()
    repos_list = [repo['name'] for repo in repos]
    return repos_list


# Get & create access token
def callback_github(request):
    try:
        oauth_state = request.session['oauth_state']
    except KeyError:
        return HttpResponseBadRequest('Missing OAuth2 state.')

    # Get user's token
    token = get_token(oauth_state, request)
    # Get user's username at Github
    username, repos_url, headers = get_github_username(token)
    # Save user's repositories to session
    repos_list = get_user_repositories(token, repos_url, headers, request)
    # Save repositories to session
    request.session['repos_list'] = repos_list

    # Create user's GithubOAuth2Token
    GithubOAuth2Token.objects.create(
        user=request.user,
        username=username,
        access_token=token['access_token'],
        token_type=token['token_type']
    )

    messages.success(request, 'Github succesfully connected.')

    return HttpResponseRedirect(reverse('select_github_repository'))
