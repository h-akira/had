from had.shourtcuts import render, redirect, error_render
import urllib.parse
from datetime import datetime, timedelta
from http.cookies import SimpleCookie

def logout_redirect(request):
  import boto3
  from project import settings
  if request.auth:
    client = boto3.client('cognito-idp')
    response = client.global_sign_out(
      AccessToken = request.access_token
    )
    cookie = SimpleCookie()
    # id_token の削除
    cookie['id_token'] = ''
    cookie['id_token']['expires'] = (datetime.utcnow() - timedelta(days=1)).strftime("%a, %d-%b-%Y %H:%M:%S GMT")
    cookie['id_token']['path'] = '/'
    # access_token の削除
    cookie['access_token'] = ''
    cookie['access_token']['expires'] = (datetime.utcnow() - timedelta(days=1)).strftime("%a, %d-%b-%Y %H:%M:%S GMT")
    cookie['access_token']['path'] = '/'
    # refresh_token の削除
    cookie['refresh_token'] = ''
    cookie['refresh_token']['expires'] = (datetime.utcnow() - timedelta(days=1)).strftime("%a, %d-%b-%Y %H:%M:%S GMT")
    cookie['refresh_token']['path'] = '/'
    return redirect(
      settings.LOGOUT_REDIRECT_URL,
      set_cookie=[
        cookie['id_token'].OutputString(),
        cookie['access_token'].OutputString(),
        cookie['refresh_token'].OutputString()
      ]
    )
  else:
    return redirect(settings.LOGOUT_REDIRECT_URL)

def login_redirect(AuthParameters, AuthFlow="USER_PASSWORD_AUTH", return_error=False):
  import boto3
  import botocore
  from project import settings
  client = boto3.client('cognito-idp')
  try:
    response = client.initiate_auth(
      ClientId=settings.AWS["cognito"]["clientID"],
      AuthFlow=AuthFlow,
      AuthParameters=AuthParameters
    )
  except botocore.exceptions.ClientError as e:
    if e.response['Error']['Code'] == 'NotAuthorizedException':
      if return_error:
        return "NotAuthorizedException"
      else:
        return redirect(settings.LOGIN_URL)
    else:
      if return_error:
        return "UnknownError"
      else:
        return redirect(settings.LOGIN_URL)
  id_token = response['AuthenticationResult']['IdToken']
  access_token = response['AuthenticationResult']['AccessToken']
  refresh_token = response['AuthenticationResult']['RefreshToken']
  # try:
  # CookieにJWTトークンをセット
  cookie = SimpleCookie()
  cookie['id_token'] = id_token
  cookie['id_token']['httponly'] = True
  cookie['id_token']['secure'] = True
  cookie['id_token']['path'] = '/'
  # # アクセストークンをCookieにセット
  cookie['access_token'] = access_token
  cookie['access_token']['httponly'] = True  # クライアント側のJavaScriptからアクセスできないように設定
  cookie['access_token']['secure'] = True  # HTTPS接続でのみ送信されるように設定
  cookie['access_token']['path'] = '/'  # クッキーが有効なパスを指定
  # リフレッシュCookieにセット
  cookie['refresh_token'] = refresh_token
  cookie['refresh_token']['httponly'] = True  # クライアント側のJavaScriptからアクセスできないように設定
  cookie['refresh_token']['secure'] = True  # HTTPS接続でのみ送信されるように設定
  cookie['refresh_token']['path'] = '/'  # クッキーが有効なパスを指定
  return redirect(
    settings.LOGIN_REDIRECT_URL, 
    set_cookie=[
      cookie['id_token'].OutputString(),
      cookie['access_token'].OutputString(),
      cookie['refresh_token'].OutputString()
    ]
  )
