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

"""Google Drive API Helper Functions.

The source code is here if you wish to debug:
  https://github.com/google/google-api-python-client

"""

__author__ = 'Pavel Simakov (psimakov@google.com)'


from apiclient import discovery
import config
import httplib2


SCOPE_RO = 'https://www.googleapis.com/auth/drive.readonly'


class HTTPError(Exception):
  pass


class _UrlsHelper(object):
  """Helper class to construct varoud Google Drive URL's."""

  @classmethod
  def get_worksheet_csv_url(cls, file_id, worksheet_id):
    return (
        'https://docs.google.com/spreadsheets/d/'
        '%s/export?format=csv&gid=%s' % (file_id, worksheet_id))


class DriveManager(object):
  """Manages access to Google Drive."""

  def __init__(self, service, transport):
    self.service = service
    self.transport = transport

  @classmethod
  def from_oauth2_credentials(cls, credentials):
    """Creates Manged from oauth2 credentials."""
    transport = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v3', http=transport)
    return cls(service, transport)

  def _http_request(self, url):
    """Performs HTTP request using the Python API client with auth setup."""
    # pylint: disable=protected-access
    return self.service._http.request(url)

  def download_sheet(self, file_id, worksheet_id):
    """Downloads Sheet content as CSV."""
    url = _UrlsHelper.get_worksheet_csv_url(file_id, worksheet_id)
    config.LOG.info('Fetching: %s', url)
    response, content = self._http_request(url)
    if response.status != 200:
      raise HTTPError(
          'Failed to fetch URL %s, status: $%s' % (url, response.status))
    return content

