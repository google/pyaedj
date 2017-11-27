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

"""Classes and Functions to Control Command Execution From Console."""

__author__ = 'Pavel Simakov (psimakov@google.com)'


import argparse
from contextlib import contextmanager
import io
import subprocess
import sys
import threading
import config


@contextmanager
def gcloud_project(command, project_id):
  command.shell('gcloud config set project {project_id}'.format(
      project_id=project_id))
  try:
    yield None
  finally:
    command.shell('gcloud config unset project')


def tee(live, infile, *files):
  """Print `infile` to `files` in a separate thread."""
  def fanout(infile, *files):
    for line in iter(infile.readline, ''):
      for f in files:
        try:
          f.write(line.decode('utf-8'))
          if live:
            config.LOG.info(line.strip())
        except UnicodeEncodeError:
          config.LOG.error('Failed to log console output: %s', line)
    infile.close()
  t = threading.Thread(target=fanout, args=(infile,)+files)
  t.daemon = True
  t.start()
  return t


def teed_call(cmd_args, **kwargs):
  """Setup pipes and call subprocess."""
  stdout, stderr = [kwargs.pop(s, None) for s in ['stdout', 'stderr']]
  silent = [kwargs.pop(s, None) for s in ['silent']]
  live = [kwargs.pop(s, None) for s in ['live']]
  p = subprocess.Popen(cmd_args,
                       stdout=subprocess.PIPE if stdout is not None else None,
                       stderr=subprocess.PIPE if stderr is not None else None,
                       **kwargs)
  threads = []
  if stdout is not None:
    streams = [p.stdout, stdout] if silent else [p.stdout, stdout, sys.stdout]
    threads.append(tee(live, *streams))
  if stderr is not None:
    streams = [p.stderr, stderr] if silent else [p.stderr, stderr, sys.stderr]
    threads.append(tee(live, *streams))
  for t in threads:
    t.join()
  return p.wait()


def _args_to_str(args):
  results = []
  for arg in args:
    if ' ' in arg:
      results.append('"%s"' % arg)
    else:
      results.append(arg)
  return ' '.join(results)


def _to_unicode(val, encoding='utf-8'):
  if isinstance(val, unicode):
    return val
  elif isinstance(val, str):
    return val.decode(encoding)
  else:
    raise Exception('Unexpected value: %s' % val)


class Command(object):
  """An command that has its own args and can be executed from console."""

  NAME = None
  DESC = None
  PYTHON_TASK = False
  COMMANDS = {}

  @classmethod
  def shell(cls, cmd, args=None, silent=False, live=False):
    """Executes command while streaming and capturing STDERR and STDOUT."""
    # from here: https://stackoverflow.com/questions/4984428/
    #    python-subprocess-get-childrens-output-to-file-and-terminal/
    #    4985080#4985080
    # from here: https://stackoverflow.com/questions/25750468/
    #    displaying-subprocess-output-to-stdout-and-redirecting-it
    if not args:
      assert cmd
      args = cmd.split(' ')
    if not silent:
      config.LOG.info('Shell: %s', ' '.join(args))
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    returncode = teed_call(args, stdout=stdout_buf, stderr=stderr_buf,
                           universal_newlines=True, silent=silent, live=live)
    output = (
        _to_unicode(stdout_buf.getvalue()),
        _to_unicode(stderr_buf.getvalue())
    )
    if returncode:
      raise Exception(
          'Command failed with an error code %s: %s\n(%s)\n(%s)' % (
              returncode, _args_to_str(args), output[1], output[0]))
    return output[0], output[1]

  @classmethod
  def shell_script(cls, text):
    """Executes each non-empty line of text as a separate shell command."""
    results = []
    lines = text.strip().split('\n')
    for line in lines:
      if not line or line.strip().startswith('#'):
        continue
      results.append(cls.shell(line.strip()))
    return results

  @classmethod
  def register(cls, action_class):
    assert action_class.NAME, 'Action requires name'
    assert action_class.NAME not in cls.COMMANDS, (
        'Action %s already registered' % action_class.NAME)
    cls.COMMANDS[action_class.NAME] = action_class()

  @classmethod
  def root_parser(cls):
    parser = argparse.ArgumentParser()
    parser.add_argument('--python', default=None)
    parser.add_argument('action', choices=cls.COMMANDS.keys(),
                        help='A name of the action to execute.')
    parser.add_argument('args', nargs=argparse.REMAINDER)
    return parser

  @classmethod
  def default_parser(cls, command):
    """Creates default command argument parser."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--python', default=None)
    parser.add_argument('action', choices=[command.NAME],
                        help='A name of the action to execute.')
    return parser

  @classmethod
  def _list_commands(cls):
    lines = []
    for command in Command.COMMANDS.values():
      lines.append('\t%s:\t%s' % (command.NAME, command.DESC))
    lines = sorted(lines)
    return '\n'.join(lines)

  @classmethod
  def dispatch(cls):
    """Receives, parses, validates and dispatches arguments to an action."""
    parser = cls.root_parser()
    try:
      parsed_args = parser.parse_args()
      cmd = Command.COMMANDS.get(
          parser.parse_args().action, (None, None))
      if not cmd:
        print 'Unknown action: %s' % parsed_args.action
        raise Exception()
    except:  # pylint: disable=bare-except
      print 'Usage: project.py [-h] action ...'
      print 'Valid actions are:\n%s' % cls._list_commands()
      sys.exit(1)

    assert cmd
    cmd_parser = cmd.make_parser
    cmd_args = cmd_parser().parse_args()
    assert cmd_args.action == parser.parse_args().action
    assert not cmd.args
    cmd.args = cmd_args

    # clear args so Google SDK or other libs will not try to use the values
    sys.argv = [sys.argv[0]]

    config.LOG.info('Starting action: %s', cmd_args.action)
    try:
      cmd.execute()
    finally:
      cmd.args = None
    config.LOG.info('Completed action: %s', cmd_args.action)

  def __init__(self):
    self.args = None

  def make_parser(self):
    """Returns args parser for this command."""
    return self.default_parser(self)

  def execute(self):
    """Executes the command."""
    raise NotImplementedError()
