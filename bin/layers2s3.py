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
  parser.add_argument("-p", "--project", action="store_true", help="")
  parser.add_argument("-e", "--external", action="store_true", help="")
  parser.add_argument("file", metavar="settings-json-file", help="settings.json")
  options = parser.parse_args()
  if not options.project and not options.external:
    raise Exception("Please specify either -p or -e.")
  if not os.path.isfile(options.file): 
    raise Exception("The input file does not exist.") 
  return options

def upload(S3_BUCKET, S3_KEY, NEW_VERSION, DIR, name):
  if os.path.exists(os.path.join(DIR, f'{name}.zip')):
    os.remove(os.path.join(DIR, f'{name}.zip'))
  subprocess.run(['zip', '-r', f'{name}.zip', '.'], cwd=DIR)
  subprocess.run(
    ['aws', 's3', 'cp', os.path.join(DIR, f"{name}.zip"), 
     f's3://{S3_BUCKET}/{S3_KEY}/layers/{name}/v{NEW_VERSION:04d}.zip']
  )
  print(f"Uploaded {name} to S3.")

def main():
  options = parse_args()
  with open(options.file, "r") as f:
    settings_json = json.load(f)
  CURRENT_DIR = os.path.dirname(options.file)
  with open(os.path.join(CURRENT_DIR, settings_json["latest_version"]), "r") as f:
    versions = json.load(f)
  S3_BUCKET = settings_json['S3']['bucket']
  S3_KEY = settings_json['S3']['key']
  if options.external:
    DIR = os.path.join(CURRENT_DIR, settings_json['pip']['layer']['directory'])
    NEW_VERSION = versions['external'] + 1
    upload(S3_BUCKET, S3_KEY, NEW_VERSION, DIR, 'external')
    versions["external"] = NEW_VERSION
    with open(os.path.join(CURRENT_DIR, settings_json["latest_version"]), "w") as f:
      json.dump(versions, f, indent=2)
  if options.project:
    DIR = os.path.join(CURRENT_DIR, settings_json['layer']['directory'])
    NEW_VERSION = versions['project'] + 1
    upload(S3_BUCKET, S3_KEY, NEW_VERSION, DIR, 'project')
    versions["project"] = NEW_VERSION
    with open(os.path.join(CURRENT_DIR, settings_json["latest_version"]), "w") as f:
      json.dump(versions, f, indent=2)

if __name__ == '__main__':
  main()
