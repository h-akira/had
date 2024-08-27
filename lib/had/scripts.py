import sys
import os
import json
import shutil
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
  try:
    if pathParameters:
      return {function}(request, **pathParameters)
    else:
      return {function}(request)
  except Exception as e:
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
      print(f"Remove directory: {os.path.join(CURRENT_DIR, settings_json['handlers']['directory'], APP['name'], EXIST_HANDLER)}")
      shutil.rmtree(os.path.join(CURRENT_DIR, settings_json["handlers"]["directory"], APP["name"], EXIST_HANDLER))
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

if __name__ == '__main__':
  main()
