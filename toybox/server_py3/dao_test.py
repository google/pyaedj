"""Tests."""


__author__ = 'Pavel Simakov (psimakov@google.com)'


import contextlib
import unittest
import webtest
from google.cloud import datastore
import container
import dao
import main


_TEST_PROJECT = 'TOYBOX_TEST'


class MockQueryFetch(object):
  """Mock query fetch."""

  def __init__(self, items):
    self.items = items
    self.order = None
    self.filters = []

  def fetch(self):
    results = []
    for item in self.items:
      add = True
      for afilter in self.filters:
        field, op, value = afilter
        if op == '=':
          if item[field] != value:
            add = False
            break
        else:
          raise Exception('Unsupported filter: %s' % afilter)
      if add:
        results.append(item)
    return results

  def add_filter(self, field, op, value):
    self.filters.append((field, op, value))


class MockDatastoreClient(object):
  """Mock Datastore client to use in tests."""

  def __init__(self):
    self._uid = 1
    self.items = []
    self.entities = {}
    self.entity = None

  def transaction(self):
    @contextlib.contextmanager
    def ctx():
      yield

    return ctx()

  def key(self, kind, uid=None):
    if uid:
      return datastore.Key(kind, uid, project=_TEST_PROJECT)
    return datastore.Key(kind, project=_TEST_PROJECT)

  def get(self, key):
    return self.entities.get(key)

  def put(self, entity):
    assert entity.key

    # object may have explicit key.name or key.id; if it has none
    # we need to assign new key.id
    if not (entity.key.name or entity.key.id):
      entity.key = self.key(entity.key.kind, uid=self._uid)
      self._uid += 1

    self.entity = entity
    self.items.append(('put', entity))
    self.entities[entity.key] = entity

  def query(self, kind=None):
    results = []
    for key, value in self.entities.items():
      if not kind or key.kind == kind:
        results.append(value)
    return MockQueryFetch(results)


class BaseTestSuite(unittest.TestCase):
  DATASTORE_MOCK = MockDatastoreClient

  def setUp(self):
    super(BaseTestSuite, self).setUp()
    main.app.testing = True
    self.app = webtest.TestApp(main.app)
    self.client = self.DATASTORE_MOCK()
    self.old_datastore_client = container.Registry.current().patch(
        'datastore_client', self.client)

  def tearDown(self):
    container.Registry.current().patch(
        'datastore_client', self.old_datastore_client)
    super(BaseTestSuite, self).tearDown()


class MembersTestSuite(BaseTestSuite):
  """Test cases for Members."""

  def test_get_or_create_member(self):
    members = dao.Members()
    self.assertEqual(0, len(list(members.query_members())))
    members.get_or_create_member('member-1')
    self.assertEqual(1, len(list(members.query_members())))


class PostsAndVotesBaseTestSuite(BaseTestSuite):
  """Test cases for Posts and Votes."""

  def setUp(self):
    super(PostsAndVotesBaseTestSuite, self).setUp()
    self.members = dao.Members()
    self.posts = dao.Posts()
    self.votes = dao.Votes()

  def _insert_post(self, uid, data):
    self.posts.insert_post(uid, data)
    self.assertEqual(1, len(list(self.posts.query_member_posts(uid))))
    post = list(self.posts.query_member_posts(uid))[0]
    self.assertEqual(uid, post.member_uid)
    self.assertEqual(data, post.data)

  def test_insert_one_post(self):
    uid = 'member-1'
    data = '{"content": "article 1"}'

    self.members.get_or_create_member(uid)
    self._insert_post(uid, data)

    votes = list(self.votes.query_member_votes('member-1'))
    self.assertEqual(0, len(votes))

    post = list(self.posts.query_member_posts(uid))[0]
    self.assertEqual(uid, post.member_uid)
    self.assertEqual(data, post.data)

    return post


class PostsTestSuite(PostsAndVotesBaseTestSuite):
  """Test cases for Posts."""

  def test_query_posts(self):
    posts = list(self.posts.query_posts())
    self.assertEqual(0, len(posts))

  def test_mark_post_deleted(self):
    post = self.test_insert_one_post()
    posts = list(self.posts.query_posts())
    self.assertEqual(1, len(posts))

    self.posts.mark_post_deleted('member-1', post.key.id)
    posts = list(self.posts.query_posts())
    self.assertEqual(0, len(posts))

  def test_mark_post_deleted_fails_if_not_owner(self):
    self.members.get_or_create_member('member-1')
    self.members.get_or_create_member('member-2')

    post = self.test_insert_one_post()
    with self.assertRaisesRegexp(dao.BusinessRuleError,
                                 'Access denied deleting post.'):
      self.posts.mark_post_deleted('member-2', post.key.id)

  def test_two_users_insert_two_posts(self):
    uid1 = 'member-1'
    uid2 = 'member-2'
    data1 = '{"content": "article 1"}'
    data2 = '{"content": "article 2"}'

    self.members.get_or_create_member(uid1)
    self.members.get_or_create_member(uid2)

    self._insert_post(uid1, data1)
    self._insert_post(uid2, data2)

    post1, post2 = self.posts.query_posts()

    self.assertEqual(uid1, post1.member_uid)
    self.assertEqual(data1, post1.data)

    self.assertEqual(uid2, post2.member_uid)
    self.assertEqual(data2, post2.data)


class VotesTestSuite(PostsAndVotesBaseTestSuite):
  """Test cases for Votes."""

  def test_query_votes(self):
    votes = list(self.votes.query_votes())
    self.assertEqual(0, len(votes))

  def test_member_votes(self):
    self.members.get_or_create_member('member-1')
    self.assertFalse(list(self.votes.query_member_votes('member-1')))

  def test_query_member_votes_no_posts(self):
    self.members.get_or_create_member('member-1')
    self.assertFalse(list(self.votes.query_member_votes_for(
        'member-1', [])))

  def test_query_member_votes_for(self):
    self.members.get_or_create_member('member-1')
    post = self.test_insert_one_post()
    self.assertFalse(list(self.votes.query_member_votes_for(
        'member-1', [post.key.id])))

  def test_query_post_votes(self):
    post = self.test_insert_one_post()
    votes = list(self.votes.query_post_votes(post.key.id))
    self.assertFalse(votes)

  def test_new_up_vote(self):
    post = self.test_insert_one_post()
    self.assertEqual(0, post.votes_up)

    self.votes.insert_vote('member-1', post.key.id, 1)

    votes = list(self.votes.query_votes())
    self.assertEqual(1, len(votes))

    votes = list(self.votes.query_member_votes('member-1'))
    self.assertEqual(1, len(votes))

    updated_post = self.posts.get_post(post.key.id)
    self.assertEqual(1, updated_post.votes_up)
    self.assertEqual(0, updated_post.votes_down)
    self.assertEqual(1, updated_post.votes_total)

    return post

  def test_new_down_vote(self):
    post = self.test_insert_one_post()
    self.assertEqual(0, post.votes_up)

    self.votes.insert_vote('member-1', post.key.id, -1)

    votes = list(self.votes.query_votes())
    self.assertEqual(1, len(votes))

    votes = list(self.votes.query_member_votes('member-1'))
    self.assertEqual(1, len(votes))

    updated_post = self.posts.get_post(post.key.id)
    self.assertEqual(0, updated_post.votes_up)
    self.assertEqual(1, updated_post.votes_down)
    self.assertEqual(-1, updated_post.votes_total)

    return post

  def test_revote_up_vote_to_down(self):
    post = self.test_new_up_vote()

    self.votes.insert_vote('member-1', post.key.id, -1)

    votes = list(self.votes.query_votes())
    self.assertEqual(1, len(votes))

    votes = list(self.votes.query_member_votes('member-1'))
    self.assertEqual(1, len(votes))

    updated_post = self.posts.get_post(post.key.id)
    self.assertEqual(0, updated_post.votes_up)
    self.assertEqual(1, updated_post.votes_down)
    self.assertEqual(-1, updated_post.votes_total)

  def test_revote_down_vote_to_up(self):
    post = self.test_new_down_vote()

    self.votes.insert_vote('member-1', post.key.id, 1)

    votes = list(self.votes.query_votes())
    self.assertEqual(1, len(votes))

    votes = list(self.votes.query_member_votes('member-1'))
    self.assertEqual(1, len(votes))

    updated_post = self.posts.get_post(post.key.id)
    self.assertEqual(1, updated_post.votes_up)
    self.assertEqual(0, updated_post.votes_down)
    self.assertEqual(1, updated_post.votes_total)

  def test_revoting_with_the_same_way_cancel_first_vote(self):
    post = self.test_insert_one_post()

    # no votes yet
    self.assertEqual(0, post.votes_up)
    self.assertEqual(0, post.votes_down)
    self.assertEqual(0, post.votes_total)

    votes = list(self.votes.query_post_votes(post.key.id))
    self.assertEqual(0, len(votes))

    # vote first time
    self.votes.insert_vote('member-1', post.key.id, 1)

    updated_post1 = self.posts.get_post(post.key.id)
    self.assertEqual(1, updated_post1.votes_up)
    self.assertEqual(0, updated_post1.votes_down)
    self.assertEqual(1, updated_post1.votes_total)

    votes = list(self.votes.query_post_votes(updated_post1.key.id))
    self.assertEqual(1, len(votes))
    vote = votes[0]
    self.assertEqual(1, vote.value)

    # vote second time
    self.votes.insert_vote('member-1', post.key.id, 1)

    updated_post2 = self.posts.get_post(post.key.id)
    self.assertEqual(0, updated_post2.votes_up)
    self.assertEqual(0, updated_post2.votes_down)
    self.assertEqual(0, updated_post2.votes_total)

    votes = list(self.votes.query_post_votes(updated_post2.key.id))
    self.assertEqual(1, len(votes))
    vote = votes[0]
    self.assertEqual(0, vote.value)


if __name__ == '__main__':
  unittest.main()
