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

"""Common classes that extend Django Admin interface."""

__author__ = 'Pavel Simakov (psimakov@google.com)'

from compiler.ast import flatten

from django import forms
from django import template
from django.conf import settings
from django.conf import urls
from django.contrib import admin
from django.contrib import messages
from django.contrib.admin.utils import quote as quote_pk
from django.core import exceptions
from django.core import serializers
from django.core import urlresolvers
from django.db.models.fields import Field
from django.db.models.lookups import IContains
from django.db.models.lookups import IExact
from django.forms.models import ModelForm
from django.http import HttpResponseRedirect


def from_request_cache(request, key, getter):
  """Caches the getter on the request object or uses the cached value."""
  if not request:
    return getter()

  # pylint: disable=protected-access
  if not hasattr(request, '_local_cache'):
    request._local_cache = {}
  cache = request._local_cache
  # pylint: enable=protected-access

  if key not in cache:
    cache[key] = getter()

  return cache[key]


def get_current_user_email(request):
  return request.user.email


def get_dict_for_model_instance(instance):
  """Gets serialized OrderedDict snapshot of a model instance."""
  return serializers.serialize('python', [instance,])[0]


def _get_object_view_url(app_name, obj):
  aclass = '%s' % obj.__class__.__name__.lower()
  return urlresolvers.reverse(
      'admin:%s_%s_change' % (app_name, aclass), args=[quote_pk(obj.id)])


def set_butterbar(request, message):
  """Sets a butterbar message to be shown on the next page."""
  messages.add_message(request, messages.INFO, message)


class RedirectAction(object):
  """Provides a redirect action."""

  def __init__(self, target_url):
    self._target_url = target_url

  @property
  def target_url(self):
    return self._target_url

  def __str__(self):
    """Needed to render action class name into HTML."""
    return self.__class__.__name__


class BaseCustomModelAdmin(admin.ModelAdmin):
  """Base class for custom ModelAdmin."""

  # A name of Django setting to control URL format for child view routing.
  # Value of True enables view routing using query string, for example:
  #     /cms/{{ model }}-{{ pk }}/change/?cms-action={{ action }}
  # Value of False enables view routing using context path, for example:
  #     /cms/{{ model }}-{{ pk }}/{{ action }}/
  SETTING_NAME_VIEW_ROUTING = 'ADMIN_EXTENSIONS_QUERY_STRING_VIEW_ROUTING'

  _ACTION_LIST_NAME = 'changelist'
  _ACTION_CHANGE_NAME = 'change'
  _ACTION_REDIRECT_NAME = '_redirect_to'

  QUERY_STRING_VIEW_ROUTING = True

  APP_NAME = None
  ACTION_ADD_NAME = 'add'

  LIST_VIEW = None
  FORM_VIEWS = {}

  def __init__(self, *args, **kwargs):
    self.active_record_obj_before_update = None
    self.active_record_dict_before_update = None
    super(BaseCustomModelAdmin, self).__init__(*args, **kwargs)

  @classmethod
  def _get_action_param_name(cls):
    return cls.APP_NAME + '-action'

  @classmethod
  def _use_query_string_view_routing(cls):
    if hasattr(settings, cls.SETTING_NAME_VIEW_ROUTING):
      return getattr(settings, cls.SETTING_NAME_VIEW_ROUTING)
    return True

  def get_list_view_def(self):
    """Override to provide dynamic list view."""
    return self.LIST_VIEW

  def get_form_view_defs(self):
    """Override to provide dynamic list of form views."""
    return self.FORM_VIEWS

  def _make_url(self, action, method):
    """Makes a URL for action view."""
    if action == self._ACTION_LIST_NAME:
      path = r'^$'
    elif action == self.ACTION_ADD_NAME:
      path = r'^add/$'
    else:
      path = r'^(.+)/{}/$'.format(action)
    return urls.url(
        path,
        method,
        name='_'.join((self.APP_NAME, self.model.__name__.lower(), action)))

  def get_urls(self):
    """Makes a URL map containing all child views."""
    if self._use_query_string_view_routing():
      return super(BaseCustomModelAdmin, self).get_urls()
    else:
      items = []
      for action, _ in self.get_form_view_defs().iteritems():
        if isinstance(action, RedirectAction):
          continue
        if action is None:
          action = self._ACTION_CHANGE_NAME
        items.append(self._make_url(action, self.changeform_view))
      list_view = self.get_list_view_def()
      if list_view:
        items.append(self._make_url(self._ACTION_LIST_NAME,
                                    self.changelist_view))
      return items

  def personalize_context_vars(self, context, request):
    """Override to provide dynamic list of view context variables."""
    return {}

  def format_action_buttons(self, exclude=None, include=None):
    """Formats list of actions to be displayed on the page."""
    result = []
    for key in self.get_accessible_action_keys():
      if exclude and key in exclude:
        continue
      if include and key not in include:
        continue
      view = self.FORM_VIEWS[key]
      result.append({
          'href': self.get_link_to_action(key),
          'action': key,
          'title': view.ACTION_HELP_TEXT,
          'content': view.ACTION_TITLE,
      })
    if result:
      return template.Template('''
          <span class="object-tools">
            {% for result in results %}
              <a href="{{ result.href }}"
                 class="pyaedj-action pyaedj-action-{{ result.action }}"
                 title="{{ result.title }}">{{ result.content }}</a>
            {% endfor %}
          </span>
      ''').render(template.Context({
          'results': result
      }))
    return []

  def _reset_all_fields(self):
    # inherited list view fields
    self.actions = None
    self.list_display = ()
    self.list_display_links = ()
    self.list_filter = ()
    self.search_fields = ()
    self.ordering = ()
    self.list_editable = ()
    self.list_display_links = ()

    # inherited form fields
    self.fieldsets = []
    self.fields = ()
    self.field_labels = ()
    self.readonly_fields = ()
    self.filter_horizontal = ()

    # inlines
    self.inlines = []

    # other inherited
    self.save_on_top = False
    self.save_as = False
    self.dynamic_config_context = {
        'title': None,
        'show_save': False,
        'show_save_and_continue': False,
        'show_save_and_add_another': False,
        'pyaedj_form_help_text': None,
        'form_save_button_text': 'Save',
        'form_cancel_button_text': 'Cancel',
        'page_heading': None,
        'current_view': None,
        'multistep_views': [],
    }

    # internal
    self._accessible_action_keys = []
    self.change_form_template = None

  def get_accessible_action_keys(self):
    if not hasattr(self, '_accessible_action_keys'):
      return []
    return self._accessible_action_keys

  def get_link_to_action(self, name):
    if isinstance(name, RedirectAction):
      return './?%s=%s' % (self._ACTION_REDIRECT_NAME, name.target_url)
    # TODO(psimakov): consider using resolvers here
    if self._use_query_string_view_routing():
      return './?%s=%s' % (self._get_action_param_name(), name)
    else:
      return '../%s/' % name

  def _compute_accessible_action_keys(self, request, obj):
    self._accessible_action_keys = []
    for key, form_class in self.get_form_view_defs().iteritems():
      if key is None or key == self.ACTION_ADD_NAME:
        continue
      form = form_class()
      if form.can_access(request, obj):
        self._accessible_action_keys.append(key)

  def render_change_form(
      self, request, context, add=False, change=False, form_url='', obj=None):
    """Customizes form view just before it is rendered."""
    add = False
    change = False
    adminform = context['adminform']
    for name, value in self.field_labels.iteritems():
      if name not in adminform.form.fields:
        continue
      adminform.form.fields[name].label = value
    # pylint: disable=protected-access
    adminform.form._meta.labels = self.field_labels
    # pylint: enable=protected-access
    context.update(self.dynamic_config_context)
    self.personalize_context_vars(context, request)
    return super(BaseCustomModelAdmin, self).render_change_form(
        request, context, add, change, form_url, obj)

  def _patch_clean_method_into(self, form, request, obj):
    def _clean(instance, request, obj):
      self.validate_form_data(request, instance, obj)
      return instance.cleaned_data

    form.clean = lambda x: _clean(x, request, x.instance)

  def _get_request_action(self, request):
    """Inspects request to figure out what action view is being requested."""
    if self._use_query_string_view_routing():
      action = request.GET.get(self._get_action_param_name())
    else:
      # all our object URLs are in the standard form and ending with slash:
      #   /cms/{{ model }}-{{ pk }}/{{ action }}/
      if request.path.endswith('/%s/' % self._ACTION_CHANGE_NAME):
        return None
      parts = request.path.split('/')
      action = parts[-2]
    return action

  def get_form(self, request, obj=None, **kwargs):
    """Based on action, selects and calls configure() on a form."""
    # keep the original object before any updates are applied to it
    if obj:
      self.active_record_obj_before_update = obj.__class__.objects.get(
          pk=obj.pk)
      self.active_record_dict_before_update = get_dict_for_model_instance(
          self.active_record_obj_before_update)
    else:
      self.active_record_obj_before_update = None
      self.active_record_dict_before_update = None

    # get desired action and the corresponding form class name
    action = self._get_request_action(request)

    if not action and obj is None:
      action = self.ACTION_ADD_NAME
    form_class = self.get_form_view_defs().get(action)
    if not form_class:
      raise exceptions.PermissionDenied()

    # reset
    self._reset_all_fields()
    self._compute_accessible_action_keys(request, obj)

    # create and configure
    form_view = form_class()
    if not form_view.can_access(request, obj):
      raise exceptions.PermissionDenied()
    form_view.configure(request, self, obj)

    # reset and recopy fields
    title = form_view.title
    if not title:
      title = form_view.ACTION_TITLE
    self.dynamic_config_context['title'] = title
    self.dynamic_config_context['page_heading'] = form_view.PAGE_HEADING
    self.dynamic_config_context['show_save'] = form_view.show_save
    self.dynamic_config_context[
        'pyaedj_form_help_text'] = form_view.FORM_HELP_TEXT
    self.dynamic_config_context['form_save_button_text'] = (
        form_view.FORM_SAVE_BUTTON_TEXT)
    self.dynamic_config_context['form_cancel_button_text'] = (
        form_view.FORM_CANCEL_BUTTON_TEXT)
    self.dynamic_config_context['current_view'] = form_view
    self.dynamic_config_context['multistep_views'] = form_view.multistep_views

    self.fieldsets = form_view.fieldsets
    self.fields = form_view.fields
    self.field_labels = form_view.field_labels
    self.readonly_fields = form_view.readonly_fields
    self.filter_horizontal = form_view.filter_horizontal
    self.inlines = form_view.INLINES

    self.add_form_template = form_view.add_form_template
    self.change_form_template = form_view.change_form_template

    # select appropriate form
    self.form = form_view.form if form_view.form else ModelForm

    # add dynamic base class to self
    self.__class__.__bases__ = (form_class,) + self.__class__.__bases__

    # execute the inherited method
    form = super(BaseCustomModelAdmin, self).get_form(request, obj, **kwargs)

    # suppress the generic message for multi-select widget
    for _, (_, field) in enumerate(form.base_fields.iteritems()):
      if isinstance(field, forms.models.ModelMultipleChoiceField):
        field.help_text = field.help_text.replace(
            'Hold down "Control", or "Command" on a Mac, to select more than '
            'one.', '')

    # patch the form
    self._patch_clean_method_into(form, request, obj)

    return form

  def _get_cancel_url(self, request, object_id):
    """Creates an appropriate cancel URL: to list view or to obejct view."""
    if self._use_query_string_view_routing():
      # current path: /cms/{{ model }}-{{ pk }}/change/?cms-action{{ action }}
      if object_id is None:
        url = request.path + '../'
      else:
        url = request.path
      return HttpResponseRedirect(url)
    else:
      # current path: /cms/{{ model }}-{{ pk }}/{{ action }}/
      if object_id is None:
        url = request.path + '../'
      else:
        url = request.path + '../%s/' % self._ACTION_CHANGE_NAME
      return HttpResponseRedirect(url)

  def changeform_view(
      self, request, object_id=None, form_url='', extra_context=None):
    """Custom changeform_view() that delegates to one of FORM_VIEWS."""
    if not self.get_form_view_defs():
      raise exceptions.PermissionDenied()

    # check if redirect action
    redirect_to = request.GET.get(self._ACTION_REDIRECT_NAME)
    if redirect_to:
      return HttpResponseRedirect(redirect_to)

    # check if edit is cancelled
    action = request.POST.get('_cancel')
    if action:
      return self._get_cancel_url(request, object_id)

    # reset
    self._reset_all_fields()

    # remember our old methods to restore them and call inhertited
    old_bases = self.__class__.__bases__
    try:
      return super(BaseCustomModelAdmin, self).changeform_view(
          request, object_id, form_url, extra_context)
    finally:
      self.__class__.__bases__ = old_bases

  def changelist_view(self, request, extra_context=None):
    """Custom changelist_view() that delegates to LIST_VIEW."""
    extra_context = extra_context if extra_context else {}

    if not self.get_list_view_def():
      raise exceptions.PermissionDenied()
    list_view_class = self.get_list_view_def()

    # reset
    self._reset_all_fields()

    # create and configure
    list_view = list_view_class()  # pylint: disable=not-callable
    if not list_view.can_access(request):
      raise exceptions.PermissionDenied()
    list_view.configure(request, self)

    # reset and recopy fields
    self.actions = list_view.actions
    self.list_display = list_view.list_display
    self.list_display_links = list_view.list_display_links
    self.list_filter = list_view.list_filter
    self.search_fields = list_view.search_fields
    self.ordering = list_view.ordering
    self.list_editable = list_view.list_editable
    self.list_display_links = list_view.list_display_links
    self.change_list_template = list_view.change_list_template

    # Add extra context data for use during template render.
    self.personalize_context_vars(extra_context, request)
    if list_view.ACTION_TITLE:
      extra_context['title'] = list_view.ACTION_TITLE
    extra_context['add_button_text'] = (
        list_view.ADD_BUTTON_TEXT or 'Add %s' % self.opts.verbose_name)
    extra_context['pyaedj_list_help_text'] = list_view.LIST_HELP_TEXT

    # add dynamic base class to self and invoke inherited
    old_bases = self.__class__.__bases__
    try:
      self.__class__.__bases__ = (list_view_class,) + self.__class__.__bases__
      return super(BaseCustomModelAdmin, self).changelist_view(
          request, extra_context)
    finally:
      self.__class__.__bases__ = old_bases

  def response_add(self, request, obj, post_url_continue=None):
    """Called after form has been submitted and a new object has been added."""
    messages.add_message(
        request, messages.INFO, '%s has been added' % obj.__class__.__name__)
    return HttpResponseRedirect(_get_object_view_url(self.APP_NAME, obj))

  def response_change(self, request, obj):
    """Called after form has been submitted and an object has been changed."""
    messages.add_message(
        request, messages.INFO, '%s has been updated' % obj.__class__.__name__)
    return HttpResponseRedirect(_get_object_view_url(self.APP_NAME, obj))

  # Override has-*permission since we don't use the Django permission system.
  # Individual view classes, will adjust these appropriately.

  def has_module_permission(self, unused_request):
    return True

  def has_add_permission(self, request):
    """See if we have action view for add and forward to its can_access()."""
    view_classes = self.get_form_view_defs()
    if view_classes and self.ACTION_ADD_NAME in view_classes:
      form_class = view_classes.get(self.ACTION_ADD_NAME)
      form_view = form_class()
      return form_view.can_access(request, None)
    return False

  def has_change_permission(
      self, unused_request, obj=None):  # pylint: disable=unused-argument
    return True

  # TODO(psimakov): can we make this permission forward to action views like
  # we already do in has_add_permission?
  def has_delete_permission(
      self, unused_request, obj=None):  # pylint: disable=unused-argument
    return False

  # Disable object action logging. We don't need it and don't use it.
  def log_addition(self, unused_request, unused_object, unused_message):
    pass

  def log_change(self, unused_request, unused_object, unused_message):
    pass

  def log_deletion(self, unused_request, unused_object, unused_object_repr):
    pass


class BaseCustomListView(object):
  """Base class for custom list views."""

  ACTION_TITLE = None
  ADD_BUTTON_TEXT = None
  LIST_HELP_TEXT = None

  def __init__(self):
    self.actions = None
    self.list_display = ()
    self.list_display_links = ()
    self.list_filter = ()
    self.search_fields = ()
    self.ordering = ()
    self.list_editable = ()
    self.list_display_links = ()
    self.change_list_template = None

  # TODO(psimakov): add suport for bulk actions; each action to be a first class
  # object with own can_access(), validate(), etc. nretallack@ has a fully
  # working example of how to do it, but that example does not go as far as
  # making bulk action views first class objects and fully controlling their
  # lifecycle at framework level.

  def can_access(self, unused_request):
    """Controls who can access this view."""
    return True

  def configure(self, unused_request):
    """Override this method to configure the view."""
    raise Exception('Not implemented')


class BaseCustomFormView(object):
  """Base class for custom form views."""

  ACTION = None
  ACTION_TITLE = None
  FORM_HELP_TEXT = None
  FORM_SAVE_BUTTON_TEXT = 'Save'
  FORM_CANCEL_BUTTON_TEXT = 'Cancel'
  PAGE_HEADING = None
  INLINES = []
  MULTISTEP_VIEWS = []

  def __init__(self):
    self.show_save = False
    self.fields = ()
    self.fieldsets = ()
    self.field_labels = {}
    self.readonly_fields = ()
    self.filter_horizontal = ()
    self.title = None
    self.form = None
    self.add_form_template = None
    self.change_form_template = None
    self.multistep_views = []

  @classmethod
  def extract_field_names_from(cls, fieldsets):
    """Extracts all fields from the fieldsets into a flat list."""
    names = []
    for fieldset in fieldsets:
      names += flatten(fieldset[1]['fields'])
    return names

  def can_access(self, unused_request, unused_obj):
    """Controls who can access this form."""
    return True

  def validate_form_data(
      self, unused_request, unused_form, unused_obj):
    """Override this method to validate the form submission."""
    pass

  def configure(self, unused_request, unused_modeladmin, unused_obj):
    """Override this method to configure the form."""
    pass


# see: https://docs.djangoproject.com/en/1.9/howto/custom-lookups/
class CustomIContains(IContains):
  """Provides case-insensitive __icontains queries with utf8_bin collation."""

  def as_sql(self, compiler, connection):
    lhs, lhs_params = self.process_lhs(compiler, connection)
    rhs, rhs_params = self.process_rhs(compiler, connection)
    params = lhs_params + rhs_params
    return 'UPPER(%s) LIKE UPPER(%s)' % (lhs, rhs), params


class CustomIExact(IExact):
  """Provides case-insensitive __iexact queries with utf8_bin collation."""

  def as_sql(self, compiler, connection):
    lhs, lhs_params = self.process_lhs(compiler, connection)
    rhs, rhs_params = self.process_rhs(compiler, connection)
    params = lhs_params + rhs_params
    return 'UPPER(%s) = UPPER(%s)' % (lhs, rhs), params


Field.register_lookup(CustomIContains)
Field.register_lookup(CustomIExact)
