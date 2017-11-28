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

"""Settings for running on the deveoper box."""

from base import *  # pylint: disable=wildcard-import

__author__ = 'Pavel Simakov (psimakov@google.com)'


# Setup connection to local db.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'HOST': 'localhost',
        'NAME': 'gaedj',
        'OPTIONS': {
            'charset': 'utf8',
            'init_command': 'SET '
                            'default_storage_engine=INNODB,'
                            'character_set_connection=utf8,'
                            'collation_connection=utf8_bin'
        },
        'PASSWORD': '',
        'PORT': '3306',
        'TEST': {
            'CHARSET': 'utf8',
            'COLLATION': 'utf8_bin',
        },
        'USER': 'root',
    }
}

# Allow debug use in dev.
DEBUG = True

# Email addresses of super users.
SUPER_USER_EMAILS = set(['pavel.simakov@gmail.com'])

# Setup allowed local hosts.
ALLOWED_HOSTS = [
    'testserver',
    'localhost',
    '127.0.0.1',
    '.localhost',
]
