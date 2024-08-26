#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created: 2024-08-26 21:44:11

import json
import subprocess
import os
import sys

def parse_args():
  import argparse
  parser = argparse.ArgumentParser(description="""\

""", formatter_class = argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument("--version", action="version", version='%(prog)s 0.0.1')
  # parser.add_argument("-o", "--output", metavar="output-file", default="output", help="output file")
  # parser.add_argument("-", "--", action="store_true", help="")
  parser.add_argument("file", metavar="settings-json-file", help="settings.json")
  options = parser.parse_args()
  if not os.path.isfile(options.file): 
    raise Exception("The input file does not exist.") 
  return options

def main():
  options = parse_args()
  with open(options.file, "r") as f:
    settings_json = json.load(f)
  CURRENT_DIR = os.path.dirname(options.file)
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

if __name__ == '__main__':
  main()
