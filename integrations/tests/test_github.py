import re
import requests
from unittest.mock import patch
from datetime import datetime

from urllib.parse import unquote
from django.contrib.auth.models import User
from django.test import TestCase

import integrations

from ..models import GithubOAuth2Token, GithubRepository
from ..tasks import (fetch_data_from_github,
                     push_github_data_to_databox)


BASE_URL = 'https://www.googleapis.com/analytics/v3/data/ga?'
DATES = '&start-date=today&end-date=today'
METRICS = '&metrics=ga:users,ga:sessions,ga:pageviewsPerSession,ga:bounces,ga:bounceRate'
QUERYSTRING = '{0}{1}'.format(DATES, METRICS)


class AuthorizeGithubTest(TestCase):

    def setUp(self):
        # Create user
        self.user = User.objects.create_user(
            username='user',
            password='test1234'
        )
        # Login user
        self.client.login(username='user', password='test1234')

    def test_authorization_doesnt_exist(self):
        response = self.client.get('/authorize/github', follow=True)
        redirect_url, status_code = response.redirect_chain[-1]
        redirect_url = unquote(unquote(redirect_url))

        # Check if all parameters from OAuth2Session are in redirect_url
        params = [
            'https://github.com/login/oauth/authorize',
            '?response_type=code',
            'client_id=389a66a5bc2dbc0dac13',
        ]
        p_in_params = [p in redirect_url for p in params]
        self.assertFalse(False in p_in_params)

        # Check if state parameter in redirect_uri equals state passed to session
        # Find state value in redirect_uri
        start = 'state='
        state = re.search('{0}(.*)'.format(start), redirect_url).group(1)
        # Get state saved to session
        session = self.client.session
        self.assertEqual(session['oauth_state'], state)

        print('\nGITHUB: test_authorization_doesnt_exist: SUCCESS!')

    # Logged in user visits '/authorize/google' although already authorized
    def test_authorization_exists(self):
        # Create token
        self.token = GithubOAuth2Token.objects.create(
            user=self.user,
            username='test_user',
            access_token='test_access_token',
            token_type='test_token_type',
        )

        # Response
        response = self.client.get('/authorize/github', follow=True)
        self.assertRedirects(
            response,
            '/profile/{0}'.format(self.user.username),
            status_code=302,
            target_status_code=200,
            fetch_redirect_response=True
        )
        self.assertContains(
            response,
            'Github already connected!',
        )

        print('\nGITHUB: test_authorization_exists: SUCCESS!')


class CallbackGithubTest(TestCase):

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

    @patch('integrations.github.get_token')
    def test_callback_github(self, mock_get_token):
        # Mock token returned
        mock_get_token.return_value = ({
                'access_token': 'test_access_token',
                'token_type': 'test_token_type'
            })

        def fake_get_github_username(token):
            self.arg_token_1 = token
            return 'test_username', 'test_repos_url', {'Authorization': 'Bearer ' + 'test_access_token'}

        def fake_get_user_repositories(token, repos_url, headers, request):
            self.arg_token_2 = token
            self.arg_repos_url = repos_url
            self.arg_headers = headers
            self.arg_request = request
            return ['test_repo_1', 'test_repo_2', 'test_repo_3']

        integrations.github.get_github_username = fake_get_github_username
        integrations.github.get_user_repositories = fake_get_user_repositories

        # Response
        response = self.client.get('/callback/github', follow=True)

        self.assertRedirects(
            response,
            '/select-repository/github',
            status_code=302,
            target_status_code=200,
            fetch_redirect_response=True
        )

        self.assertEqual(
            response.wsgi_request.session['repos_list'],
            ['test_repo_1', 'test_repo_2', 'test_repo_3']
        )
        self.assertContains(response, 'test_repo_1')

        # Args passed to mock_get_token function
        (oauth_state, request), kwargs = mock_get_token.call_args
        self.assertEqual(oauth_state, 'test_state')
        self.assertIn('/callback/github', request.build_absolute_uri())

        # Args passed to fake_get_github_username and fake_get_user_repositories function
        self.assertEqual(self.arg_token_1, self.arg_token_2)
        self.assertEqual(self.arg_repos_url, 'test_repos_url')
        self.assertEqual(self.arg_headers, {'Authorization': 'Bearer ' + 'test_access_token'})
        self.assertIn('/callback/github', self.arg_request.build_absolute_uri())

        # Token created
        token = GithubOAuth2Token.objects.get(user=self.user)
        self.assertEqual(token.access_token, 'test_access_token')
        self.assertEqual(token.token_type, 'test_token_type')

        print('\nGITHUB: test_callback_github: SUCCESS!')


class GoogleAnalyticsFetchPushTest(TestCase):

    def setUp(self):
        # Create user
        self.user = User.objects.create_user(
            username='user',
            password='test1234'
        )
        # Create token
        self.token = GithubOAuth2Token.objects.create(
            user=self.user,
            username='test_username',
            access_token='test_access_token',
            token_type='test_token_type',
        )
        # Create repository
        self.repository = GithubRepository.objects.create(
            user=self.user,
            name='test_repo_1'
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
    def test_fetch_data_from_github(self, mock_get):
        # Mock data returned
        data = {
            'repo': 'test_repo_1',
            'forks_count': 5,
            'stargazers_count': 10,
            'watchers_count': 5,
            'open_issues_count': 1,
            'subscribers_count': 2
        }
        mock_get.return_value = self.response_dict_to_json(data)

        # Call the method tested
        data_returned = fetch_data_from_github(
            self.token,
            self.repository
        )
        self.assertEqual(data, data_returned)

        # Args passed to mock_get function
        fetch_url_tuple, kwargs = mock_get.call_args

        FETCH_URL = 'https://api.github.com/repos/{0}/{1}'.format(
            self.token.username,
            'test_repo_1'
        )

        self.assertEqual(fetch_url_tuple[0], FETCH_URL)
        self.assertEqual(
            kwargs['headers'],
            {'Authorization': 'Bearer test_access_token'}
        )

        print('\nGITHUB: test_fetch_data_from_github: SUCCESS!')

    @patch('integrations.tasks.client.insert_all')
    def test_push_github_data_to_databox(self, mock_insert_all):
        # Mock RESPONSE_ID returned
        RESPONSE_ID = 12356
        mock_insert_all.return_value = RESPONSE_ID

        data = {
            'repo': 'test_repo_1',
            'forks_count': 5,
            'stargazers_count': 10,
            'watchers_count': 5,
            'open_issues_count': 1,
            'subscribers_count': 2
        }

        # Response
        response_id = push_github_data_to_databox(data)
        self.assertEqual(RESPONSE_ID, response_id)

        # Args passed to mock_insert_all function
        inserted_data_tuple, kwargs = mock_insert_all.call_args

        today = datetime.today().strftime('%Y-%m-%d')
        # Test data inserted
        inserted_data = [
            {'key': data['repo'] + ' forks_count', 'value': data['forks_count'], 'date': today},
            {'key': data['repo'] + ' stargazers_count', 'value': data['stargazers_count'], 'date': today},
            {'key': data['repo'] + ' watchers_count', 'value': data['watchers_count'], 'date': today},
            {'key': data['repo'] + ' open_issues_count', 'value': data['open_issues_count'], 'date': today},
            {'key': data['repo'] + ' subscribers_count', 'value': data['subscribers_count'], 'date': today},
        ]
        self.assertEqual(inserted_data_tuple[0], inserted_data)

        print('\nGITHUB: test_push_github_data_to_databox: SUCCESS!')
