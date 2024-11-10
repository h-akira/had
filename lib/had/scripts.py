import sys
import os
import json
import shutil
import datetime
from zoneinfo import ZoneInfo
import importlib
import subprocess

CODE_TEMPLATE = """\
import sys
import os
from project import settings
from had.handler import RequestClass
from {app}.views import {function}
from had.shourtcuts import redirect, error_render
import traceback

def lambda_handler(event, context):
  try:
    request = RequestClass(event, context)
    login_required = {login_required}
    if login_required:
      if not request.auth:
        return redirect(settings.LOGIN_URL)
  except Exception as e:
    return error_render(None, traceback.format_exc())
  if request.error:
    return error_render(None, request.error)
  try:
    pathParameters = event["pathParameters"]
  except KeyError:
    pathParameters = False
  if settings.DEBUG:
    try:
      if pathParameters:
        return {function}(request, **pathParameters)
      else:
        return {function}(request)
    except Exception as e:
      return error_render(request, traceback.format_exc())
  else:
    if pathParameters:
      return {function}(request, **pathParameters)
    else:
      return {function}(request)"""

def gen_handlers(settings_json_path):
  with open(settings_json_path, "r") as f:
    settings_json = json.load(f)
  CURRENT_DIR = os.path.dirname(settings_json_path)
  sys.path.append(os.path.join(CURRENT_DIR,settings_json["layer"]["directory"], settings_json["layer"]["path"]))
  sys.path.append(os.path.join(CURRENT_DIR,settings_json["pip"]["layer"]["directory"], settings_json["pip"]["layer"]["path"]))
  from project import settings
  if not os.path.isdir(os.path.join(CURRENT_DIR, settings_json["handlers"]["directory"])):
    os.makedirs(os.path.join(CURRENT_DIR, settings_json["handlers"]["directory"]))
  EXIST_APPS = os.listdir(os.path.join(CURRENT_DIR, settings_json["handlers"]["directory"]))
  # ディレクトリかどうか確認
  for EXIST_APP in EXIST_APPS:
    if not os.path.isdir(os.path.join(CURRENT_DIR, settings_json["handlers"]["directory"], EXIST_APP)):
      print(f"Error: {os.path.join(CURRENT_DIR, settings.HANDLER_DIR, APP)} is not a directory.")
      raise Exception
  for APP in settings.APPS:
    if APP["name"] in EXIST_APPS:
      EXIST_APPS.remove(APP["name"])
    else:
      print(f'Create directory: {os.path.join(CURRENT_DIR, settings_json["handlers"]["directory"], APP["name"])}')
      os.makedirs(os.path.join(CURRENT_DIR, settings_json["handlers"]["directory"], APP["name"]))
    urls = importlib.import_module(f"{APP['name']}.urls")
    EXIST_HANDLERS = os.listdir(os.path.join(CURRENT_DIR, settings_json["handlers"]["directory"], APP["name"]))
    for EXIST_HANDLER in EXIST_HANDLERS:
      if EXIST_HANDLER[-4:] != ".zip":
        print(f"Error: {os.path.join(CURRENT_DIR, settings_json['handlers']['directory'], APP['name'], EXIST_HANDLER)} is not a zip file.")
        raise Exception
    for urlpattern in urls.urlpatterns:
      if urlpattern["integration"].lower() != "lambda":
        continue
      handler_dir = os.path.join(CURRENT_DIR, settings_json["handlers"]["directory"], APP["name"], urlpattern['name'])
      handler_path = os.path.join(handler_dir, "lambda_function.py")
      if urlpattern["name"]+".zip" in EXIST_HANDLERS:
        EXIST_HANDLERS.remove(urlpattern["name"]+".zip")
      os.makedirs(handler_dir)
      code = CODE_TEMPLATE.format(
        app=APP["name"], 
        function=urlpattern["function"].__name__,
        login_required=urlpattern["login_required"]
      )
      with open(handler_path, "w") as f:
        f.write(code)
      # zip
      shutil.make_archive(handler_dir, 'zip', handler_dir)
      shutil.rmtree(handler_dir)
    # print(EXIST_HANDLERS)
    for EXIST_HANDLER in EXIST_HANDLERS:
      print(f"Remove file: {os.path.join(CURRENT_DIR, settings_json['handlers']['directory'], APP['name'], EXIST_HANDLER)}")
      os.remove(os.path.join(CURRENT_DIR, settings_json["handlers"]["directory"], APP["name"], EXIST_HANDLER))
  for EXIST_APP in EXIST_APPS:
    print(f"Remove directory: {os.path.join(CURRENT_DIR, settings_json['handlers']['directory'], EXIST_APP)}")
    shutil.rmtree(os.path.join(CURRENT_DIR, settings_json["handlers"]["directory"], EXIST_APP))
  print("Complete!")

def handlers2s3(settings_json_path):
  with open(settings_json_path, "r") as f:
    settings_json = json.load(f)
  CURRENT_DIR = os.path.dirname(settings_json_path)
  with open(os.path.join(CURRENT_DIR, settings_json["latest_version"]), "r") as f:
    versions = json.load(f)
  HANDLERS_DIR = os.path.join(CURRENT_DIR, settings_json['handlers']['directory'])
  S3_BUCKET = settings_json['S3']['bucket']
  S3_KEY = settings_json['S3']['key']
  # 新しいバージョンを設定
  NEW_VERSION = versions['handlers'] + 1
  # aws s3 cp コマンドを実行
  subprocess.run(
    ['aws', 's3', 'cp', HANDLERS_DIR, f's3://{S3_BUCKET}/{S3_KEY}/handlers/v{NEW_VERSION:04d}', '--recursive']
  )
  print("Uploaded to S3.")
  versions['handlers'] = NEW_VERSION
  with open(os.path.join(CURRENT_DIR, settings_json["latest_version"]), "w") as f:
    json.dump(versions, f, indent=2)

def upload_layer(S3_BUCKET, S3_KEY, NEW_VERSION, DIR, name):
  if os.path.exists(os.path.join(DIR, f'{name}.zip')):
    os.remove(os.path.join(DIR, f'{name}.zip'))
  subprocess.run(['zip', '-r', f'{name}.zip', '.'], cwd=DIR)
  subprocess.run(
    ['aws', 's3', 'cp', os.path.join(DIR, f"{name}.zip"), 
     f's3://{S3_BUCKET}/{S3_KEY}/layers/{name}/v{NEW_VERSION:04d}.zip']
  )
  print(f"Uploaded {name} to S3.")

def layers2s3(settings_json_path, project_upload=False, external_upload=False):
  with open(settings_json_path, "r") as f:
    settings_json = json.load(f)
  CURRENT_DIR = os.path.dirname(settings_json_path)
  with open(os.path.join(CURRENT_DIR, settings_json["latest_version"]), "r") as f:
    versions = json.load(f)
  S3_BUCKET = settings_json['S3']['bucket']
  S3_KEY = settings_json['S3']['key']
  if external_upload:
    DIR = os.path.join(CURRENT_DIR, settings_json['pip']['layer']['directory'])
    NEW_VERSION = versions['external'] + 1
    upload_layer(S3_BUCKET, S3_KEY, NEW_VERSION, DIR, 'external')
    versions["external"] = NEW_VERSION
    with open(os.path.join(CURRENT_DIR, settings_json["latest_version"]), "w") as f:
      json.dump(versions, f, indent=2)
  if project_upload:
    DIR = os.path.join(CURRENT_DIR, settings_json['layer']['directory'])
    NEW_VERSION = versions['project'] + 1
    upload_layer(S3_BUCKET, S3_KEY, NEW_VERSION, DIR, 'project')
    versions["project"] = NEW_VERSION
    with open(os.path.join(CURRENT_DIR, settings_json["latest_version"]), "w") as f:
      json.dump(versions, f, indent=2)

def cfn_create(settings_json_path):
  with open(settings_json_path, "r") as f:
    settings_json = json.load(f)
  CURRENT_DIR = os.path.dirname(settings_json_path)
  s3_url = _upload_yaml_to_s3(os.path.join(CURRENT_DIR, settings_json["CloudFormation"]["template"]), settings_json)
  # スタックの作成
  subprocess.run(
    ['aws', 'cloudformation', 'create-stack', '--stack-name', settings_json['CloudFormation']['stack_name'], 
     '--template-url', s3_url, 
     '--capabilities', 'CAPABILITY_NAMED_IAM']
  )
  print("Waiting for CloudFormation Stack create.")
  subprocess.run(
    ['aws', 'cloudformation', 'wait', 'stack-create-complete', 
     '--stack-name', settings_json['CloudFormation']['stack_name'],
    ]
  )
  print("Finished CloudFormation Stack create.")

def cfn_update(settings_json_path):
  with open(settings_json_path, "r") as f:
    settings_json = json.load(f)
  CURRENT_DIR = os.path.dirname(settings_json_path)
  s3_url = _upload_yaml_to_s3(os.path.join(CURRENT_DIR, settings_json["CloudFormation"]["template"]), settings_json)
  # スタックの更新
  subprocess.run(
    ['aws', 'cloudformation', 'update-stack', '--stack-name', settings_json['CloudFormation']['stack_name'], 
     '--template-url', s3_url, 
     '--capabilities', 'CAPABILITY_NAMED_IAM']
  )
  print("Waiting for CloudFormation Stack update.")
  subprocess.run(
    ['aws', 'cloudformation', 'wait', 'stack-update-complete', '--stack-name', settings_json['CloudFormation']['stack_name']]
  )
  print("Finished CloudFormation Stack update.")

def cfn_delete(settings_json_path):
  if not input("Are you sure you want to delete the stack? (y/other): ") == "y":
    print("Canceled.")
    return None
  with open(settings_json_path, "r") as f:
    settings_json = json.load(f)
  # スタックの削除
  subprocess.run(
    ['aws', 'cloudformation', 'delete-stack', '--stack-name', settings_json['CloudFormation']['stack_name']]
  )
  print("Waiting for CloudFormation Stack delete.")
  subprocess.run(
    ['aws', 'cloudformation', 'wait', 'stack-delete-complete', '--stack-name', settings_json['CloudFormation']['stack_name']]
  )
  print("Finished CloudFormation Stack delete.")

def cfn_exists(settings_json_path):
  with open(settings_json_path, "r") as f:
    settings_json = json.load(f)
  # スタックの存在確認
  try:
    subprocess.run(
      ['aws', 'cloudformation', 'describe-stacks', '--stack-name', settings_json['CloudFormation']['stack_name']],
      check=True,
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE
    )
    print("The stack exists.")
  except subprocess.CalledProcessError:
    if "does not exist" in e.stderr.decode():
      raise Exception("The stack does not exist.")
    else:
      raise Exception(f"An error occurred: {e.stderr.decode()}")

def _upload_yaml_to_s3(local_file, settings_json):
  s3_key = os.path.join(settings_json['S3']['key'],"CloudFormation", f"{datetime.datetime.now(ZoneInfo('Asia/Tokyo')).strftime('%Y%m%d%H%M%S')}.yaml")
  subprocess.run(
    ['aws', 's3', 'cp', local_file, f's3://{settings_json["S3"]["bucket"]}/{s3_key}']
  )
  s3_url = f'https://{settings_json["S3"]["bucket"]}.s3.{settings_json["region"]}.amazonaws.com/{s3_key}'
  return s3_url

if __name__ == '__main__':
  main()
