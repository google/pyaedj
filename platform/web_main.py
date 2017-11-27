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

"""App Engine Web Module entry point."""

__author__ = 'Pavel Simakov (psimakov@google.com)'


# Imported for side-effects. pylint: disable=unused-import
import appengine_config
import config
from django.core import wsgi


application = wsgi.get_wsgi_application()
