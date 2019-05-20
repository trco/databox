import requests
from django.views.generic.base import TemplateView
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from django.views import generic
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.shortcuts import render
from django.contrib import messages

from integrations.models import (GoogleOAuth2Token, GithubOAuth2Token,
                                 GithubRepository)
from .forms import SelectRepoForm


class Index(TemplateView):
    template_name = 'pages/index.html'


class SignUp(generic.CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'pages/signup.html'


def login_redirection(request):
    return HttpResponseRedirect(reverse(
            'user_profile',
            args=[request.user.username]
        )
    )


def user_profile(request, username=None):
    context = {}

    if 'repos_list' in request.session:
        request.session['repos_list'] = None

    google_authorized = GoogleOAuth2Token.objects.filter(user=request.user)
    github_authorized = GithubOAuth2Token.objects.filter(user=request.user)
    github_repos = GithubRepository.objects.filter(user=request.user)

    context['user'] = request.user
    context['google_authorized'] = google_authorized
    context['github_authorized'] = github_authorized
    context['github_repos'] = github_repos

    return render(request, 'pages/user_profile.html', context)


def select_github_repository(request):
    context = {}
    repos_list = request.session['repos_list']

    form = SelectRepoForm(
        request.POST or None,
        repos_list=repos_list,
        initial={'user': request.user}
    )
    if form.is_valid():
        repo = form.save()
        messages.success(
            request,
            'Repository {0} succesfully connected.'.format(repo.name)
        )
        return HttpResponseRedirect(reverse(
                'user_profile',
                args=[request.user.username]
            )
        )
    else:
        pass

    context['form'] = form
    context['user'] = request.user

    return render(request, 'pages/select_github_repository.html', context)


def activate_another_github_repository(request):
    token = GithubOAuth2Token.objects.get(user=request.user)

    # Get Github username
    headers = {'Authorization': 'Bearer ' + token.access_token}
    USER_URL = 'https://api.github.com/user'
    response = requests.get(USER_URL, headers=headers).json()

    # Get user repositories
    REPOS_URL = response['repos_url']
    repos = requests.get(REPOS_URL, headers=headers).json()
    repos_list = [repo['name'] for repo in repos]
    request.session['repos_list'] = repos_list

    repos_list = request.session['repos_list']

    return HttpResponseRedirect(reverse('select_github_repository'))


def disconnect_google(request):
    token = GoogleOAuth2Token.objects.get(user=request.user)
    token.delete()

    messages.success(request, 'Google Analytics succesfully disconnected.')

    return HttpResponseRedirect(reverse(
            'user_profile',
            args=[request.user.username]
        )
    )


def disconnect_github(request):
    token = GithubOAuth2Token.objects.get(user=request.user)
    token.delete()

    repos = GithubRepository.objects.filter(user=request.user)
    if repos:
        for repo in repos:
            repo.delete()

    messages.success(request, 'Github and all the repositories succesfully disconnected.')

    return HttpResponseRedirect(reverse(
            'user_profile',
            args=[request.user.username]
        )
    )


def deactivate_github_repository(request, repo_id):
    repo = GithubRepository.objects.get(id=repo_id)
    messages.success(request, 'Repository {0} succesfully deactivated.'.format(repo.name))

    repo.delete()

    return HttpResponseRedirect(reverse(
            'user_profile',
            args=[request.user.username]
        )
    )
