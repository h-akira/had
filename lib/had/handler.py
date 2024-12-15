import jwt
from jwt import PyJWKClient
from datetime import datetime
import urllib.parse
from http.cookies import SimpleCookie
import logging

class RequestClass:
  def __init__(self, event, context):
    self.logger = logging.getLogger()
    self.logger.setLevel(logging.INFO)
    self.error = None
    self.event = event
    self.context = context
    self._set_method()
    self._set_parsed_body(self.method)
    self._set_auth()  # self.authとself.username
  def get_cookies_to_refresh(self):
    cookie = SimpleCookie()
    cookie['id_token'] = self.id_token
    cookie['id_token']['httponly'] = True
    cookie['id_token']['secure'] = True
    cookie['id_token']['path'] = '/'
    # アクセストークンをCookieにセット
    cookie['access_token'] = self.access_token
    cookie['access_token']['httponly'] = True  # クライアント側のJavaScriptからアクセスできないように設定
    cookie['access_token']['secure'] = True  # HTTPS接続でのみ送信されるように設定
    cookie['access_token']['path'] = '/'  # クッキーが有効なパスを指定
    # # リフレッシュCookieにセット
    # cookie['refresh_token'] = self.refresh_token
    # cookie['refresh_token']['httponly'] = True  # クライアント側のJavaScriptからアクセスできないように設定
    # cookie['refresh_token']['secure'] = True  # HTTPS接続でのみ送信されるように設定
    # cookie['refresh_token']['path'] = '/'  # クッキーが有効なパスを指定
    return [
      cookie['id_token'].OutputString(),
      cookie['access_token'].OutputString()
      # cookie['refresh_token'].OutputString()
    ]
  def _set_parsed_body(self, method):
    if method == "POST":
      self.body = urllib.parse.parse_qs(self.event['body'])
      for key, value in self.body.items():
        if len(value) == 1:
          self.body[key] = value[0]
    else:
      self.body = None
  def _set_method(self):
    self.method = self.event['requestContext']["httpMethod"]
  def _set_auth(self):
    from project import settings
    self.id_token = None
    self.access_token = None
    self.refresh_token = None
    self.refresh = False
    cookies = self.event['headers'].get('Cookie', '')
    if not cookies:
      self.auth = False
      self.username = None
      return None
    for cookie in cookies.split(';'):
      name, value = cookie.strip().split('=')
      if name == 'id_token':
        self.id_token = value
      elif name == 'refresh_token':
        self.refresh_token = value
      elif name == 'access_token':
        self.access_token = value
      if self.id_token is not None and self.refresh_token is not None and self.access_token is not None:
        break
    else:
      self.auth = False
      self.username = None
      return None
    jwk_client = PyJWKClient(
      f'https://cognito-idp.{settings.AWS["region"]}.amazonaws.com/{settings.AWS["cognito"]["userPoolID"]}/.well-known/jwks.json'
    )
    signing_key = jwk_client.get_signing_key_from_jwt(self.id_token)
    try:
      self.decoded_token = jwt.decode(
        self.id_token,
        signing_key.key,
        algorithms=["RS256"],
        audience=settings.AWS["cognito"]["clientID"],
        issuer=f'https://cognito-idp.{settings.AWS["region"]}.amazonaws.com/{settings.AWS["cognito"]["userPoolID"]}'
      )
      self.auth = True
      self.username = self.decoded_token.get('cognito:username', None)
    except jwt.ExpiredSignatureError:
      import boto3
      client = boto3.client('cognito-idp')
      try:
        response = client.initiate_auth(
          ClientId=settings.AWS["cognito"]["clientID"],
          AuthFlow='REFRESH_TOKEN_AUTH',
          AuthParameters={
            'REFRESH_TOKEN': self.refresh_token
          }
        )
        self.id_token = response['AuthenticationResult']['IdToken']
        self.access_token = response['AuthenticationResult']['AccessToken']
        # self.refresh_token = response['AuthenticationResult']['RefreshToken']
        self.refresh = True
        signing_key = jwk_client.get_signing_key_from_jwt(self.id_token)
        self.decoded_token = jwt.decode(
          self.id_token,
          signing_key.key,
          algorithms=["RS256"],
          audience=settings.AWS["cognito"]["clientID"],
          issuer=f'https://cognito-idp.{settings.AWS["region"]}.amazonaws.com/{settings.AWS["cognito"]["userPoolID"]}'
        )
        self.auth = True
        self.username = self.decoded_token.get('cognito:username', None)
      except:
        # import traceback
        self.auth = False
        self.username = None
        # self.error = "Expire and failed to refresh: " + traceback.format_exc()
    except jwt.InvalidTokenError:
      self.auth = False
      self.username = None
      # self.error = "InvalidToken"
    

