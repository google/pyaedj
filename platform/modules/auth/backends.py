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

"""Authentication backends for the Google auth module."""

__author__ = 'John Cox (johncox@google.com)'


class AlwaysCrashBackend(object):
  """Backend that throws if it's ever accessed.

  App Engine is our authentication system, and we're bypassing Django's auth
  system and model layer. We want loud crashes if our encapsulation is ever
  violated and the Django layers are accessed.
  """

  def authenticate(self, **unused_credentials):
    raise NotImplementedError(
        'User authentication is owned by App Engine; authenticate() is not '
        'supported')

  def get_user(self, unused_user_id):
    raise NotImplementedError(
        'User authentication is owned by App Engine; get_user() is not '
        'supported.')
