"""ToyBox API Server in Python 3.7."""


__author__ = 'Pavel Simakov (psimakov@google.com)'


import datetime
import json
import logging
import mimetypes
import os
import traceback
import flask
from werkzeug.exceptions import HTTPException
import auth
import dao


# here we define user roles; roles are additive bundles of priveleges
ROLE_USER = 'user'              # id_token verified; whitelist rules passed
ROLE_MODERATOR = 'moderator'    # valid user, who has moderator priveleges
ROLE_ADMIN = 'admin'            # valid user, who has admin priveleges
ROLES_ALL = [ROLE_USER, ROLE_MODERATOR, ROLE_ADMIN]

# profile visibility
PROFILE_VISIBILITY_PRIVATE = 'private'
PROFILE_VISIBILITY_PUBLIC = 'public'
PROFILE_VISIBILITY = {
    PROFILE_VISIBILITY_PRIVATE: 'private (hidden from other site users)',
    PROFILE_VISIBILITY_PUBLIC: 'public (visible to other site users)',
}

# tags that user can assign to their profile
PROFILE_TAGS = {
    '1': 'sports',
    '2': 'dance',
    '3': 'science',
    '4': 'reading',
    '5': 'politics',
    '6': 'languages',
    '7': 'treavel',
    '8': 'art',
}

# limits
MAX_MEMBERS_IN_LIST = 500
MAX_POSTS_IN_LIST = 500

# application schema; this is delivered to the client as JSON
APP_SCHEMA = {
    'version': 'V1',
    'is_consent_required': True,
    'user': {
        'role': {
            'keys': dict([(role, role) for role in ROLES_ALL]),
        },
    },
    'profile': {
        'visibility': {
            'keys': dict([(key, key) for key in PROFILE_VISIBILITY.keys()]),
            'values': PROFILE_VISIBILITY,
        },
        'tags': PROFILE_TAGS,
    },
    'post': {
        'list': {
            'max_length': MAX_POSTS_IN_LIST,
        },
    },
    'member': {
        'list': {
            'max_length': MAX_MEMBERS_IN_LIST,
        },
    },
}

# admin email addresses
ADMIN_EMAILS = set([
    'psimakov@google.com',
])

# whitelisted domains
WHITELISTED_DOMAINS = set([])

# whitelisted emails
WHITELISTED_EMAILS = set([
    # App Script robot account to test OAuth auth
    'toybox-app-script-drive-api@a120-toybox.iam.gserviceaccount.com',
])

# Google Cloud Platform project that manages your Firebase Authentication users
FIREBASE_CLOUD_PROJECT_ID = 'psimakov-pwa'

# Firebase/OAuth user id namespaces
FIREBASE_UID_NS = '1'
OAUTH_UID_NS = '2'

# JSON response details
API_RESPONSE_PREFIX = ')]}\'\n'
API_RESPONSE_CONTENT_TYPE = 'application/json; charset=utf-8'

# allowed static hosting roots
STATIC_SERVING_ROOTS = set([
    'img',
    'css',
    'js',
])

# relative path to static assets
STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')
if not os.path.isdir(STATIC_DIR):
  STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')
  assert os.path.isdir(STATIC_DIR), 'Invalid static folder: %s' % STATIC_DIR

# we need to id_token verifier, which is bpound to Firebase project_id
firebase_utils = auth.FirebaseAppUtils(FIREBASE_CLOUD_PROJECT_ID)
oauth2_utils = auth.OAuth2AppUtils(FIREBASE_CLOUD_PROJECT_ID)


def parse_api_response(body):
  assert body.startswith(API_RESPONSE_PREFIX)
  unprefixed = body[len(API_RESPONSE_PREFIX):]
  return json.loads(unprefixed)


def set_cors_headers(headers):
  headers['Access-Control-Allow-Origin'] = '*'
  headers['Access-Control-Allow-Headers'] = '*'
  headers['Access-Control-Allow-Methods'] = '*'


def set_no_cache_headers(headers):
  headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
  headers['Expires'] = 'Mon, 01 Jan 1990 00:00:00 GMT'
  headers['Pragma'] = 'no-cache'


def serve_static_file(filename):
  """Serves static file."""
  filename = os.path.normpath(filename)
  root = filename.split('/')[0]
  if root not in STATIC_SERVING_ROOTS:
    flask.abort(404)

  filename = os.path.join(STATIC_DIR, filename)
  mime = mimetypes.guess_type(filename)[0]
  if not mime:
    mime = 'text/plain'

  if not os.path.isfile(filename):
    flask.abort(404)
  with open(filename, 'rb') as data:
    return flask.Response(data.read(), 200, mimetype=mime)


def format_api_response(status_code, data):
  response = flask.Response(
      '%s%s' % (API_RESPONSE_PREFIX, json.dumps(data, sort_keys=True)),
      status_code, {
          'Content-Type': API_RESPONSE_CONTENT_TYPE,
      })
  set_no_cache_headers(response.headers)
  return response


def get_server_info():
  return {
      'lang': 'PY37',
      'time': str(datetime.datetime.now()),
      'software': os.environ.get('GAE_RUNTIME', 'UNKNOWN_RUNTIME'),
      'version': os.environ.get('GAE_VERSION', 'UNKNOWN_VERSION'),
  }


def abort_invalid_attribute(name, message):
  flask.abort(format_api_response(
      400, dao.InvalidFieldValueError(name, message).to_json_serializable()))


def abort_user_error(message):
  flask.abort(format_api_response(
      400, dao.BusinessRuleError(message).to_json_serializable()))


app = flask.Flask(__name__)


@app.after_request
def set_cors_policy(response):
  set_cors_headers(response.headers)
  return response


@app.route('/', methods=['GET'])
def static_root():
  return flask.redirect('/index.html', code=301)


@app.route('/<path:filename>', methods=['GET'])
def static_get(filename):
  response = serve_static_file(filename)
  set_no_cache_headers(response.headers)
  return response


def api_v1_ping():
  """Handles ping()."""
  return format_api_response(200, {
      'server': get_server_info(),
  })


class ETag(object):
  """ETag.

  We use "etag" as a generic mechanism to manage concurrent from multiple
  clients; client will receive "etag" from server and must send it back for any
  mutattion operation; server can encode into "etag" enough data to properly
  order mutations or detect what objects have changed; how storage issues
  "etags" varies; sometimes you may choose not to use them and let mutations
  override each other; sometimes you can use "version" attribute that you
  monotonically increment; timestamp can also be used as long as server issues
  it to prevent clock skews; most project will not use "etags"; we do provide
  support and example here so you know how to do it if you have to
  """
  ETAG_NAME_SETTINGS = 'settings_etag'

  @classmethod
  def from_request(cls, name):
    data = flask.request.form
    value = data.get(name, None)
    if value is None:
      abort_user_error('Missing required parameter "%s".' % name)
    return value


def get_roles_for(user):
  """Checks if user can access the system, and in which specific roles."""
  email = user.get('email', '')
  good_status = 'Your account is in good standing.'

  # admin users
  if email in ADMIN_EMAILS:
    return ROLES_ALL, good_status

  # whitelisted users
  if WHITELISTED_EMAILS and (email in WHITELISTED_EMAILS):
    return [ROLE_USER], good_status

  # whitelisted domains users
  domain = email.split('@')[1]
  if WHITELISTED_DOMAINS and (domain in WHITELISTED_DOMAINS):
    return [ROLE_USER], good_status

  # if not limited to any domains
  if not WHITELISTED_DOMAINS:
    return [ROLE_USER], good_status

  # otherwise access denied
  bad_status = 'Your account doesn\'t have rights to access this system.'
  return [], bad_status


def get_user_for_request(request):
  """Determines user for the request."""
  user = None
  if request.headers.get(oauth2_utils.HTTP_HEADER_NAME):
    verified_claims = oauth2_utils.verify_access_token_from_request(request)
    user = oauth2_utils.get_user_for_access_token(verified_claims)
    scope = OAUTH_UID_NS
  elif request.headers.get(firebase_utils.HTTP_HEADER_NAME):
    verified_claims = firebase_utils.verify_id_token_from_request(request)
    user = firebase_utils.get_user_for(verified_claims)
    scope = FIREBASE_UID_NS
  if not user:
    return None

  assert user['uid']
  user['uid'] = '%s/%s' % (scope, user['uid'])
  user['uid_scope'] = scope
  return user


def get_uid_for(user):
  uid = user['uid']
  assert uid
  return uid


def with_user(method):
  """Executed method with current user."""
  user = get_user_for_request(flask.request)
  if not user:
    return flask.Response('Unauthorized.', 401)
  roles, status = get_roles_for(user)

  result = None
  if method:
    if not roles:
      return flask.Response('Access denied.', 403)
    try:
      result = method(user, roles)
    except HTTPException:              # these are flask.abort; ok
      raise
    except dao.BusinessRuleError:      # these are our dao.* exceptions; ok
      raise
    except Exception:  # pylint: disable=broad-except
      logging.error('Exception:\n%s', traceback.format_exc())
      flask.abort(format_api_response(
          500,
          dao.BusinessRuleError(
              'Internal server error. Please try again later.'
          ).to_json_serializable()))

  member = dao.Members().get_or_create_member(get_uid_for(user))

  user['roles'] = roles
  user['settings'] = json.loads(member.data)
  user['slug'] = member.slug
  user['status'] = status
  user[ETag.ETAG_NAME_SETTINGS] = member.version

  response = {
      'app': {
          'schema': APP_SCHEMA,
      },
      'user': user,
      'server': get_server_info(),
  }

  if result or result == []:  # pylint: disable=g-explicit-bool-comparison
    response['result'] = result

  return format_api_response(200, response)


def validate_profile(profile):
  # not strictly nessesary, but we will require few profile attributes
  # to be set just to show error handling end to end from client to server
  if not profile.get('title'):
    abort_invalid_attribute('title', 'Title is required.')
  if not profile.get('location'):
    abort_invalid_attribute('location', 'Location is required.')
  if not profile.get('about'):
    abort_invalid_attribute('about', 'Information about you is required.')


def api_v1_whoami():
  """Queries capabilities of user specified by id_token in HTTP header."""
  return with_user(None)


def api_v1_registration():
  """Register current user into the program."""

  def action(user, unused_roles):
    members = dao.Members()

    # load member current settings
    member_uid = get_uid_for(user)
    member = members.get_or_create_member(member_uid)
    version = ETag.from_request(ETag.ETAG_NAME_SETTINGS)
    if not version:
      version = member.version

    # update registration portion of settings
    settings = json.loads(member.data)
    settings['registered'] = True
    settings['registration'] = {
        'displayName': user['displayName'],
        'photoURL': user['photoURL'],
        'email': user['email'],
        'created_on': dao.datetime_to_str(dao.timezone_aware_now()),
    }

    # save to storage
    try:
      members.update(member_uid, json.dumps(settings), version=version)
    except dao.ETagError as error:
      flask.abort(format_api_response(400, error.to_json_serializable()))

  return with_user(action)


def api_v1_profile():
  """Updates current user profile."""

  # load and validate new settings from request
  json_string = flask.request.form.get('profile', None)
  if not json_string:
    abort_user_error('Missing required parameter "profile".')
  try:
    profile = json.loads(json_string)
  except:  # pylint: disable=bare-except
    abort_user_error('Provided "profile" is not a valid JSON.')
  validate_profile(profile)

  def action(user, unused_roles):
    members = dao.Members()

    # load member current settings
    member_uid = get_uid_for(user)
    member = members.get_or_create_member(member_uid)
    version = ETag.from_request(ETag.ETAG_NAME_SETTINGS)
    if not version:
      version = member.version

    # update profile portion of settings
    settings = json.loads(member.data)
    settings['profile'] = profile

    # save to storage
    try:
      members.update(member_uid, json.dumps(settings), version=version)
    except dao.ETagError as error:
      flask.abort(format_api_response(400, error.to_json_serializable()))

  return with_user(action)


def api_v1_members():
  """Lists members."""

  def action(unused_user, roles):
    members = dao.Members()
    is_admin = ROLE_ADMIN in roles
    results = []

    # add registered members
    for member in members.query_members():
      if len(results) > MAX_MEMBERS_IN_LIST:
        break

      settings = json.loads(member.data)
      profile = settings.get('profile', None)
      registration = settings.get('registration', None)

      # check rights
      is_public = profile and (
          profile.get('visibility') == PROFILE_VISIBILITY_PUBLIC)
      if not(is_public or is_admin):
        continue

      # add projection to output
      results.append({
          'slug': member.slug,
          'profile': profile,
          'registration': registration,
      })

    return results

  return with_user(action)


def api_v1_posts_get():
  """Lists all posts."""

  def action(user, unused_roles):
    posts = dao.Posts()
    member_uid = get_uid_for(user)
    return dao.posts_query_to_list(
        member_uid, posts.query_posts(), client=posts.client)

  return with_user(action)


def api_v1_member_posts():
  """Lists all posts of current user."""

  def action(user, unused_roles):
    posts = dao.Posts()
    member_uid = get_uid_for(user)
    return dao.posts_query_to_list(
        member_uid, posts.query_member_posts(member_uid), client=posts.client)

  return with_user(action)


def api_v1_posts_insert():
  """Records new user post."""

  json_string = flask.request.form.get('post', None)
  if not json_string:
    abort_user_error('Missing required parameter "post".')

  def action(user, unused_roles):
    member_uid = get_uid_for(user)
    dao.Posts().insert_post(member_uid, json_string)

  return with_user(action)


def api_v1_posts_post():
  """Marks post deleted new user post."""

  json_string = flask.request.form.get('post', None)
  if not json_string:
    abort_user_error('Missing required parameter "post".')
  post = json.loads(json_string)

  post_uid = post.get('uid')
  if not post_uid:
    abort_user_error('Missing required parameter "post.uid".')

  def action(user, unused_roles):
    member_uid = get_uid_for(user)
    dao.Posts().mark_post_deleted(member_uid, post_uid)

  return with_user(action)


def api_v1_votes_put():
  """Records user vote."""

  # extract and validate post data
  json_string = flask.request.form.get('vote', None)
  if not json_string:
    abort_user_error('Missing required parameter "vote".')
  vote = json.loads(json_string)
  post_uid = vote.get('uid')
  if not post_uid:
    abort_user_error('Missing required parameter "vote.uid".')
  value = vote.get('value')
  if not value:
    abort_user_error('Missing required parameter "vote.value".')

  def action(user, unused_roles):
    votes = dao.Votes()
    member_uid = get_uid_for(user)

    # record vote
    post, vote = votes.insert_vote(member_uid, post_uid, value)
    result = dao.posts_query_to_list(member_uid, [post], fill_votes=False,
                                     client=votes.client)[0]

    # update my_vote_value directly; it may not get picked up
    # due to indexed query being out of date
    result['my_vote_value'] = vote.value
    return result

  return with_user(action)


# all HTTP routes are registered in one place here
ALL_ROUTES = [
    ('/api/rest/v1/ping', api_v1_ping, ['GET']),
    ('/api/rest/v1/whoami', api_v1_whoami, ['GET']),
    ('/api/rest/v1/registration', api_v1_registration, ['PUT']),
    ('/api/rest/v1/profile', api_v1_profile, ['POST']),
    ('/api/rest/v1/members', api_v1_members, ['GET']),
    ('/api/rest/v1/member/posts', api_v1_member_posts, ['GET']),
    ('/api/rest/v1/posts', api_v1_posts_get, ['GET']),
    ('/api/rest/v1/posts', api_v1_posts_insert, ['PUT']),
    ('/api/rest/v1/posts', api_v1_posts_post, ['POST']),
    ('/api/rest/v1/votes', api_v1_votes_put, ['PUT']),
]


# add routes to Flask
for path, view_func, methods in ALL_ROUTES:
  app.add_url_rule(path, view_func=view_func, methods=methods)


if __name__ == '__main__':
  # This is used when running locally only. When deploying to Google App
  # Engine, a webserver process such as Gunicorn will serve the app. This
  # can be configured by adding an `entrypoint` to app.yaml.
  app.run(host='0.0.0.0', port=8080, debug=True)
