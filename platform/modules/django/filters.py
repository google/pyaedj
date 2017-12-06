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

"""Common classes that extend Django Admin filters."""

__author__ = 'Pavel Simakov (psimakov@google.com)'


import operator

from django.contrib import admin
from django.db import models


class BaseSimpleListFilter(admin.SimpleListFilter):
  """Base class for filtered list views."""
  pass


class BaseEnumFilter(admin.SimpleListFilter):
  """Base class for enum filters."""
  enum_names = None

  def lookups(self, request, model_admin):
    result = []
    for value, name in self.enum_names.iteritems():
      result.append((value, name))
    return sorted(tuple(result), key=operator.itemgetter(1))

  def queryset(self, request, queryset):
    if self.value():
      return queryset.filter(**{self.parameter_name: self.value()})


class BaseRelationFilter(admin.SimpleListFilter):
  """Base class for filtering by a related model."""
  model = None

  def lookups(self, request, model_admin):
    return [(item.id, item.name) for item in self.model.objects.all()]

  def queryset(self, request, queryset):
    if self.value():
      return queryset.filter(**{self.parameter_name: self.value()})


class BaseMultiSelectFilter(admin.SimpleListFilter):
  """Appears like a regular filter, but clicking choices toggles them."""

  def choices(self, cl):
    yield {
        'selected': self.value() is None,
        'query_string': cl.get_query_string({}, [self.parameter_name]),
        'display': 'All',
    }

    value = self.value()
    selected_list = set(value.split(',')) if value else set()
    for lookup, title in self.lookup_choices:
      text_lookup = str(lookup)
      selected = text_lookup in selected_list
      option = set((text_lookup,))

      # Clicking on a choice either adds it to the filter if it's not already
      # present or removes it from the filter if it's currently in the list of
      # selected options.
      if selected:
        param_value = selected_list - option
      else:
        param_value = selected_list | option

      yield {
          'selected': selected,
          'query_string': cl.get_query_string({
              self.parameter_name: ','.join(param_value) or None,
          }, []),
          'display': title,
      }

  def queryset(self, request, queryset):
    if self.value():
      return queryset.filter(
          **{self.parameter_name + '__in': self.value().split(',')})


class CustomBooleanFlagFilter(admin.SimpleListFilter):
  """Custom filter based on a value of boolean field."""

  def lookups(self, request, model_admin):
    return ((0, 'No'), (1, 'Yes'))

  def queryset(self, request, queryset):
    if self.value() is None:
      return queryset
    kwargs = {self.parameter_name: False}
    q = models.Q(**kwargs)
    if self.value() == '1':
      q = ~q
    return queryset.filter(q)
