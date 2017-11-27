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

"""Models."""

__author__ = 'Pavel Simakov (psimakov@google.com)'

import uuid
from django.db import models


MAX_CHAR_LEN = 255


def new_random_key():
  return uuid.uuid4().int


def new_person_pk():
  return 'person-%s' % new_random_key()


class Person(models.Model):
  """Story."""
  id = models.CharField(max_length=MAX_CHAR_LEN, primary_key=True,
                        default=new_person_pk)
  email = models.CharField(max_length=MAX_CHAR_LEN, unique=True, db_index=True)
