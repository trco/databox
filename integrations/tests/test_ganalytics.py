import re
import requests
from unittest.mock import patch
from datetime import datetime

from urllib.parse import unquote
from django.contrib.auth.models import User
from django.test import TestCase

from ..models import GoogleOAuth2Token
from ..tasks import (fetch_data_from_ganalytics,
                     push_ganalytics_data_to_databox,
                     validate_token,
                     refresh_token)

BASE_URL = 'https://www.googleapis.com/analytics/v3/data/ga?'
DATES = '&start-date=today&end-date=today'
METRICS = '&metrics=ga:users,ga:sessions,ga:pageviewsPerSession,ga:bounces,ga:bounceRate'
QUERYSTRING = '{0}{1}'.format(DATES, METRICS)


class AuthorizeGoogleAnalyticsTest(TestCase):

    def setUp(self):
        # Create user
        self.user = User.objects.create_user(
            username='user',
            password='test1234'
        )
        # Login user
        self.client.login(username='user', password='test1234')

    def test_authorization_doesnt_exist(self):
        response = self.client.get('/authorize/google', follow=True)
        redirect_url, status_code = response.redirect_chain[-1]
        redirect_url = unquote(unquote(redirect_url))

        # Check if all parameters from OAuth2Session are in redirect_url
        params = [
            'redirect_uri=http://127.0.0.1:8000/callback/google',
            'scope=https://www.googleapis.com/auth/analytics.readonly',
            'access_type=offline',
            'prompt=select_account',
        ]
        p_in_params = [p in redirect_url for p in params]
        self.assertTrue(any(p_in_params))

        # Check if state parameter in redirect_uri equals state passed to session
        # Find state value in redirect_uri
        start = 'state='
        end = '&access_type'
        state = re.search('{0}(.*){1}'.format(start, end), redirect_url).group(1)
        # Get state saved to session
        session = self.client.session
        self.assertEqual(session['oauth_state'], state)

        print('\ntest_authorization_doesnt_exist: SUCCESS!')

    # Logged in user visits '/authorize/google' although already authorized
    def test_authorization_exists(self):
        # Create token
        self.token = GoogleOAuth2Token.objects.create(
            user=self.user,
            profile_id=123456,
            access_token='test_access_token',
            refresh_token='test_refresh_token',
            expires=3600
        )

        # Response
        response = self.client.get('/authorize/google', follow=True)
        self.assertRedirects(
            response,
            '/profile/{0}'.format(self.user.username),
            status_code=302,
            target_status_code=200,
            fetch_redirect_response=True
        )
        self.assertContains(
            response,
            'Google Analytics already connected!',
        )

        print('\ntest_authorization_exists: SUCCESS!')


class CallbackGoogleAnalyticsTest(TestCase):

    def setUp(self):
        # Create user
        self.user = User.objects.create_user(
            username='user',
            password='test1234'
        )
        # Login user
        self.client.login(username='user', password='test1234')
        # Add state to the session
        session = self.client.session
        session['oauth_state'] = 'test_state'
        session.save()

    @patch('integrations.views.get_token_and_profile_id')
    def test_callback_google(self, mock_get_token_and_profile_id):
        # Mock token and profile_id returned
        mock_get_token_and_profile_id.return_value = (
            # token
            {
                'access_token': 'test_access_token',
                'expires_at': 3600,
                'refresh_token': 'test_refresh_token'
            },
            # profile_id
            123456
        )

        # Response
        response = self.client.get('/callback/google', follow=True)
        self.assertRedirects(
            response,
            '/profile/{0}'.format(self.user.username),
            status_code=302,
            target_status_code=200,
            fetch_redirect_response=True
        )
        self.assertContains(
            response,
            'Google Analytics succesfully connected.',
        )

        # Args passed to mock_get_token_and_profile_id function
        (oauth_state, request), kwargs = mock_get_token_and_profile_id.call_args
        self.assertEqual(oauth_state, 'test_state')
        self.assertIn('/callback/google', request.build_absolute_uri())

        # Token created
        token = GoogleOAuth2Token.objects.get(user=self.user)
        self.assertEqual(token.access_token, 'test_access_token')
        self.assertEqual(token.expires, 3600)
        self.assertEqual(token.refresh_token, 'test_refresh_token')

        print('\ntest_callback_google: SUCCESS!')


class GoogleAnalyticsFetchPushTest(TestCase):

    def setUp(self):
        # Create user
        self.user = User.objects.create_user(
            username='user',
            password='test1234'
        )
        # Create token
        self.token = GoogleOAuth2Token.objects.create(
            user=self.user,
            profile_id=123456,
            access_token='test_access_token',
            refresh_token='test_refresh_token',
            expires=3600
        )

    # Helper function returning json encoded response
    def response_dict_to_json(self, data):
        response = requests.Response()
        response.status_code = 200

        def json_func():
            return data

        response.json = json_func
        return response

    @patch('integrations.tasks.requests.get')
    def test_validate_token(self, mock_get):
        # Validated token is invalid
        mock_get.return_value = self.response_dict_to_json(
            {'error': 'invalid_token'}
        )
        # Call the method tested
        token_valid = validate_token(self.token)
        self.assertEqual(token_valid, None)

        # Validated token is valid
        mock_get.return_value = self.response_dict_to_json(
            {'access_token': 'test_access_token'}
        )
        # Call the method tested
        token_valid = validate_token(self.token)
        self.assertEqual(token_valid, self.token.access_token)

        print('\ntest_validate_token: SUCCESS!')

    @patch('integrations.tasks.get_new_token')
    def test_refresh_token(self, mock_get_new_token):
        # Mock token returned
        new_token = {
                'access_token': 'new_access_token',
                'expires_at': 7200,
                'refresh_token': 'new_refresh_token'
            }
        mock_get_new_token.return_value = new_token

        # Call the method tested
        refresh_token(self.token)

        # Args passed to mock_get_new_token function
        token_tuple, kwargs = mock_get_new_token.call_args
        self.assertIsInstance(token_tuple[0], GoogleOAuth2Token)

        # User's token from setUp method is updated
        self.assertEqual(self.token.access_token, 'new_access_token')
        self.assertEqual(self.token.expires, 7200)
        self.assertEqual(self.token.refresh_token, 'new_refresh_token')

        print('\ntest_refresh_token: SUCCESS!')

    @patch('integrations.tasks.requests.get')
    def test_fetch_data_from_ganalytics(self, mock_get):
        # Mock data returned
        data = {
                'totalsForAllResults': {
                    'ga:users': 10,
                    'ga:sessions': 10,
                    'ga:pageviewsPerSession': 15,
                    'ga:bounces': 5,
                    'ga:bounceRate': 5,
                }
            }
        mock_get.return_value = self.response_dict_to_json(data)

        # Call the method tested
        data_returned = fetch_data_from_ganalytics(
            self.token.access_token,
            self.token.profile_id
        )

        self.assertEqual(data['totalsForAllResults'], data_returned)

        # Args passed to mock_get function
        fetch_url_tuple, kwargs = mock_get.call_args

        PROFILE = 'ids=ga:{0}'.format(str(self.token.profile_id))
        FETCH_URL = '{0}{1}{2}'.format(BASE_URL, PROFILE, QUERYSTRING)

        self.assertEqual(fetch_url_tuple[0], FETCH_URL)
        self.assertEqual(
            kwargs['headers'],
            {'Authorization': 'Bearer test_access_token'}
        )

        print('\ntest_fetch_data_from_ganalytics: SUCCESS!')

    @patch('integrations.tasks.client.insert_all')
    def test_push_ganalytics_data_to_databox(self, mock_insert_all):
        # Mock RESPONSE_ID returned
        RESPONSE_ID = 12356
        mock_insert_all.return_value = RESPONSE_ID

        data = {
            'ga:users': 10,
            'ga:sessions': 10,
            'ga:pageviewsPerSession': 15,
            'ga:bounces': 5,
            'ga:bounceRate': 5,
        }

        # Response
        response_id = push_ganalytics_data_to_databox(data)
        self.assertEqual(RESPONSE_ID, response_id)

        # Args passed to mock_insert_all function
        inserted_data_tuple, kwargs = mock_insert_all.call_args

        today = datetime.today().strftime('%Y-%m-%d')
        # Test data inserted
        inserted_data = [
            {'key': 'GA Users', 'value': data['ga:users'], 'date': today},
            {'key': 'GA Sessions', 'value': data['ga:sessions'], 'date': today},
            {'key': 'GA Page Views Per Session', 'value': data['ga:pageviewsPerSession'], 'date': today},
            {'key': 'GA Bounces', 'value': data['ga:bounces'], 'date': today},
            {'key': 'GA Bounce Rate', 'value': data['ga:bounceRate'], 'date': today},
        ]
        self.assertEqual(inserted_data_tuple[0], inserted_data)

        print('\ntest_push_ganalytics_data_to_databox: SUCCESS!')
