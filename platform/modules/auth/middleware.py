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

"""Middleware for Google auth module."""

__author__ = 'John Cox (johncox@google.com)'


from django.conf import settings
from modules.auth import users


class AuthenticationMiddleware(object):
  """Sets request.user to the current App Engine user."""

  def process_request(self, request):
    user = users.get_current_user()

    if not user:
      if not request.path.startswith(
          settings.GOOGLE_AUTH_NOT_REQUIRED_PATH_PREFIXES):
        raise AssertionError(
            'Google App Engine authentication must be applied to all endpoints '
            'where user authentication is required. Failed to get a the '
            'currently signed-in user; most likely cause is a missing "login: '
            'required" in your app.yaml.')
    else:
      request.user = user
