from had.shourtcuts import render, redirect, error_render
from project import settings
from had.authenticate import login_redirect, logout_redirect
import urllib.parse
from datetime import datetime, timedelta
from http.cookies import SimpleCookie
import traceback

def signup(request):
  import boto3
  import botocore
  # 参考
  # https://qiita.com/cloud-solution/items/3a770fb763efcf92a4a9
  if request.method == "POST":
    client = boto3.client('cognito-idp', region_name=settings.AWS["region"])
    username = request.body.get('username')
    email = request.body.get('email')
    passwd = request.body.get('passwd')
    try:
      # ユーザの作成
      response = client.admin_create_user(
        UserPoolId=settings.AWS["cognito"]["userPoolID"],
        Username=username,
        UserAttributes=[
          {
            'Name': 'email',
            'Value': email
          },   
          {
            'Name': 'email_verified',  # メールアドレスが確認済みかどうかを指定
            'Value': 'true'
          }
        ],
        # MessageAction='RESEND',
        # DesiredDeliveryMediums=['EMAIL']
        # メッセージ送信は抑止
        MessageAction='SUPPRESS',
        # 一時パスワードは未設定(次の処理で永続的なパスワードを)
        #TemporaryPassword = '',
      )
      # パスワードの設定
      # Permanentで永続的なパスワードに設定する。
      response = client.admin_set_user_password(
        UserPoolId=settings.AWS["cognito"]["userPoolID"],
        Username=username,
        Password=passwd,
        Permanent=True,
      )
      return redirect(settings.LOGIN_URL)
    except botocore.exceptions.ClientError as error:
      if error.response['Error']['Code'] == 'UsernameExistsException':
        return render(
          request, 'accounts/signup.html', context={"error":"ユーザ名が既に存在しています"}
        )
      elif error.response['Error']['Code'] == 'InvalidPasswordException':
        client.admin_delete_user(
            UserPoolId=settings.AWS["cognito"]["userPoolID"],
            Username=username
        )
        return render(
          request, 'accounts/signup.html', context={"error":"パスワードを複雑にしてください"}
        )
      else:
        return error_render(request, traceback.format_exc())
  else:
    return render(
      request, 'accounts/signup.html', context={"error":""}
    )

def login(request):
  if request.auth:
    return redirect(settings.LOGIN_REDIRECT_URL)
  else:
    if request.method == "POST":
      username = request.body.get('username')
      # email = request.body.get('email')
      passwd = request.body.get('passwd')
      AuthParameters = {
        'USERNAME': username,
        'PASSWORD': passwd
      }
      response = login_redirect(AuthParameters, return_error=True)
      if response.__class__ == str:
        return render(
          request, 
          'accounts/login.html', 
          context={"error":response}
        )
      else:
        return response
    else:
      return render(
        request, 
        'accounts/login.html', 
        context={"error":""}
      )

def logout(request):
  return logout_redirect(request)





