from django.views.generic.base import TemplateView
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from django.views import generic
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.shortcuts import render

from integrations.models import GoogleOAuth2Token


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

    google_authorized = GoogleOAuth2Token.objects.filter(user=request.user)

    context['user'] = request.user
    context['google_authorized'] = google_authorized

    return render(request, 'pages/user_profile.html', context)
