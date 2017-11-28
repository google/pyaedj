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

"""Base Django settings."""

__author__ = 'Pavel Simakov (psimakov@google.com)'

import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN_TEMPLATES_DIR = os.path.join(BASE_DIR, '..', 'cms', 'templates')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Logging configuration. We disable Django's defaults and configure our own.
# Note that, should any child settings files need to override LOGGING, they will
# have to call logging.config.dictConfig themselves to apply the overrides.
LOGGING_CONFIG = None

# SECURITY WARNING: change this value before your own deployment
SECRET_KEY = '3wbp5q4ebrb4dpztmx7otnxnph5kgapr'

# Application definition
INSTALLED_APPS = [
    # We don't use django.contrib.auth, but django.contrib.contenttypes will
    # error if its models are not present.
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'modules.web.cms',
    'django.contrib.admin',
]

AUTHENTICATION_BACKENDS = []

MIDDLEWARE_CLASSES = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'modules.web.settings.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [MAIN_TEMPLATES_DIR],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                # We don't use django.contrib.auth, but
                # django.contrib.contenttypes will error if its models are not
                # present.
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'web_main.application'


# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATIC_URL = '/static/'

# Django uses this value to limit the size an uploaded file can be in memory
# before it is stremed to the file system. Since we can't write to the
# filesystem on GAE this should always be at least slightly larger than the
# largest uploaded file we accept.
FILE_UPLOAD_HANDLERS = (
    'django.core.files.uploadhandler.MemoryFileUploadHandler',)
FILE_UPLOAD_MAX_MEMORY_SIZE = 32 * 1024 * 1024  # 32MB

DATABASES = {}
