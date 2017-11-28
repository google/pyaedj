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

"""Configuration for Django Admin."""

__author__ = 'Pavel Simakov (psimakov@google.com)'


import sys
from django import shortcuts
from django.contrib import admin
from django.db import utils
from modules.web.cms import models

APP_NAME = 'cms'


def server_error(request):
  """Renders custom 500 error page."""
  error_type = 'An Unknown Error'
  error_details = ''
  is_intermittent = False
  _, error, _ = sys.exc_info()
  if error:
    if isinstance(error, models.UserVisibleBusinessRuleViolation):
      error_type = 'A Business Rule Violation'
      error_details = str(error)
      is_intermittent = False
    elif isinstance(error, utils.DatabaseError):
      error_type = 'A Database Error'
      is_intermittent = True
    else:
      error_type = 'An Unexpected Error'
  return shortcuts.render(request, 'admin/500.html', {
      'error_type': error_type, 'error_details': error_details,
      'is_intermittent': is_intermittent})


class CustomAdminSite(admin.AdminSite):
  """Admin site."""

  site_title = 'Django on App Engine'
  site_header = site_title
  site_url = None

  def app_index(self, request, app_label, extra_context=None):
    return super(CustomAdminSite, self).app_index(
        request, app_label, extra_context=extra_context)

  # Override has-*permission since we don't use the Django permissions system.
  def has_permission(self, request):
    return True

  def has_add_permission(self, request):
    return True

  def has_change_permission(self, request, obj=None):
    return True

  def has_delete_permission(self, request):
    return True

  def has_module_permission(self, request):
    return True


class PersonAdmin(admin.ModelAdmin):
  """Person admin."""

  APP_NAME = APP_NAME

  def log_addition(self, request, obj, message):
    pass

  def has_module_permission(self, request):
    return True

  def has_add_permission(self, request):
    return True

  def has_change_permission(self, request, obj=None):
    return True

  def has_delete_permission(self, request, obj=None):
    return True


admin.site = CustomAdminSite()


ALL_ADMINS = [
    (models.Person, PersonAdmin)
]

for amodel, aadmin in ALL_ADMINS:
  aadmin.APP_NAME = APP_NAME
  admin.site.register(amodel, aadmin)
