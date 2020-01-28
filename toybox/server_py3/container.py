"""Here we consolidate all dependencies on the runtime and globals."""


__author__ = 'Pavel Simakov (psimakov@google.com)'


import logging


_DATASTORE_NS = 'A120_PWA'


class Registry(object):
  """Here we will keep all global objects."""

  def __init__(self):
    self.datastore_client = None

    # TODO(psimakov): we could pick a different NS when running locally
    self.datastore_ns = _DATASTORE_NS

  def patch(self, name, value):
    old_value = getattr(self, name, value)
    setattr(self, name, value)
    return old_value

  @classmethod
  def current(cls):
    return _REGISTRY


_REGISTRY = Registry()


# Enable App Engine Stackdriver Debug if available. Without this one
# is unable to step through the code in Google Cloud debugger.
try:
  import googleclouddebugger  # pylint: disable=g-import-not-at-top
  googleclouddebugger.enable()
except ImportError as e:
  logging.error('Error in enabling googleclouddebugger: %s', e)


# import Datastore package; note how this is not from google.*
# from google.auth import app_engine as gae
from google.cloud import datastore


# Create client and share it across requests.
# If you don't specify credentials when constructing the client, the
# client library will look for credentials in the environment.
# For unit testing. When testing with Forge or on TAP, datastore cannot acquire
# credentials for Datastore. We make it an empty object for the tests to mock.
try:
  _REGISTRY.datastore_client = datastore.Client(
      namespace=_REGISTRY.datastore_ns)
except Exception as e:  # pylint: disable=broad-except
  logging.error('Error in datastore.Client(): %s', e)
  _REGISTRY.datastore_client = object  # pylint: disable=invalid-name
