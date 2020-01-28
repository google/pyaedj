"""Tests."""


__author__ = 'Pavel Simakov (psimakov@google.com)'


import json
import unittest
import dao
import dao_test
import main


def mock_get_admin_user_for_request(unused_request):
  return {
      'email': list(main.ADMIN_EMAILS)[0],
      'uid': 'abc123',
      'uid_scope': '1',
      'displayName': 'Some User',
      'photoURL': 'https://example.com/photo.jpg',
  }


def mock_get_whiteisted_email_user_for_request(unused_request):
  return {
      'email': list(main.WHITELISTED_EMAILS)[0],
      'uid': 'abc123',
      'uid_scope': '1',
  }


def mock_get_whiteisted_domain_user_for_request(unused_request):
  return {
      'email': 'some_legid_user@%s' % list(main.WHITELISTED_DOMAINS)[0],
      'uid': 'abc123',
      'uid_scope': '1',
  }


def mock_get_rogue_user_for_request(unused_request):
  return {
      'email': 'some_user@example.com',
      'uid': 'abc123',
      'uid_scope': '1',
  }


def mock_get_no_user_for_request(unused_request):
  return None


def status_json(response):
  return json.dumps(main.parse_api_response(response.text), sort_keys=True)


class AuthAndRolesTestSuite(dao_test.BaseTestSuite):
  """Auth & Auth test cases."""

  def test_api_ping_get_requires_no_credentials(self):
    response = self.app.get('/api/rest/v1/ping')
    self.assertEqual(200, response.status_int)
    self.assertEqual(
        set(['lang', 'time', 'software', 'version']),
        set(main.parse_api_response(response.text)['server'].keys()))

  def test_api_whoami_get_not_authorized(self):
    response = self.app.get('/api/rest/v1/whoami', expect_errors=True)
    self.assertEqual(401, response.status_int)

  def test_whoami_requires_id_token(self):
    response = self.app.get('/api/rest/v1/whoami', expect_errors=True)
    self.assertEqual(401, response.status_int)

  def _test_mock_user(self, mock, expected_roles, status=200):
    original = main.get_user_for_request
    try:
      main.get_user_for_request = mock
      response = self.app.get('/api/rest/v1/whoami', expect_errors=True)
      self.assertEqual(status, response.status_int)

      if status == 200:
        self.assertEqual(
            expected_roles,
            main.parse_api_response(response.text)['user']['roles'])
    finally:
      main.get_user_for_request = original

  def test_admin_user_roles(self):
    if main.ADMIN_EMAILS:
      self._test_mock_user(mock_get_admin_user_for_request,
                           ['user', 'moderator', 'admin'])

  def test_whitelisted_email_user_roles(self):
    if main.WHITELISTED_EMAILS:
      self._test_mock_user(mock_get_whiteisted_email_user_for_request,
                           ['user'])

  def test_whitelisted_domain_user_roles(self):
    if main.WHITELISTED_DOMAINS:
      self._test_mock_user(mock_get_whiteisted_domain_user_for_request,
                           ['user'])

  def test_no_user_roles(self):
    self._test_mock_user(mock_get_no_user_for_request, None, status=401)


class MembersTestSuite(dao_test.BaseTestSuite):
  """Test cases for Members."""

  def _with_user(self, then):
    self.test_registration(then=then)

  def test_registration(self, etag=1, then=None):
    original = main.get_user_for_request
    try:
      main.get_user_for_request = mock_get_admin_user_for_request
      params = {
          'settings_etag': etag,
      }
      response = self.app.put('/api/rest/v1/registration', params=params)
      self.assertEqual(200, response.status_int)

      if then:
        then('abc123')
    finally:
      main.get_user_for_request = original

  def test_registration_is_idempotent(self):
    self.test_registration()
    self.test_registration(etag=2)

  def test_registration_fails_if_old_version(self):
    original = main.get_user_for_request
    try:
      main.get_user_for_request = mock_get_admin_user_for_request
      params = {
          'settings_etag': 0,
      }
      response = self.app.put(
          '/api/rest/v1/registration', params=params, expect_errors=True)

      self.assertEqual(400, response.status_int)
      self.assertEqual(
          '{'
          '"code": "ETagError", '
          '"message": "Object was modified by someone from version V0 to V1.", '
          '"origin": "pyaedj.common.pwa.server"'
          '}',
          status_json(response))
    finally:
      main.get_user_for_request = original

  def test_update_fails_if_required_profile_attrs_are_missing(self):
    original = main.get_user_for_request
    try:
      main.get_user_for_request = mock_get_admin_user_for_request
      params = {
          'settings_etag': 0,
          'profile': '{}',
      }
      response = self.app.post('/api/rest/v1/profile', params=params,
                               expect_errors=True)
      self.assertEqual(400, response.status_int)
      self.assertEqual(
          '{'
          '"code": "InvalidFieldValueError", '
          '"message": "Title is required.", '
          '"name": "title", '
          '"origin": "pyaedj.common.pwa.server"'
          '}',
          status_json(response))
    finally:
      main.get_user_for_request = original

  def test_update(self):
    expected = {
        'title': 'My title',
        'location': 'SFO, MTV',
        'about': 'I am a engineer who loves most dogs.',
    }

    original = main.get_user_for_request
    try:
      main.get_user_for_request = mock_get_admin_user_for_request
      params = {
          'settings_etag': 1,
          'profile': json.dumps(expected),
      }
      response = self.app.post('/api/rest/v1/profile', params=params)
      self.assertEqual(200, response.status_int)
      self.assertEqual(
          expected,
          main.parse_api_response(
              response.text)['user']['settings']['profile'])
    finally:
      main.get_user_for_request = original

    return expected

  def test_list_members(self):
    expected = self.test_update()
    original = main.get_user_for_request
    try:
      main.get_user_for_request = mock_get_admin_user_for_request

      response = self.app.get('/api/rest/v1/members')
      self.assertEqual(200, response.status_int)

      members = main.parse_api_response(response.text)['result']
      self.assertEqual(1, len(members))
      self.assertEqual(expected, members[0]['profile'])
    finally:
      main.get_user_for_request = original


class PostsAndVotesTestSuite(MembersTestSuite):
  """Test cases for Posts and Votes."""

  def insert_post(self):
    response = self.app.put('/api/rest/v1/posts', {
        'post': '{}'
    })
    self.assertEqual(200, response.status_int)

  def list_posts(self):
    response = self.app.get('/api/rest/v1/posts')
    self.assertEqual(200, response.status_int)
    return main.parse_api_response(response.text)['result']

  def test__api_posts_put(self):

    def then(unused_member_uid):
      self.assertEqual(0, len(self.list_posts()))
      self.insert_post()

    self._with_user(then)

  def test__api_posts_get(self):

    def then(unused_member_uid):
      self.insert_post()
      self.assertEqual(1, len(self.list_posts()))

    self._with_user(then)

  def test__api_posts_post(self):

    def then(unused_member_uid):
      self.insert_post()

      response = self.app.post('/api/rest/v1/posts', {
          'post': json.dumps({
              'uid': dao.Posts().query_posts()[0].key.id
          }),
      })
      self.assertEqual(200, response.status_int)

      self.assertEqual(0, len(self.list_posts()))

    self._with_user(then)

  def test__api_votes_put__bad_value(self):

    def then(unused_member_uid):
      self.insert_post()

      with self.assertRaises(
          dao.BusinessRuleError,
          msg='Allowed vote values are +1 and -1, was "2".'
      ):
        self.app.put('/api/rest/v1/votes', {
            'vote': json.dumps({
                'uid': dao.Posts().query_posts()[0].key.id,
                'value': 2,
            }),
        })

    self._with_user(then)

  def test__api_votes_put(self):

    def then(unused_member_uid):
      self.insert_post()

      response = self.app.put('/api/rest/v1/votes', {
          'vote': json.dumps({
              'uid': dao.Posts().query_posts()[0].key.id,
              'value': 1,
          }),
      })
      self.assertEqual(200, response.status_int)

    self._with_user(then)


if __name__ == '__main__':
  unittest.main()
