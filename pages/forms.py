from django import forms

from integrations.models import GithubRepository


class SelectRepoForm(forms.ModelForm):
    name = forms.ChoiceField(widget=forms.RadioSelect())

    class Meta:
        model = GithubRepository
        exclude = []

    def __init__(self, *args, repos_list=None, **kwargs):
        super(SelectRepoForm, self).__init__(*args, **kwargs)
        CHOICES = [(repo, repo) for repo, repo in enumerate(repos_list)]
        self.fields['name'].choices = CHOICES
