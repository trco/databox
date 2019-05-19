import re
import requests
from unittest.mock import patch

from urllib.parse import unquote
from django.contrib.auth.models import User
from django.test import TestCase

from .models import GoogleOAuth2Token
from .tasks import (fetch_data_from_google_analytics, push_data_to_databox,
                    validate_token, refresh_token)


class AuthorizeGoogleTest(TestCase):

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

    # Logged in user visits '/authorize/google' although he already authorized
    def test_authorization_exists(self):
        # Create token
        self.token = GoogleOAuth2Token.objects.create(
            user=self.user,
            profile_id=123456,
            access_token='test_access_token',
            refresh_token='test_refresh_token',
            expires=3600
        )
        response = self.client.get('/authorize/google', follow=True)
        # If fetch_redirect_response is False, the final page won’t be loaded.
        # Since the test client can’t fetch external URLs, this is particularly
        # useful if expected_url isn’t part of your Django app.

        # Checks
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


class CallbackGoogleTest(TestCase):

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
        session['oauth_state'] = 'Test state!'
        session.save()

    @patch('integrations.views.get_token_and_profile_id')
    def test_callback_google(self, mock_get_token_and_profile_id):
        mock_get_token_and_profile_id.return_value = (
            {
                'access_token': 'test_access_token',
                'expires_at': 3600,
                'refresh_token': 'test_refresh_token'
            },
            123456
        )

        response = self.client.get('/callback/google', follow=True)
        tokens = GoogleOAuth2Token.objects.all()

        # Checks
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
        self.assertEqual(tokens.count(), 1)

        print('\ntest_callback_google: SUCCESS!')

    # 1. Add state to request
    # 2. Patch oauth.fetch_token function
    # 3. Patch requests.get()


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
        # Test if token or None returned
        mock_get.return_value = self.response_dict_to_json(
            {'error': 'invalid_token'}
        )
        token_valid = validate_token(self.token)
        self.assertEqual(token_valid, None)

        mock_get.return_value = self.response_dict_to_json(
            {'access_token': 'test_access_token'}
        )
        token_valid = validate_token(self.token)
        self.assertEqual(token_valid, self.token.access_token)

        print('\ntest_validate_token: SUCCESS!')

    @patch('integrations.tasks.get_new_token')
    def test_refresh_token(self, mock_get_new_token):
        new_token = {
                'access_token': 'new_access_token',
                'expires_at': 7200,
                'refresh_token': 'new_refresh_token'
            }
        mock_get_new_token.return_value = new_token

        refresh_token(self.token)

        self.assertEqual(self.token.access_token, 'new_access_token')
        self.assertEqual(self.token.expires, 7200)
        self.assertEqual(self.token.refresh_token, 'new_refresh_token')

        print('\ntest_refresh_token: SUCCESS!')

    @patch('integrations.tasks.requests.get')
    def test_fetch_data_from_google_analytics(self, mock_get):
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
        returned_data = fetch_data_from_google_analytics(
            self.token.access_token,
            self.token.profile_id
        )

        self.assertEqual(data['totalsForAllResults'], returned_data)

        print('\ntest_fetch_data_from_google_analytics: SUCCESS!')

    @patch('integrations.tasks.client.insert_all')
    def test_push_data_to_databox(self, mock_insert_all):
        RESPONSE_ID = 12356
        mock_insert_all.return_value = RESPONSE_ID
        data = {
            'ga:users': 10,
            'ga:sessions': 10,
            'ga:pageviewsPerSession': 15,
            'ga:bounces': 5,
            'ga:bounceRate': 5,
        }

        response_id = push_data_to_databox(data)

        self.assertEqual(RESPONSE_ID, response_id)

        print('\ntest_push_data_to_databox: SUCCESS!')
