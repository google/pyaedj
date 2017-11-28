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


class EnvTestCases(testing.BaseTestCase):
  """Tests ENV."""

  def test_default(self):
    self.assertTrue(config.ENV.project_id)

  def test_no_existent(self):
    with self.assertRaisesRegexp(KeyError, 'Unknown key: some_unset_property'):
      self.assertTrue(config.ENV.some_unset_property)

  def test_override(self):
    config.add_env_override('some_unset_property', 'is now set')
    self.assertEqual('is now set', config.ENV.some_unset_property)
    config.remove_env_override('some_unset_property')


class DAOTestCases(testing.BaseTestCase):
  """Tests."""

  @testing.ephimeral
  def test_key(self, client=None):
    key = client.key('Foo', 12345)
    self.assertEqual('Foo::12345', key)

  @testing.ephimeral
  def test_composite_key(self, client=None):
    key = client.key('Foo', 'Bar::6789')
    self.assertEqual('Foo::Bar::6789', key)

  @testing.ephimeral
  def test_get_non_existent(self, client=None):
    key = client.key('MyKind', 1)
    item = client.get(str(key))
    self.assertEqual(None, item)

  @testing.ephimeral
  def test_insert_new(self, client=None):
    item = client.put('MyKind', {'foo': 'bar'}, [])
    self.assertEqual('MyKind::1', item)

  @testing.ephimeral
  def test_get_existing(self, client=None):
    self.test_insert_new(client=client)
    key = client.key('MyKind', 1)
    item = client.get(str(key))
    self.assertEqual({'foo': 'bar'}, item)

  @testing.ephimeral
  def test_empty_query_existing(self, client=None):
    self.assertEqual([], client.query(kind='MyKind'))

  @testing.ephimeral
  def test_query_existing(self, client=None):
    self.test_insert_new(client=client)
    self.assertEqual([('MyKind::1', {'foo': 'bar'})],
                     client.query(kind='MyKind'))
