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

"""RPC, REST, HTTP Helper Functions."""

__author__ = 'Pavel Simakov (psimakov@google.com)'


import json
import traceback
import config
from flask import request


class DomainError(Exception):
  """An error to be reported across API coundary."""

  message = 'Internal error.'
  status_code = 420

  def __init__(self, message=None, code=None, data=None):
    self.code = code
    self.data = data
    self.message = message if message else self.__class__.message
    super(DomainError, self).__init__(message)


class BadPayloadFormatException(DomainError):
  message = 'Bad payload format.'
  status_code = 400


class RequestContext(object):
  """Aa API request context."""

  def __init__(self, data):
    self.data = data
    self.response = None
    self.status_code = None

  def mixin(self, cls):
    """Mixin all clazz methods into this object instance."""
    base_cls = self.__class__
    base_cls_name = self.__class__.__name__
    self.__class__ = type(base_cls_name, (base_cls, cls), {})

  def clone_and_filter(self, data, allow_names):
    """Copies an object removing all attributes not in allow_names."""
    if not data:
      return None
    assert isinstance(data, dict)
    new_data = dict(data)
    for name in data:
      if name not in allow_names:
        del new_data[name]
    return new_data

  def set_domain_error_response(self, error):
    """Set response from the error."""
    assert not self.response
    data = {'error_class': error.__class__.__name__}
    if error.data:
      data.update(error.data)
    self.status_code = 200
    self.response = {
        'data': data,
        'message': error.message,
        'statusCode': error.status_code
    }

  def set_data_response(self, data, status_code):
    assert not self.response
    self.status_code = status_code
    self.response = {
        'data': data,
        'statusCode': status_code
    }

  def set_response(self, content, status_code):
    assert not self.response
    self.status_code = status_code
    self.response = {
        'data': content,
        'statusCode': status_code
    }


def response_500(exception, data, user_message):
  stack_info = traceback.format_exc()
  config.LOG.exception('Exception %s:\n%s\n%s\n%s',
                       user_message, str(data), exception, stack_info)
  return (user_message, 500)


def handler(func):
  """Handles REST response with all nessesary error handling and Auth."""

  def wrapper(self, *unused_args, **unused_kwargs):
    """A decorator that manages error handling."""
    context_class = None
    if hasattr(self, 'CONTEXT_CLASS'):
      context_class = self.CONTEXT_CLASS
    if not context_class:
      context_class = RequestContext
    try:
      try:
        self.ctx = context_class(
            json.loads(request.data) if request.data else {})
      except Exception as e:
        config.LOG.error('Failed to parse request body: %s\n%s\n%s', e,
                         request.data, request.headers)
        self.ctx = context_class({})
        raise BadPayloadFormatException()
      func(self)
    except DomainError as de:
      self.ctx.set_domain_error_response(de)
    except Exception as e:  # pylint: disable=broad-except
      stack_info = traceback.format_exc()
      config.LOG.error('%s\n%s', e, stack_info)
      self.ctx.set_response(*(
          response_500(e, '%s\n%s' % (request.headers, request.data),
                       'Internal error.')))
    assert self.ctx.response and self.ctx.status_code
    return (json.dumps(self.ctx.response, indent=4, sort_keys=True),
            self.ctx.response['statusCode'])

  return wrapper
