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

"""User identity management."""

__author__ = 'John Cox (johncox@google.com)'


from google.appengine.api import users


# Arg names are determined by the signature of the App Engine fn we wrap.
# pylint: disable=invalid-name
def create_login_url(dest_url=None, _auth_domain=None, federated_identity=None):
  return users.create_login_url(
      dest_url=dest_url, _auth_domain=_auth_domain,
      federated_identity=federated_identity)
# pylint: enable=invalid-name


def create_logout_url(dest_url):
  return users.create_logout_url(dest_url)


def get_current_user():
  return User.from_app_engine_user(users.get_current_user())


def is_current_user_admin():
  return users.is_current_user_admin()


class User(object):
  """DDO for user data.

  This object is *not* API-compatible with Django's User. This is deliberate. We
  are not yet supporting any of the features (ACLs, etc.) of Django's user
  system. If this changes, we can revisit. In the mean time, try to minimize
  skew between this interface and Django's user interface.
  """

  def __init__(self, user_id, email):
    """Creates a new User.

    Args:
      user_id: string. The user_id.
      email: string. The user's email address.

    Returns:
      User.
    """
    assert user_id
    assert email
    self.user_id = user_id
    self.email = email

  def has_perm(self, unused_permission_name):
    # ignore Django persmission checks; we have our own ACL system
    return True

  @classmethod
  def from_app_engine_user(cls, user):
    """Creates a User from an App Engine users.User."""
    if user is None:
      return None
    return cls(user.user_id(), user.email())
