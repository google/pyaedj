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

"""Google Cloud Datastore API wrap along with Mock implementation for testing.

Here is the source:
  https://github.com/GoogleCloudPlatform/google-cloud-python/


General WARNING!!!

  Cloud Datastore API seems simple, but it is not... Do spend time running
  research projects to understand how to use it for your specific use cases.
  This documents contains critical information for our use of Cloud Datastore.


Key Conventions:

  # No classes in google.cloud.datastore are directly accessible to
  application layer. All calls are proxied and all objects are wrapped.

  # _Key == is a string representation of google.cloud.datastore.Key(),
  containing only key.kind and key.id, for example: "UserProfile::12345".
  Namespace and project is removed, making backups directly portable between
  envornments. Application code operates with string rep of _Key.

  # All kinds use natural auto-assigned primary keys, unless (very rarely)
  an explicit key used, when it is known and we need a guarantee that row is
  unique.

  # *_ref == holds a str _Key pointing to a specific typed object instance,
  for example: "UserProfile::12345".


Key Notes:

    # reload in transaction all entities you plan to mutate in transaction
    # query() is not allowed in transaction; do query ahead of time
    # equality filters do NOT require composite indexes
    # put() in transaction does not set key into the entity until commit()
    # if you did put(obj1.name) and put(obj2.desc) first and then did a query
    # for "name is Null" - query will NOT return obj2 :(
    # if you put non-timezone datetime in, timezone-aware one comes out :(


Good Luck!
"""

__author__ = 'Pavel Simakov (psimakov@google.com)'


from contextlib import contextmanager
import copy
import datetime
import json
import config
import flask
from google.appengine.ext import deferred


def chunk_list(l, n):
  """Yield successive n-sized chunks from l."""
  for i in range(0, len(l), n):
    yield l[i:i + n]


def do_later(f, *args):
  deferred.defer(f, *args)


def _json_serializer(obj):
  """JSON serializer for objects not serializable by default json code."""
  if isinstance(obj, datetime.datetime):
    return obj.isoformat()
  raise TypeError('Type %s not serializable' % type(obj))


def to_utc_datetime(value):
  if value.tzinfo is not None:
    return value.replace(tzinfo=None) - value.utcoffset()
  return value


def entity_to_json(entity):
  return unicode(json.dumps(entity, sort_keys=True, default=_json_serializer,
                            ensure_ascii=False))


def entity_from_json(json_text):
  return json.loads(json_text)


class _Key(object):
  """Flat key."""

  def __init__(self, kind, uid):
    self.kind = str(kind)
    self.uid = str(uid)

  @classmethod
  def from_string(cls, key):
    try:
      parts = key.split('::', 1)
      assert len(parts) == 2, key
      return _Key(parts[0], parts[1])
    except:
      config.LOG.error('Bad key: %s', key)
      raise

  @classmethod
  def to_string(cls, kind, uid):
    return '{kind}::{uid}'.format(kind=kind, uid=uid)

  def __str__(self):
    return self.to_string(self.kind, self.uid)


class DatastoreProvider(object):
  """Storage provider backed by Datastore."""

  MAX_DATA_LEN = 25
  _datastore_module = None

  def __init__(self):
    if not self._datastore_module:
      from google.cloud import datastore  # pylint: disable=g-import-not-at-top
      self._datastore_module = datastore
    self.client = self._datastore_module.Client(
        namespace=config.ENV.namespace, project=config.ENV.project_id)

  @classmethod
  @contextmanager
  def client(cls):
    if flask.has_request_context():
      if flask.g.get('provider', None):
        current = flask.g.provider
      else:
        current = DatastoreProvider()
        flask.g.provider = current
    else:
      current = DatastoreProvider()
    yield current

  @contextmanager
  def transaction(self):
    with self.client.transaction():
      yield None

  def key(self, kind, uid):
    return _Key.to_string(kind, uid)

  def get(self, key):
    key = _Key.from_string(key)
    return self.client.get(self.client.key(key.kind, key.uid))

  def query(self, kind, order=None, filters=None, limit=None):
    """Query datstore."""
    if order is None:
      order = []
    query = self.client.query(kind=kind, order=order)
    if filters:
      for name, op, value in filters:
        query.add_filter(name, op, value)
    items = []
    for entity in query.fetch(limit=limit):
      items.append((_Key.to_string(kind, entity.key.id_or_name), entity))
    return items

  def query_iterator(self, kind, order=None, filters=None):
    """Query datstore."""
    if order is None:
      order = []
    query = self.client.query(kind=kind, order=order)
    if filters:
      for name, op, value in filters:
        query.add_filter(name, op, value)
    for entity in query.fetch():
      yield (_Key.to_string(kind, entity.key.id_or_name), entity)

  def put(self, kind, data, indexable_keys, key=None):
    """Insert a new object into storage."""
    if not key:
      assert kind
      key = self.client.key(kind)
    else:
      key = _Key.from_string(key)
      assert key.kind == kind
      key = self.client.key(key.kind, key.uid)

    assert set(indexable_keys).issubset(data.keys()), (indexable_keys, data)
    non_indexable_keys = set(data.keys()) - set(indexable_keys)
    assert self._datastore_module
    item = self._datastore_module.Entity(
        key=key,
        exclude_from_indexes=list(non_indexable_keys))
    state = {}
    for key, value in data.iteritems():
      if isinstance(value, str):
        try:
          value = unicode(value.decode('utf-8'))
        except Exception as e:  # pylint: disable=broad-except
          config.LOG.error('Failed to decode value: "%s"\n%s', value, e)
      state[key] = value
    item.update(state)
    self.client.put(item)
    return _Key.to_string(kind, item.key.id_or_name)

  def delete_multi(self, keys):
    keys = []
    for key in keys:
      key = _Key.from_string(key)
      keys.append(self.client.key(key.kind, key.uid))
    for chunk in chunk_list(keys, 100):
      self.client.delete_multi(chunk)

  def delete(self, key):
    self.delete_multi([key])


class EphimeralStorageProvider(object):
  """Storage provider that loggs data."""

  MAX_DATA_LEN = 25
  TREE = {}
  DATA = []
  KEY = 0

  @classmethod
  @contextmanager
  def client(cls):
    yield EphimeralStorageProvider()

  @contextmanager
  def transaction(self):
    yield None

  @classmethod
  def _clear(cls):
    cls.KEY = 0
    cls.TREE = {}

  @classmethod
  def _next_key(cls):
    cls.KEY += 1
    return cls.KEY

  @classmethod
  def _copy(cls, data):
    """Make a copy so we own the data."""
    return copy.deepcopy(data)

  def key(self, kind, uid):
    return _Key.to_string(kind, uid)

  def get(self, key):
    key = _Key.from_string(key)
    return self._copy(self.TREE.get(key.kind, {}).get(key.uid))

  def query(  # pylint: disable=unused-argument
      self, kind, order=None, filters=None, limit=None):
    items = []
    for key, entity in self.TREE.get(kind, {}).iteritems():
      items.append((_Key.to_string(kind, key), entity))
    return items

  def put(self, kind, data, unused_indexable_keys, key=None):
    """Upserts the object into storage."""
    if not key:
      uid = str(self._next_key())
      key = _Key.to_string(kind, uid)
    else:
      uid = _Key.from_string(key).uid
    if kind not in self.TREE:
      self.TREE[kind] = {}
    for item_key, item_value in data.iteritems():
      if isinstance(item_value, str):
        data[item_key] = unicode(item_value.decode('utf-8'))
    self.TREE[kind][uid] = self._copy(data)
    return key


# choose default provider based on environment
if config.IS_APP_ENGINE_STANDADR_PROD:
  _PROVIDER = DatastoreProvider
else:
  _PROVIDER = EphimeralStorageProvider
config.LOG.info('Setting current DAO provider to: %s', _PROVIDER)


@contextmanager
def provider(clazz):
  global _PROVIDER
  old = _PROVIDER
  _PROVIDER = clazz
  try:
    yield _PROVIDER
  finally:
    _PROVIDER = old


def get_provider():
  return _PROVIDER
