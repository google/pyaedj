"""Helper classes for working with Firebase/OAuth 2."""


__author__ = 'Pavel Simakov (psimakov@google.com)'


import json
import logging
import os
import urllib
import firebase_admin
from firebase_admin import auth as firebase_auth
from google.auth.transport import requests
from google.oauth2 import id_token as oauth2_id_token


IS_GAE_PROD = os.environ.get('GAE_ENV', 'UNKNOWN_ENV') == 'standard'


class FirebaseAppUtils(object):
  """Helper class for Firebase Auth."""

  HTTP_HEADER_NAME = 'A120-PWA-Authorization'
  HTTP_HEADER_VALUE_PREFIIX = 'Firebase idToken '

  def __init__(self, project_id):
    self.app = None
    self.project_id = project_id

  def _get_app(self):
    if not self.app:
      self.app = firebase_admin.initialize_app(options={
          'projectId': self.project_id,
      })
    return self.app

  def verify_firebase_id_token(self, id_token):
    if not id_token:
      return None
    try:
      return firebase_auth.verify_id_token(
          id_token, app=self._get_app(), check_revoked=IS_GAE_PROD)
    except ValueError as e:
      logging.error('Failed to decode Firebase id_token: %s', e)
      return None

  def get_firebase_id_token_from_request(self, request):
    header = request.headers.get(self.HTTP_HEADER_NAME, '')
    parts = header.split(self.HTTP_HEADER_VALUE_PREFIIX)
    if len(parts) == 2:
      return parts[1]
    return None

  def verify_id_token_from_request(self, request):
    return self.verify_firebase_id_token(
        self.get_firebase_id_token_from_request(request))

  def check_sign_in_provider(self, verified_claims):
    """Checks sign_in_provider of verified claims."""
    if verified_claims:
      if (
          verified_claims.get('firebase', {}).get(
              'sign_in_provider') == 'google.com'
      ) and (
          verified_claims.get('firebase', {}).get(
              'identities', {}).get('google.com')
      ) and (
          verified_claims.get('email_verified')
      ):
        return True
    return False

  def get_user_for(self, verified_claims):
    """Looks up user details and user roles from id_token."""
    if self.check_sign_in_provider(verified_claims):
      return {
          'uid': verified_claims.get('uid'),
          'focus_gaia_id': verified_claims.get('firebase', {}).get(
              'identities', {}).get('google.com'),
          'email': verified_claims.get('email'),
          'displayName': verified_claims.get('name'),
          'photoURL': verified_claims.get('picture'),
      }
    return None


class OAuth2AppUtils(object):
  """Helper class for OAuth 2 Auth."""

  HTTP_HEADER_NAME = 'Authorization'
  HTTP_HEADER_VALUE_PREFIIX = 'Bearer '

  def __init__(self, project_id):
    self.project_id = project_id

  def verify_id_token(self, token):
    claims = oauth2_id_token.verify_oauth2_token(
        token, requests.Request(), self.project_id)
    if claims['iss'] not in [
        'accounts.google.com', 'https://accounts.google.com']:
      raise ValueError('Wrong issuer.')
    return claims

  def get_user_for_id_token(self, claims):
    return {
        'uid': claims['sub'],
        'focus_gaia_id': None,
        'email': claims['email'],
        'displayName': claims['name'],
        'photoURL': claims['picture'],
    }

  def get_oauth2_access_token_from_request(self, request):
    header = request.headers.get(self.HTTP_HEADER_NAME, '')
    parts = header.split(self.HTTP_HEADER_VALUE_PREFIIX)
    if len(parts) == 2:
      return parts[1]
    return None

  def verify_access_token_from_request(self, request):
    """Fetches user based upon access_token."""
    conn = urllib.request.urlopen(
        'https://www.googleapis.com/plus/v1/people/me'
        '?%s' % urllib.parse.urlencode({
            'access_token': self.get_oauth2_access_token_from_request(request)
        }))
    return json.loads(conn.read().decode('utf-8'))

  def get_user_for_access_token(self, claims):
    return {
        'uid': claims.get('id'),
        'focus_gaia_id': None,
        'email': claims.get('emails', [{}])[0].get('value'),
        'displayName': claims.get('displayName'),
        'photoURL': claims.get('image', {}).get('url'),
    }
