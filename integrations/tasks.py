import requests
from celery.task.schedules import crontab
from celery.decorators import periodic_task
from databox import Client

from .models import GoogleOAuth2Token


@periodic_task(
    run_every=(crontab(minute='*/1')),
    name='google_analytics_fetch_push_data',
    # ignore_result=True
)
def google_analytics_fetch_push_data():
    tokens = GoogleOAuth2Token.objects.all()

    for user_token in tokens:
        # Get user's GoogleOAuth2Token
        headers = {'Authorization': 'Bearer ' + user_token.access_token}

        # Construct fetch_url
        base = 'https://www.googleapis.com/analytics/v3/data/ga?'
        profile = 'ids=ga:' + str(user_token.profile_id)
        metrics = '&start-date=today&end-date=today&metrics=ga:users,ga:sessions,ga:pageviewsPerSession,ga:bounces,ga:bounceRate'
        fetch_url = '{0}{1}{2}'.format(base, profile, metrics)

        # Fetch data from user's Google Analytics profile
        data = requests.get(fetch_url, headers=headers).json()
        print(data)
        totals = data['totalsForAllResults']

        # Push data to Databox
        # TODO: Set today's date
        client = Client('sjq01fw3zq95c1aeuj6yw')
        client.insert_all([
            {'key': 'GA Users', 'value': totals['ga:users'], 'date': '2019-05-16'},
            {'key': 'GA Sessions', 'value': totals['ga:sessions'], 'date': '2019-05-16'},
            {'key': 'GA Page Views Per Session', 'value': totals['ga:pageviewsPerSession'], 'date': '2019-05-16'},
            {'key': 'GA Bounces', 'value': totals['ga:bounces'], 'date': '2019-05-16'},
            {'key': 'GA Bounce Rate', 'value': totals['ga:bounceRate'], 'date': '2019-05-16'},
        ])

        return totals['ga:users'], totals['ga:sessions'], totals['ga:pageviewsPerSession'], totals['ga:bounces'], totals['ga:bounceRate']
