import requests
from datetime import datetime
from celery.task.schedules import crontab
from celery.decorators import periodic_task
from databox import Client
from requests_oauthlib import OAuth2Session

from .models import GoogleOAuth2Token

client_id = '305201098664-3ve83l14nr1grpd0iejhr0ua32n4r4ks.apps.googleusercontent.com'
client_secret = 'KbaxLRkzXiLktyyeLo1rMIey'
BASE_URL = 'https://www.googleapis.com/analytics/v3/data/ga?'
DATES = '&start-date=today&end-date=today'
METRICS = '&metrics=ga:users,ga:sessions,ga:pageviewsPerSession,ga:bounces,ga:bounceRate'
QUERYSTRING = '{0}{1}'.format(DATES, METRICS)
DATABOX_TOKEN = 'sjq01fw3zq95c1aeuj6yw'
client = Client(DATABOX_TOKEN)

# Helper functions


def fetch_data_from_google_analytics(access_token, profile_id):
    """Fetch data from user's Google Analytics profile"""
    headers = {'Authorization': 'Bearer ' + access_token}

    # Construct fetch_url
    PROFILE = 'ids=ga:{0}'.format(str(profile_id))
    FETCH_URL = '{0}{1}{2}'.format(BASE_URL, PROFILE, QUERYSTRING)

    response = requests.get(FETCH_URL, headers=headers)
    fetched_data = response.json()

    data = fetched_data['totalsForAllResults']
    # data = fetched_data['rows']

    print('Fetching data...')

    return data


def push_data_to_databox(fetched_data):
    """Push data to Databox"""
    today = datetime.today().strftime('%Y-%m-%d')

    response_id = client.insert_all([
        {'key': 'GA Users', 'value': fetched_data['ga:users'], 'date': today},
        {'key': 'GA Sessions', 'value': fetched_data['ga:sessions'], 'date': today},
        {'key': 'GA Page Views Per Session', 'value': fetched_data['ga:pageviewsPerSession'], 'date': today},
        {'key': 'GA Bounces', 'value': fetched_data['ga:bounces'], 'date': today},
        {'key': 'GA Bounce Rate', 'value': fetched_data['ga:bounceRate'], 'date': today},
    ])

    print('Data pushed to Databox!')

    return response_id


def validate_token(user_token):
    """ Validate user's token"""
    VALIDATE_URL = ('https://www.googleapis.com/oauth2/v1/tokeninfo?'
                    'access_token={0}'.format(user_token.access_token))
    response = requests.get(VALIDATE_URL).json()
    token_valid = True if 'error' not in response else False

    print('Validating token...')

    return user_token.access_token if token_valid else None


def get_new_token(user_token):
    REFRESH_URL = 'https://accounts.google.com/o/oauth2/token'
    refresh_token = {'refresh_token': user_token.refresh_token}

    extra = {
        'client_id': client_id,
        'client_secret': client_secret,
    }

    oauth = OAuth2Session(client_id, token=refresh_token)
    new_token = oauth.refresh_token(REFRESH_URL, **extra)

    return new_token


def refresh_token(user_token):
    """Refresh user's token"""
    new_token = get_new_token(user_token)

    # Update expired user's token
    user_token.access_token = new_token['access_token']
    user_token.expires = new_token['expires_at']
    user_token.refresh_token = new_token['refresh_token']
    user_token.save()

    print('Refreshing token...')

    return new_token['access_token']


@periodic_task(
    run_every=(crontab(minute='*/1')),  # TODO: Really needed?
    name='google_analytics_fetch_push',  # TODO: Really needed?
    # ignore_result=True
)
def google_analytics_fetch_push():
    """Fetch data from Google Analytics and push them to Databox"""
    tokens = GoogleOAuth2Token.objects.all()

    for user_token in tokens:
        # TODO: Update token if expired
        access_token = validate_token(user_token)
        if not access_token:
            access_token = refresh_token(user_token)
        fetched_data = fetch_data_from_google_analytics(access_token, user_token.profile_id)
        push_id = push_data_to_databox(fetched_data)

        return fetched_data, 'push_id: {0}'.format(push_id)
