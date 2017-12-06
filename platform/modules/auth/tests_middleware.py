#
# Copyright 2017 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Tests for Google Authentication middleware."""

__author__ = 'John Cox (johncox@google.com)'


import copy
import os
from django import http
from django import test
from django.conf import urls
from django.views.generic import base
from google.appengine.ext import testbed


class TestView(base.View):

  def get(self, request):
    return http.HttpResponse('Hello, world!')


class AssertUserAttachedToRequestView(base.View):

  def get(self, request):
    assert hasattr(request, 'user')
    assert request.user is not None
    assert request.user.user_id == os.environ['USER_ID']
    assert request.user.email == os.environ['USER_EMAIL']
    return http.HttpResponse('OK')


urlpatterns = [
    urls.url(r'auth/test', TestView.as_view()),
    urls.url(r'anon/test', TestView.as_view()),
    urls.url(r'assert_user_attached_to_request',
             AssertUserAttachedToRequestView.as_view())
]


@test.override_settings(
    ROOT_URLCONF='modules.auth.tests_middleware',
    MIDDLEWARE_CLASSES=[('modules.auth.middleware.AuthenticationMiddleware')]
)
class GoogleAuthenticationMiddlewareTests(test.TestCase):
  """Testscases for Google Authentication middleware."""

  def setUp(self):
    super(GoogleAuthenticationMiddlewareTests, self).setUp()

    self.old_environ = copy.deepcopy(os.environ)
    os.environ['AUTH_DOMAIN'] = 'google.com'
    os.environ['HTTP_SCHEME'] = 'http'

    self.testbed = testbed.Testbed()
    self.testbed.activate()
    self.testbed.init_datastore_v3_stub()
    self.testbed.init_memcache_stub()
    self.testbed.init_mail_stub()
    self.testbed.init_user_stub()

  def tearDown(self):
    self.testbed.deactivate()
    os.environ = self.old_environ
    super(GoogleAuthenticationMiddlewareTests, self).tearDown()

  def login(self, email):
    os.environ['USER_ID'] = '//user-id/%s' % email
    os.environ['USER_EMAIL'] = email
    self.testbed.setup_env(
        user_email=os.environ['USER_EMAIL'], user_id=os.environ['USER_ID'])

  def test_authenticated_request_succeeds(self):
    self.login('test@example.com')
    response = self.client.get('/auth/test')
    self.assertEqual(response.content, 'Hello, world!')
    self.assertEqual(response.status_code, 200)

  def test_unauthenticated_request_fails(self):
    with self.assertRaisesRegexp(AssertionError, 'missing "login: required"'):
      self.client.get('/auth/test')

  @test.override_settings(
      GOOGLE_AUTH_NOT_REQUIRED_PATH_PREFIXES=('/anon/test',))
  def test_unauthenticated_request_whitelisted_url_succeeds(self):
    response = self.client.get('/anon/test')
    self.assertEqual(response.content, 'Hello, world!')
    self.assertEqual(response.status_code, 200)

  @test.override_settings(
      GOOGLE_AUTH_NOT_REQUIRED_PATH_PREFIXES=('/anon/test',))
  def test_unauthenticated_request_unwhitelisted_url_fails(self):
    with self.assertRaisesRegexp(AssertionError, 'missing "login: required"'):
      self.client.get('/auth/test')

  @test.override_settings(GOOGLE_AUTH_NOT_REQUIRED_PATH_PREFIXES=
                          ('/anon/test', '/auth/test'))
  def test_unauthenticated_request_multiple_whitelisted_urls_succeeds(self):
    response = self.client.get('/anon/test')
    self.assertEqual(response.content, 'Hello, world!')
    self.assertEqual(response.status_code, 200)

    response = self.client.get('/auth/test')
    self.assertEqual(response.content, 'Hello, world!')
    self.assertEqual(response.status_code, 200)

  @test.override_settings(GOOGLE_AUTH_NOT_REQUIRED_PATH_PREFIXES=
                          ('/assert_user_attached_to_request'))
  def test_authenticated_request_whitelisted_url_attaches_user_to_request(self):
    self.login('test@example.com')
    self.client.get('/assert_user_attached_to_request')

  def test_authenticated_request_regular_url_attaches_user_to_request(self):
    self.login('test@example.com')
    self.client.get('/assert_user_attached_to_request')

  @test.override_settings(GOOGLE_AUTH_NOT_REQUIRED_PATH_PREFIXES=
                          ('/assert_user_attached_to_request'))
  def test_anon_request_whitelisted_url_doesnt_attach_user_to_request(self):
    with self.assertRaises(AssertionError):
      self.client.get('/assert_user_attached_to_request')
