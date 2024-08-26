#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created: 2024-08-06 00:17:21

import sys
import os
import json
import csv
import shutil
import importlib

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

def parse_args():
  import argparse
  parser = argparse.ArgumentParser(description="""\

""", formatter_class = argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument("--version", action="version", version='%(prog)s 0.0.1')
  parser.add_argument("-o", "--output", metavar="output-file", default="output", help="output file")
  parser.add_argument("-a", "--all", action="store_true", help="更新の有無に関係なくすべてのhandlerを生成")
  # parser.add_argument("-s", "--source", action="store_true", help="ソースコードを残す")
  # parser.add_argument("-", "--", action="store_true", help="")
  parser.add_argument("file", metavar="settings-json-file", help="settings.json")
  options = parser.parse_args()
  # if not os.path.isfile(options.file): 
    # raise Exception("The input file does not exist.") 
  return options

def read_settings_json():
  with open(os.path.join(os.path.dirname(__file__), "settings.json"), "r") as f:
    settings_json = json.load(f)
  return settings_json

def main():
  options = parse_args()
  with open(options.file, "r") as f:
    settings_json = json.load(f)
  CURRENT_DIR = os.path.dirname(options.file)
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





if __name__ == '__main__':
  main()
