import requests
from datetime import datetime

from celery.decorators import periodic_task
from celery.task.schedules import crontab
from databox import Client
from requests_oauthlib import OAuth2Session

from setup.settings import CLIENT_ID_GA, CLIENT_SECRET_GA, DATABOX_TOKEN

from .models import GoogleOAuth2Token, GithubOAuth2Token, GithubRepository

BASE_URL = 'https://www.googleapis.com/analytics/v3/data/ga?'
DATES = '&start-date=today&end-date=today'
METRICS = '&metrics=ga:users,ga:sessions,ga:pageviewsPerSession,ga:bounces,ga:bounceRate'
QUERYSTRING = '{0}{1}'.format(DATES, METRICS)
client = Client(DATABOX_TOKEN)


# Google Analytics task

@periodic_task(
    run_every=(crontab(minute='*/1')),
    name='google_analytics_fetch_push'
)
def google_analytics_fetch_push():
    """Fetch data from Google Analytics and push them to Databox"""
    tokens = GoogleOAuth2Token.objects.all()

    if tokens:
        for user_token in tokens:
            # 1. Validate token
            access_token = validate_token(user_token)

            if not access_token:
                access_token = refresh_token(user_token)

            # 2. Fetch data from Google Analytics
            fetched_data = fetch_data_from_ganalytics(access_token, user_token.profile_id)

            # 3. Push data to Databox
            push_id = push_ganalytics_data_to_databox(fetched_data)

            return fetched_data, 'push_id: {0}'.format(push_id)
    else:
        return 'Skipped'


# Google Analytics helper functions

def fetch_data_from_ganalytics(access_token, profile_id):
    """Fetch data from user's Google Analytics profile"""
    headers = {'Authorization': 'Bearer ' + access_token}

    # Construct fetch_url
    PROFILE = 'ids=ga:{0}'.format(str(profile_id))
    FETCH_URL = '{0}{1}{2}'.format(BASE_URL, PROFILE, QUERYSTRING)

    response = requests.get(FETCH_URL, headers=headers)
    fetched_data = response.json()

    data = fetched_data['totalsForAllResults']

    return data


def push_ganalytics_data_to_databox(fd):
    """Push data to Databox"""
    today = datetime.today().strftime('%Y-%m-%d')

    response_id = client.insert_all([
        {'key': 'GA Users', 'value': fd['ga:users'], 'date': today},
        {'key': 'GA Sessions', 'value': fd['ga:sessions'], 'date': today},
        {'key': 'GA Page Views Per Session', 'value': fd['ga:pageviewsPerSession'], 'date': today},
        {'key': 'GA Bounces', 'value': fd['ga:bounces'], 'date': today},
        {'key': 'GA Bounce Rate', 'value': fd['ga:bounceRate'], 'date': today},
    ])

    return response_id


def validate_token(user_token):
    """ Validate user's token"""
    VALIDATE_URL = ('https://www.googleapis.com/oauth2/v1/tokeninfo?'
                    'access_token={0}'.format(user_token.access_token))
    response = requests.get(VALIDATE_URL).json()
    token_valid = True if 'error' not in response else False

    return user_token.access_token if token_valid else None


def refresh_token(user_token):
    """Refresh user's token"""
    new_token = get_new_token(user_token)

    # Update expired user's token
    user_token.access_token = new_token['access_token']
    user_token.expires = new_token['expires_at']
    user_token.refresh_token = new_token['refresh_token']
    user_token.save()

    return new_token['access_token']


def get_new_token(user_token):
    REFRESH_URL = 'https://accounts.google.com/o/oauth2/token'
    refresh_token = {'refresh_token': user_token.refresh_token}

    extra = {
        'client_id': CLIENT_ID_GA,
        'client_secret': CLIENT_SECRET_GA,
    }

    oauth = OAuth2Session(CLIENT_ID_GA, token=refresh_token)
    new_token = oauth.refresh_token(REFRESH_URL, **extra)

    return new_token


# Github task

@periodic_task(
    run_every=(crontab(minute='*/1')),
    name='github_fetch_push'
)
def github_fetch_push():
    """Fetch data from Github and push them to Databox"""
    tokens = GithubOAuth2Token.objects.all()

    if tokens:
        fetched_data_list = []

        for user_token in tokens:
            # Get user's activated repositories
            repositories = GithubRepository.objects.filter(user=user_token.user)

            for repo in repositories:
                # 1. Fetch data for repository
                fetched_data = fetch_data_from_github(user_token, repo)
                fetched_data_list.append(fetched_data)

                # 2. Push data for the repository to Databox
                push_github_data_to_databox(fetched_data)

        return fetched_data_list, 'username: {0}'.format(user_token.username)

    else:
        return 'Skipped'


# Github helper functions

def fetch_data_from_github(user_token, repository):
    """Fetch data from user's Github profile"""
    headers = {'Authorization': 'Bearer ' + user_token.access_token}

    # Construct fetch_url
    REPO = repository.name
    USER = user_token.username
    FETCH_URL = 'https://api.github.com/repos/{0}/{1}'.format(USER, REPO)

    response = requests.get(FETCH_URL, headers=headers)
    fetched_data = response.json()

    data = {
        'repo': REPO,
        'forks_count': fetched_data['forks_count'],
        'stargazers_count': fetched_data['stargazers_count'],
        'watchers_count': fetched_data['watchers_count'],
        'open_issues_count': fetched_data['open_issues_count'],
        'subscribers_count': fetched_data['subscribers_count']
    }

    return data


def push_github_data_to_databox(fd):
    """Push data to Databox"""
    today = datetime.today().strftime('%Y-%m-%d')

    response_id = client.insert_all([
        {'key': fd['repo'] + ' forks_count', 'value': fd['forks_count'], 'date': today},
        {'key': fd['repo'] + ' stargazers_count', 'value': fd['stargazers_count'], 'date': today},
        {'key': fd['repo'] + ' watchers_count', 'value': fd['watchers_count'], 'date': today},
        {'key': fd['repo'] + ' open_issues_count', 'value': fd['open_issues_count'], 'date': today},
        {'key': fd['repo'] + ' subscribers_count', 'value': fd['subscribers_count'], 'date': today},
    ])

    return response_id
