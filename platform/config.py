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

"""Various Config Data."""

__author__ = 'Pavel Simakov (psimakov@google.com)'


from contextlib import contextmanager
import logging
import os
import sys


ISO_8601_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'
BUNDLE_HOME = os.path.dirname(__file__)
CURRENT_USERNAME = os.environ.get('USER', None)
XSRF_SECRET = 'change value to your own secret'

_TEST_ENV = {}
_CONFIG_ENV_NAME = os.environ.get('CONFIG_ENV_NAME', 'TEST')
_IS_PRODUCTION = _CONFIG_ENV_NAME == 'PROD'

IS_APP_ENGINE_STANDADR_PROD = os.getenv(
    'SERVER_SOFTWARE', '').startswith('Google App Engine/')

APP_VERSION = 'Test'
if IS_APP_ENGINE_STANDADR_PROD:
  APP_VERSION = os.environ.get('CURRENT_VERSION_ID', '').split('.')[0]


# select proper config
_DEFAULT_ENV = {
    'project_id': 'py-ae-dj',
    'sprint': '1',
}


def add_env_override(name, value):
  assert name not in _TEST_ENV, name
  _TEST_ENV[name] = value


def remove_env_override(name):
  assert name in _TEST_ENV, name
  del _TEST_ENV[name]


@contextmanager
def env_override(name, value):
  add_env_override(name, value)
  try:
    yield None
  finally:
    remove_env_override(name)


class _ReflectiveObjective(object):

  def __getattr__(self, name):
    if name in _TEST_ENV:
      return _TEST_ENV[name]
    if name in _DEFAULT_ENV:
      return _DEFAULT_ENV[name]
    raise KeyError('Unknown key: %s' % name)


ENV = _ReflectiveObjective()


logging.basicConfig()
LOG = logging.getLogger(__name__)
LOG.level = logging.INFO


def fix_sys_path():
  sys.path.insert(1, '{root}/lib'.format(root=BUNDLE_HOME))
  sys.path.insert(1, os.path.join(
      os.path.expanduser('~'), 'google-cloud-sdk',
      'platform', 'google_appengine'))


fix_sys_path()
LOG.info(
    'Started: version "%s", process id "%s", env: "%s" with sys.path: "%s"',
    APP_VERSION, os.getpid(), _DEFAULT_ENV, sys.path)
