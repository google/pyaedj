"""DAO classes."""


__author__ = 'Pavel Simakov (psimakov@google.com)'


import datetime
import json
import uuid
import pytz
from google.cloud import datastore
import container


# serialization date format
ISO_8601_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'

# limits
MAX_MEMBERS_IN_LIST = 500
MAX_POSTS_IN_LIST = 500

# special value for FALSE in Datastore queries
_FALSE_VALUE = False


def to_utc(value):
  return value.replace(tzinfo=pytz.utc)  # pylint: disable=g-tzinfo-replace


def timezone_aware_now():
  return to_utc(datetime.datetime.utcnow())


def str_to_datetime(value):
  return datetime.datetime.strptime(value, ISO_8601_DATETIME_FORMAT)


def datetime_to_str(value):
  return to_utc(value).isoformat()


class BusinessRuleError(Exception):
  """Any error sent out to the client application and possibly user."""

  def to_json_serializable(self):
    return {
        'origin': 'pyaedj.common.pwa.server',
        'code': self.__class__.__name__,
        'message': str(self),
    }


class InvalidFieldValueError(BusinessRuleError):
  """Any error where named attribute was invalid."""

  def __init__(self, attr_name, message):
    super(InvalidFieldValueError, self).__init__(message)
    self.attr_name = attr_name

  def to_json_serializable(self):
    result = super(InvalidFieldValueError, self).to_json_serializable()
    result['name'] = self.attr_name
    return result


class NotFoundError(BusinessRuleError):
  """Entity not found."""
  pass


class ETagError(BusinessRuleError):
  """ETag provided alongside a mutation is out of date."""
  pass


class _Member(object):
  """Persistent entity Member."""

  def __init__(self, obj):
    assert obj
    self._key = obj.key
    self._obj = obj

  @property
  def key(self):
    return self._key

  @property
  def slug(self):
    return self._obj['slug']

  @property
  def data(self):
    return self._obj['data']

  @property
  def created_on(self):
    return self._obj['created_on']

  @property
  def updated_on(self):
    return self._obj['updated_on']

  @property
  def version(self):
    return self._obj['version']


class Members(object):
  """Facade for Datastore table Members."""

  TABLE = 'Members'

  def __init__(self, client=None):
    if not client:
      client = container.Registry.current().datastore_client
    self.client = client

  def _key(self, uid=None):
    if uid:
      return self.client.key(self.TABLE, uid)
    return self.client.key(self.TABLE)

  def query_members(self):
    """Returns all members."""
    query = self.client.query(kind=self.TABLE)
    results = []
    for item in query.fetch():
      results.append(_Member(item))
    return results

  def get_or_create_member(self, uid, create_if_not_found=True):
    """Loads existing or creates new member entity."""
    with self.client.transaction():
      # load object
      key = self._key(uid)
      obj = self.client.get(key)

      # existing found
      if obj:
        return _Member(obj)

      # created new
      if create_if_not_found:
        obj = datastore.Entity(key)
        obj.update({
            'slug': str(uuid.uuid4()),
            'data': '{}',
            'created_on': datetime.datetime.utcnow(),
            'version': 1,
        })
        self.client.put(obj)
        return _Member(obj)

      # not found and not created
      return None

  def update(self, uid, data, version=None):
    """Updates existing member entity."""
    with self.client.transaction():
      # make sure payload is JSON parsable string
      if data:
        json.loads(data)
      else:
        data = '{}'

      # load object
      key = self._key(uid)
      obj = self.client.get(key)

      # none exists
      if not obj:
        raise NotFoundError('No member for uid "%s".' % uid)

      old = _Member(obj)
      if version is not None:
        if str(version) != str(old.version):
          raise ETagError(
              'Object was modified by someone from version V%s to V%s.' %
              (version, old.version))
      obj.update({
          'data': data,
          'updated_on': datetime.datetime.utcnow(),
          'version': old.version + 1,
      })
      self.client.put(obj)


class _Post(object):
  """Persistent entity Post."""

  def __init__(self, obj):
    assert obj
    self._key = obj.key
    self._obj = obj

  @property
  def key(self):
    return self._key

  @property
  def member_uid(self):
    return self._obj['member_uid']

  @property
  def data(self):
    return self._obj['data']

  @property
  def created_on(self):
    return self._obj['created_on']

  @property
  def updated_on(self):
    return self._obj['updated_on']

  @updated_on.setter
  def updated_on(self, updated_on):
    self._obj['updated_on'] = updated_on

  @property
  def votes_up(self):
    return self._obj['votes_up']

  @votes_up.setter
  def votes_up(self, votes_up):
    self._obj['votes_up'] = votes_up

  @property
  def votes_down(self):
    return self._obj['votes_down']

  @votes_down.setter
  def votes_down(self, votes_down):
    self._obj['votes_down'] = votes_down

  @property
  def votes_total(self):
    return self._obj['votes_total']

  @votes_total.setter
  def votes_total(self, votes_total):
    self._obj['votes_total'] = votes_total

  @property
  def is_deleted(self):
    return self._obj['is_deleted']

  @property
  def version(self):
    return self._obj['version']

  @version.setter
  def version(self, version):
    self._obj['version'] = version


class Posts(object):
  """Facade for Datastore table Posts."""

  TABLE = 'Posts'

  def __init__(self, client=None):
    if not client:
      client = container.Registry.current().datastore_client
    self.client = client
    self.members = Members(client=client)

  def _key(self, uid=None):
    if uid:
      return self.client.key(self.TABLE, uid)
    return self.client.key(self.TABLE)

  def query_posts(self):
    """Returns all posts."""
    query = self.client.query(kind=self.TABLE)
    query.add_filter('is_deleted', '=', _FALSE_VALUE)
    query.order = '-votes_total'
    results = []
    for item in query.fetch():
      results.append(_Post(item))
    return results

  def query_member_posts(self, member_uid):
    """Returns all posts by a member."""
    query = self.client.query(kind=self.TABLE)
    query.add_filter('is_deleted', '=', _FALSE_VALUE)
    query.add_filter('member_uid', '=', str(member_uid))
    query.order = '-votes_total'
    results = []
    for item in query.fetch():
      results.append(_Post(item))
    return results

  def get_post(self, post_uid):
    post_key = self._key(post_uid)
    post = self.client.get(post_key)
    if not post:
      raise NotFoundError('No post for post_uid "%s".' % post_uid)
    return _Post(post)

  def insert_post(self, member_uid, post_data):
    """Inserts new post from user."""

    with self.client.transaction():
      # make sure payload is JSON parsable string
      if post_data:
        json.loads(post_data)
      else:
        post_data = '{}'

      # verify user exists
      member_key = self.members._key(  # pylint: disable=protected-access
          member_uid)
      member = self.client.get(member_key)
      if not member:
        raise NotFoundError('No member for uid "%s".' % member_uid)

      # add new post
      post_key = self._key()
      post = datastore.Entity(post_key)
      post.update({
          'member_uid': str(member_uid),
          'data': post_data,
          'votes_up': 0,
          'votes_down': 0,
          'votes_total': 0,
          'is_deleted': False,
          'created_on': datetime.datetime.utcnow(),
          'version': 1,
      })
      self.client.put(post)
      return _Post(post)

  def mark_post_deleted(self, member_uid, post_uid):
    """Marks post deleted."""

    with self.client.transaction():
      # load post
      post_key = self._key(post_uid)
      post = self.client.get(post_key)
      if not post:
        raise NotFoundError('No post for post_uid "%s".' % post_uid)

      # only author can mark post deleted
      if post['member_uid'] != member_uid:
        raise BusinessRuleError('Access denied deleting post.')

      # update
      post.update({
          'is_deleted': True,
      })
      self.client.put(post)


class _Vote(object):
  """Persistent entity Vote."""

  def __init__(self, obj):
    assert obj
    self._key = obj.key
    self._obj = obj

  @property
  def key(self):
    return self._key

  @property
  def post_uid(self):
    return self._obj['post_uid']

  @property
  def member_uid(self):
    return self._obj['member_uid']

  @property
  def value(self):
    return self._obj['value']

  @value.setter
  def value(self, value):
    self._obj['value'] = value

  @property
  def created_on(self):
    return self._obj['created_on']

  @property
  def updated_on(self):
    return self._obj['updated_on']

  @updated_on.setter
  def updated_on(self, updated_on):
    self._obj['updated_on'] = updated_on

  @property
  def version(self):
    return self._obj['version']

  @version.setter
  def version(self, version):
    self._obj['version'] = version


class Votes(object):
  """Facade for Datastore table Votes."""

  TABLE = 'Votes'

  def __init__(self, client=None):
    if not client:
      client = container.Registry.current().datastore_client
    self.client = client
    self.posts = Posts(client=client)

  def _key(self, uid=None):
    if uid:
      return self.client.key(self.TABLE, uid)
    return self.client.key(self.TABLE)

  def _fetch(self, query):
    results = []
    for item in query.fetch():
      results.append(_Vote(item))
    return results

  def query_votes(self):
    """Returns all votes."""
    query = self.client.query(kind=self.TABLE)
    query.order = '-created_on'
    return self._fetch(query)

  def query_member_votes(self, member_uid):
    """Returns all member votes."""
    query = self.client.query(kind=self.TABLE)
    query.add_filter('member_uid', '=', str(member_uid))
    query.order = '-created_on'
    return self._fetch(query)

  def query_member_votes_for(self, member_uid, post_uids):
    """Returns all votes for specific user and posts."""

    #
    # TODO(psimakov): this is ideally done using IN query, which was available
    # in NDB like this:
    #
    #   post_uids_str = [str(item) for item in post_uids]
    #   return Votes.query(namespace=dao.NS_NAME).filter(ndb.AND(
    #       Votes.member_uid == str(member_uid),
    #       Votes.post_uid.IN(post_uids_str)
    #   )).order(-Votes.created_on).iter()
    #

    if not post_uids:
      return []

    # fet all user votes
    post_uids = set([str(item) for item in post_uids])
    query = self.client.query(kind=self.TABLE)
    query.add_filter('member_uid', '=', str(member_uid))
    query.order = '-created_on'

    # select only votes for requested posts
    results = []
    for item in query.fetch():
      vote = _Vote(item)
      if vote.post_uid in post_uids:
        results.append(vote)
    return results

  def query_post_votes(self, post_uid):
    """Returns all post votes."""
    query = self.client.query(kind=self.TABLE)
    query.add_filter('post_uid', '=', str(post_uid))
    query.order = '-created_on'
    return self._fetch(query)

  def insert_vote(self, member_uid, post_uid, value):
    """Inserts new vote from user."""

    if value not in set([1, -1]):
      raise BusinessRuleError(
          'Allowed vote values are +1 and -1, was "%s".' % value)

    with self.client.transaction():
      utcnow = datetime.datetime.utcnow()

      # load post
      post_key = self.posts._key(post_uid)  # pylint: disable=protected-access
      post_ = self.client.get(post_key)
      if not post_:
        raise NotFoundError('No post for post_uid "%s".' % post_uid)
      post = _Post(post_)

      # make new composite key for vote
      composite_uid = '%s/%s' % (post_uid, member_uid)
      vote_key = self._key(composite_uid)
      vote_ = self.client.get(vote_key)

      old_value = None
      if not vote_:
        # add new vote if not exists
        vote_ = datastore.Entity(vote_key)
        vote_.update({
            'post_uid': str(post_uid),
            'member_uid': str(member_uid),
            'created_on': utcnow,
            'version': 0,
        })
        vote = _Vote(vote_)
      else:
        # revert old vote from post
        vote = _Vote(vote_)
        old_value = vote.value
        if vote.value == 1:
          post.votes_up -= 1
        elif vote.value == -1:
          post.votes_down -= 1
        elif vote.value == 0:
          # nothing to undo
          pass
        else:
          raise BusinessRuleError('Bad vote value: "%s".' % vote.value)

      # voting with the same value again nulls the vote value
      if old_value and old_value == value:
        vote.value = 0
      else:
        vote.value = value

      # update post with new vote
      if vote.value == 1:
        post.votes_up += 1
      elif vote.value == -1:
        post.votes_down += 1
      elif vote.value == 0:
        # nothing to do
        pass
      else:
        raise BusinessRuleError('Bad vote value: "%s".' % vote.value)
      post.votes_total = post.votes_up - post.votes_down

      # update vote
      vote.updated_on = utcnow
      vote.version += 1
      self.client.put(vote._obj)  # pylint: disable=protected-access

      # update post
      post.updated_on = utcnow
      post.version += 1
      self.client.put(post._obj)  # pylint: disable=protected-access

      return post, vote


def posts_query_to_list(member_uid, posts, fill_votes=True, client=None):
  """Converts query iterator to list of posts."""
  post_uids = []
  results = []
  by_post_uid = {}

  # iterate all posts
  for post in posts:
    if len(results) > MAX_POSTS_IN_LIST:
      break

    # collect ids
    post_uids.append(str(post.key.id))

    # create projection and add to output
    item = {
        'uid': post.key.id,
        'can_delete': member_uid == post.member_uid,
        'data': json.loads(post.data),
        'my_vote_value': None,
        'votes_up': post.votes_up,
        'votes_down': post.votes_down,
        'votes_total': post.votes_total,
    }
    by_post_uid[str(post.key.id)] = item
    results.append(item)

  # add votes from current user
  if fill_votes:
    votes = Votes(client=client).query_member_votes_for(member_uid, post_uids)
    for vote in votes:
      post = by_post_uid[vote.post_uid]
      post['my_vote_value'] = vote.value

  return results
