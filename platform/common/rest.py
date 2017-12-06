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

"""REST."""

__author__ = 'Pavel Simakov (psimakov@google.com)'


import datetime
from common import dao
import config
from django import http
from django import template
from django.views import generic
from django.views.decorators import csrf


ALLOWED_REST_APP_IDS = set([config.ENV.project_id])

# XSSI protection JSON prefix.
_JSON_XSSI_PREFIX = ")]}'\n"


def _add_xssi_prefix(s):
  """Adds the XSSI prefix to the given string."""
  return '%s%s' % (_JSON_XSSI_PREFIX, s)


def _strip_xssi_prefix(s):
  """Strips the XSSI prefix (if any) from the given string."""
  return s.lstrip(_JSON_XSSI_PREFIX)


class BaseRestHandler(generic.View):
  """Base REST handler class."""

  @classmethod
  def render_response(cls, status_code, status_message, payload):
    """Generic method for returning a JSON response."""
    data = dao.entity_to_json({
        'payload': payload if payload is not None else {},
        'status_code': status_code,
        'status_message': status_message,
    })

    content = template.Template(
        '{{ xssi_prefix|safe }}{{ json|safe }}'
    ).render(template.Context({
        'json': data,
        'xssi_prefix': _JSON_XSSI_PREFIX,
    }))

    response = http.HttpResponse()
    response.status_code = status_code
    response['Content-Type'] = 'text/plain; charset=utf-8'
    response.write(content)

    return response


class TrustedCallerRestHandler(BaseRestHandler):
  """Handler that allows requests only from specific App Engine projects."""

  @csrf.csrf_exempt
  def dispatch(self, request, *args, **kwargs):
    inbound_appid = request.META.get('HTTP_X_APPENGINE_INBOUND_APPID', None)
    if inbound_appid and inbound_appid not in ALLOWED_REST_APP_IDS:
      code = 403
      payload = {'error_code': code}
      error_message = 'Access denied.'
      return self.render_response(code, error_message, payload)
    return super(TrustedCallerRestHandler, self).dispatch(
        request, *args, **kwargs)


class PingHandler(TrustedCallerRestHandler):
  """Simple REST ping."""

  def get(self, request):
    return self.render_response(200, 'Success', {
        'server_time': datetime.datetime.now()
    })
