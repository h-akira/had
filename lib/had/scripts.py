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
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
  try:
    request = RequestClass(event, context)
    login_required = {login_required}
    if login_required:
      if not request.auth:
        return redirect(settings.LOGIN_URL)
  except Exception as e:
    logger.exception('Raise Exception: %s', e)
    return error_render(None, traceback.format_exc())
  if request.error:
    return error_render(None, request.error)
  try:
    pathParameters = event["pathParameters"]
  except KeyError:
    pathParameters = False
  try:
    if pathParameters:
      return {function}(request, **pathParameters)
    else:
      return {function}(request)
  except Exception as e:
    logger.exception('Raise Exception: %s', e)
    return error_render(request, traceback.format_exc())"""

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

def handlers2s3(settings_json_path, version:str):
  with open(settings_json_path, "r") as f:
    settings_json = json.load(f)
  CURRENT_DIR = os.path.dirname(settings_json_path)
  # if versions is None:
  #   with open(os.path.join(CURRENT_DIR, settings_json["latest_version"]), "r") as f:
  #     versions = json.load(f)
  HANDLERS_DIR = os.path.join(CURRENT_DIR, settings_json['handlers']['directory'])
  S3_BUCKET = settings_json['S3']['bucket']
  S3_KEY = settings_json['S3']['key']
  # 新しいバージョンを設定
  # if versions["handlers"].__class__ is int:
  #   NEW_VERSION = versions['handlers'] + 1
  #   versions['handlers'] = NEW_VERSION
  #   subprocess.run(
  #     ['aws', 's3', 'cp', HANDLERS_DIR, f's3://{S3_BUCKET}/{S3_KEY}/handlers/v{NEW_VERSION:04d}', '--recursive']
  #   )
  #   with open(os.path.join(CURRENT_DIR, settings_json["latest_version"]), "w") as f:
  #     json.dump(versions, f, indent=2)
  # else:
  # NEW_VERSION = versions['handlers']
  subprocess.run(
    ['aws', 's3', 'cp', HANDLERS_DIR, f's3://{S3_BUCKET}/{S3_KEY}/handlers/{version}', '--recursive']
  )
  # バージョンを更新
  _latest_version_overwrite(os.path.join(CURRENT_DIR, settings_json["latest_version"]), handler=version)
  # aws s3 cp コマンドを実行
  print("Uploaded to S3.")

def upload_layer(S3_BUCKET, S3_KEY, version, DIR, name):
  if os.path.exists(os.path.join(DIR, f'{name}.zip')):
    os.remove(os.path.join(DIR, f'{name}.zip'))
  subprocess.run(['zip', '-r', f'{name}.zip', '.'], cwd=DIR)
  # if NEW_VERSION.__class__ is int:
  #   subprocess.run(
  #     ['aws', 's3', 'cp', os.path.join(DIR, f"{name}.zip"), 
  #      f's3://{S3_BUCKET}/{S3_KEY}/layers/{name}/v{NEW_VERSION:04d}.zip']
  #   )
  # else:
  subprocess.run(
    ['aws', 's3', 'cp', os.path.join(DIR, f"{name}.zip"), 
     f's3://{S3_BUCKET}/{S3_KEY}/layers/{name}/{version}.zip']
  )
  print(f"Uploaded {name} to S3.")

def layers2s3(settings_json_path, version, project_upload=False, external_upload=False):
  with open(settings_json_path, "r") as f:
    settings_json = json.load(f)
  CURRENT_DIR = os.path.dirname(settings_json_path)
  # if versions is None:
  #   with open(os.path.join(CURRENT_DIR, settings_json["latest_version"]), "r") as f:
  #     versions = json.load(f)
  S3_BUCKET = settings_json['S3']['bucket']
  S3_KEY = settings_json['S3']['key']
  if external_upload:
    DIR = os.path.join(CURRENT_DIR, settings_json['pip']['layer']['directory'])
    # if versions["external"].__class__ is int:
    #   NEW_VERSION = versions['external'] + 1
    # else:
    #   NEW_VERSION = versions['external']
    upload_layer(S3_BUCKET, S3_KEY, version, DIR, 'external')
    # versions["external"] = NEW_VERSION
    # if versions["external"].__class__ is int:
    #   with open(os.path.join(CURRENT_DIR, settings_json["latest_version"]), "w") as f:
    #     json.dump(versions, f, indent=2)
    _latest_version_overwrite(os.path.join(CURRENT_DIR, settings_json["latest_version"]), external=version)
  if project_upload:
    DIR = os.path.join(CURRENT_DIR, settings_json['layer']['directory'])
    # if versions["project"].__class__ is int:
    #   NEW_VERSION = versions['project'] + 1
    # else:
    #   NEW_VERSION = versions['project']
    upload_layer(S3_BUCKET, S3_KEY, version, DIR, 'project')
    # versions["project"] = NEW_VERSION
    # if versions["project"].__class__ is int:
    #   with open(os.path.join(CURRENT_DIR, settings_json["latest_version"]), "w") as f:
    #     json.dump(versions, f, indent=2)
    _latest_version_overwrite(os.path.join(CURRENT_DIR, settings_json["latest_version"]), project=version)

def cfn_create(settings_json_path, wait=True):
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
  if wait:
    print("Waiting for CloudFormation Stack create.")
    subprocess.run(
      ['aws', 'cloudformation', 'wait', 'stack-create-complete', 
       '--stack-name', settings_json['CloudFormation']['stack_name'],
      ]
    )
    print("Finished CloudFormation Stack create.")

def cfn_update(settings_json_path, wait=True):
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
  if wait:
    print("Waiting for CloudFormation Stack update.")
    subprocess.run(
      ['aws', 'cloudformation', 'wait', 'stack-update-complete', '--stack-name', settings_json['CloudFormation']['stack_name']]
    )
    print("Finished CloudFormation Stack update.")

def cfn_delete(settings_json_path, wait=True):
  if not input("Are you sure you want to delete the stack? (y/other): ") == "y":
    print("Canceled.")
    return None
  with open(settings_json_path, "r") as f:
    settings_json = json.load(f)
  # スタックの削除
  subprocess.run(
    ['aws', 'cloudformation', 'delete-stack', '--stack-name', settings_json['CloudFormation']['stack_name']]
  )
  if wait:
    print("Waiting for CloudFormation Stack delete.")
    subprocess.run(
      ['aws', 'cloudformation', 'wait', 'stack-delete-complete', '--stack-name', settings_json['CloudFormation']['stack_name']]
    )
    print("Finished CloudFormation Stack delete.")

def cfn_exists(settings_json_path, print_message=True):
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
    if print_message:
      print("The stack exists.")
    return True
  except subprocess.CalledProcessError:
    if "does not exist" in e.stderr.decode():
      # raise Exception("The stack does not exist.")
      if print_message:
        print("The stack does not exist.")
      return False
    else:
      raise Exception(f"An error occurred: {e.stderr.decode()}")

def _upload_yaml_to_s3(local_file, settings_json):
  s3_key = os.path.join(settings_json['S3']['key'],"CloudFormation", f"{datetime.datetime.now(ZoneInfo('Asia/Tokyo')).strftime('%Y%m%d%H%M%S')}.yaml")
  subprocess.run(
    ['aws', 's3', 'cp', local_file, f's3://{settings_json["S3"]["bucket"]}/{s3_key}']
  )
  s3_url = f'https://{settings_json["S3"]["bucket"]}.s3.{settings_json["region"]}.amazonaws.com/{s3_key}'
  return s3_url

def _version_read(later_version_json_path):
  with open(later_version_json_path, "r") as f:
    versions = json.load(f)
  return versions

def _latest_version_overwrite(latest_version_json_path, versions=None, handler=None, project=None, external=None):
  if versions is None:
    if os.path.exists(later_version_json_path):
      with open(later_version_json_path, "r") as f:
        versions = json.load(f)
    else:
      versions = {
        "handlers": None,
        "project": None,
        "external": None
      }
    if handler is not None:
      versions['handlers'] = handler
    if project is not None:
      versions['project'] = project
    if external is not None:
      versions['external'] = external
  else:
    if versions.__class__ is not dict:
      raise ValueError("versions must be dict.")
    if handler is not None or project is not None or external is not None:
      raise Exception("If versions is not None, handler, project, external must be None.")
  with open(later_version_json_path, "w") as f:
    json.dump(versions, f, indent=2)




