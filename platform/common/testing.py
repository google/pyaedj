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

"""Testing helper classes."""

__author__ = 'Pavel Simakov (psimakov@google.com)'


import base64
from contextlib import contextmanager
from datetime import datetime
from functools import wraps
from common import dao
import config
from django import test
from google.appengine.ext import deferred
from google.appengine.ext import testbed


@contextmanager
def patched(class_or_instance, new_method):
  """A decorator to patch new method into a class."""

  @classmethod
  def _patch_class_method(*args):
    return new_method(args)

  def _patch_instance_method(*args):
    return new_method(args)

  def _patch_unbound_method(*args):
    return new_method(args)

  original = getattr(class_or_instance, new_method.__name__)

  if hasattr(original, '__self__'):
    if original.__self__ is None:
      patch_method = _patch_instance_method
    else:
      patch_method = _patch_class_method
  else:
    patch_method = _patch_unbound_method

  setattr(class_or_instance, new_method.__name__, patch_method)
  try:
    yield None
  finally:
    setattr(class_or_instance, new_method.__name__, original)


@contextmanager
def frozen_time(target, value=None):
  """A decorator to patch datetime.now in target.NOW."""

  @classmethod
  def fake_now(unused_cls):
    if value:
      return value
    return datetime(2017, 1, 1, 12, 1, 1)

  old_now = target.NOW
  target.NOW = fake_now
  try:
    yield None
  finally:
    target.NOW = old_now


@contextmanager
def fixed_random(target):
  """A decorator to patch random in target.RANDOM."""

  def fake_choice(items):
    return items[0]

  class FakeRandom(object):

    def __init__(self):
      self.choice = None

  obj = FakeRandom()
  obj.choice = fake_choice

  old_random = target.RANDOM
  target.RANDOM = obj
  try:
    yield None
  finally:
    target.RANDOM = old_random


def ephimeral(f):
  """A decorator."""

  @wraps(f)
  def wrapped(*args, **kwargs):
    """Wrapper function."""
    with dao.provider(dao.EphimeralStorageProvider) as provider:
      with provider.client() as client:
        kwargs['client'] = client
        return f(*args, **kwargs)

  return wrapped


class BaseTestCase(test.TestCase):
  """Base test class for App Engine."""

  def setUp(self):
    super(BaseTestCase, self).setUp()
    dao.EphimeralStorageProvider._clear()  # pylint: disable=protected-access
    self.testbed = testbed.Testbed()
    self.testbed.activate()
    self.testbed.init_user_stub()
    self.testbed.init_memcache_stub()
    self.testbed.init_taskqueue_stub(root_path='.')
    self.taskq = self.testbed.get_stub(testbed.TASKQUEUE_SERVICE_NAME)

  def tearDown(self):
    self.execute_all_deferred_tasks()
    self.testbed.deactivate()
    super(BaseTestCase, self).tearDown()

  def assertContains(self, response, text, **kwargs):
    try:
      super(BaseTestCase, self).assertContains(response, text, **kwargs)
    except AssertionError as ae:
      config.LOG.critical('Response:\n%s', response.content)
      raise ae

  def assertNotContains(self, response, text, **kwargs):
    try:
      super(BaseTestCase, self).assertNotContains(response, text, **kwargs)
    except AssertionError as ae:
      config.LOG.critical('Response:\n%s', response.content)
      raise ae

  def execute_all_deferred_tasks(self, queue_name='default'):
    """Executes all pending deferred tasks."""
    count = 0
    for task in self.taskq.GetTasks(queue_name):
      data = base64.b64decode(task['body'])
      # TODO(psimakov): do we need to pull out the namespace?
      # namespace = dict(task['headers']).get(
      #    'X-AppEngine-Current-Namespace', '')
      deferred.run(data)
      count += 1
    self.taskq.FlushQueue(queue_name)
    return count

  def login(self, uid, email):
    self.testbed.setup_env(user_email=email, user_id=uid, user_is_admin='0',
                           overwrite=True)
