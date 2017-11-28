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

r"""Command Line Interface to Managing Various Platform Tasks.


Ongoing Administeration on Ubuntu 16.04 LTS
  * managing pip:
    > pip list
    > pip show MySQL-Python
  * managing MySQL:
    > sudo /etc/init.d/mysql stop
    > sudo /etc/init.d/mysql start
  * disable MySQL passwords checking:
    > sudo /etc/init.d/mysql stop
    > sudo nano /etc/mysql/my.cnf  # add [mysqld]\nskip-grant-tables
    > sudo /etc/init.d/mysql start


Good Luck!
"""

__author__ = 'Pavel Simakov (psimakov@google.com)'


import logging
import os
import unittest
from common import cli
import config


def _deploy_service(cmd, name):
  version, _ = cmd.shell('date +%s')
  assert version
  version = '%s-%s' % (name, version)
  try:
    cmd.shell(
        'gcloud app create --quiet --region us-central '
        '--project {project_id}'.format(project_id=config.ENV.project_id))
    config.LOG.info('Created new application.')
  except Exception as e:  # pylint: disable=broad-except
    if 'already contains an App Engine application' in str(e):
      config.LOG.info('Found existing App Engine app: %s',
                      config.ENV.project_id)
    else:
      raise
  config.LOG.info('Starting App Engine Standard deployment for %s, version %s.',
                  name, version)
  cmd.shell('rm -f index.yaml')
  cmd.shell('cp %s_main.index.yaml index.yaml' % name)
  try:
    cmd.shell(
        'gcloud app deploy --quiet --project {project_id} '
        '--version {version} {name}_main.yaml'.format(
            project_id=config.ENV.project_id, name=name,
            version=version.strip()))
    cmd.shell(
        'gcloud datastore --quiet --project {project_id} '
        'create-indexes index.yaml'.format(project_id=config.ENV.project_id))
  finally:
    cmd.shell('rm -f index.yaml')
  config.LOG.info('Deployed and live: %s.', version)


class DepsInstall(cli.Command):
  NAME = 'deps_install'
  DESC = 'Installs all dependencies defined by requirements.txt.'

  def execute(self):
    # uninstall first
    DepsUnInstall().execute()

    # check pre-requisites
    for package in [
        'python', 'gcloud', 'gsutil', 'mysql', 'mysql_config', 'pip'
    ]:
      try:
        version, _ = self.shell('%s --version' % package, silent=True)
        config.LOG.info('Found %s: %s', package, version)
      except:
        config.LOG.info('Not found: %s', package)
        raise

    # install App Engine into gcloud
    self.shell(
        'gcloud --project {project_id} --quiet '
        'components install app-engine-python'.format(
            project_id=config.ENV.project_id))

    # install all pip requirements
    self.shell('pip install -t lib -r requirements.txt')


class DepsUnInstall(cli.Command):
  NAME = 'deps_uninstall'
  DESC = 'Uninstalls all dependencies defined by requirements.txt.'

  def execute(self):
    self.shell('rm -rf ./lib')


class UnitTests(cli.Command):
  NAME = 'unit_tests'
  DESC = 'Runs all unit tests.'

  def execute(self):
    os.environ['DJANGO_SETTINGS_MODULE'] = 'modules.web.settings.dev'
    import django  # pylint: disable=g-import-not-at-top
    django.setup()

    old_level = config.LOG.level
    config.LOG.level = logging.CRITICAL
    try:
      runner = unittest.TextTestRunner()
      suite = unittest.TestLoader().discover(os.path.dirname(__file__))
      with cli.gcloud_project(self, config.ENV.project_id):
        result = runner.run(suite)
      if not result.wasSuccessful() or result.errors:
        raise Exception(result)
    finally:
      config.LOG.level = old_level


def django_admin(args):
  from django.core import management  # pylint: disable=g-import-not-at-top
  os.environ['DJANGO_SETTINGS_MODULE'] = 'modules.web.settings.dev'
  management.execute_from_command_line(['manage.py'] + args)
  del os.environ['DJANGO_SETTINGS_MODULE']


class AppRun(cli.Command):
  NAME = 'app_run'
  DESC = 'Runs WEB local test server on http://localhost:8080.'
  SETTINGS_MODULE = 'modules.web.settings.dev'

  def execute(self):
    django_admin(['collectstatic', '--noinput', '--link'])

    config.LOG.info('Running local server on http://localhost:8080')
    config.LOG.info('Press Ctrl-C to stop.')
    self.shell(
        'python {userhome}/google-cloud-sdk/bin/dev_appserver.py '
        '--max_module_instances=1 '         # to allow only one server instance
        '--use_mtime_file_watcher=True '    # to allow code reload while running
        '--dev_appserver_log_level=debug '  # to see exception on the console
        '--log_level=debug '
        '--env_var DJANGO_SETTINGS_MODULE=modules.web.settings.dev '
        'web_main.yaml'.format(userhome=os.path.expanduser('~')), live=True)


class WebDeploy(cli.Command):
  """Deploy version of Web to App Engine."""

  NAME = 'web_deploy'
  DESC = 'Deploy web module to production.'
  PYTHON_TASK = True

  def execute(self):
    UnitTests().execute()
    _deploy_service(self, 'web')


class MigrationsMake(cli.Command):
  """Makes database migrations."""

  NAME = 'migrations_make'
  DESC = 'Makes database migrations.'

  def execute(self):
    django_admin(['makemigrations', '--noinput', 'cms'])


class MigrationsApply(cli.Command):
  """Applies database migrations."""

  NAME = 'migrations_apply'
  DESC = 'Applies database migrations.'

  def execute(self):
    for app in ['admin', 'sessions', 'cms']:
      django_admin(['migrate', app, '--noinput'])


cli.Command.register(AppRun)
cli.Command.register(DepsInstall)
cli.Command.register(DepsUnInstall)
cli.Command.register(MigrationsApply)
cli.Command.register(MigrationsMake)
cli.Command.register(UnitTests)
cli.Command.register(WebDeploy)


def _del_all_pyc_files(cmd):
  cmd.shell('find {dir_name} -name *.pyc -type f -delete'.format(
      dir_name=os.path.abspath(os.path.dirname(__file__))))


if __name__ == '__main__':
  _del_all_pyc_files(cli.Command)
  cli.Command.dispatch()
