import re
from unittest.mock import patch

from urllib.parse import unquote
from django.contrib.auth.models import User
from django.test import TestCase

from .models import GoogleOAuth2Token


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
        self.assertEqual(len(tokens), 1)

        print('\ntest_callback_google: SUCCESS!')

    # 1. Add state to request
    # 2. Patch oauth.fetch_token function
    # 3. Patch requests.get()
