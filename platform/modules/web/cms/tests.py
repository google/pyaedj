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

"""Tests."""

__author__ = 'Pavel Simakov (psimakov@google.com)'


from common import testing
import config


class CMSTestCases(testing.BaseTestCase):
  """Tests."""

  def test_web_server_root(self):
    response = self.client.get('/')
    self.assertContains(
        response,
        '<h1 id="site-name"><a href="/">Django on App Engine</a></h1>')
    self.assertContains(response, '<h1>Site administration</h1>')
    self.assertContains(response, '<h3>My actions</h3>')

  def test_cms_root(self):
    response = self.client.get('/cms/')
    self.assertContains(
        response,
        '<h1 id="site-name"><a href="/">Django on App Engine</a></h1>')
    self.assertContains(response, '<h1>Cms administration</h1>')


class RESTTestCases(testing.BaseTestCase):
  """Tests."""

  def test_untrusted_project_request_fails(self):
    response = self.client.get(
        '/api/v1/ping',
        **{'HTTP_X_APPENGINE_INBOUND_APPID': 'some-other-app'})
    self.assertEquals(403, response.status_code)

  def test_trusted_project_request_ok(self):
    for project_id in [None, config.ENV.project_id]:
      response = self.client.get(
          '/api/v1/ping',
          **{'HTTP_X_APPENGINE_INBOUND_APPID': project_id})
      self.assertEquals(200, response.status_code)
