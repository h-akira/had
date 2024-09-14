#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created: 2024-08-27 20:51:12

import sys
import os
import json

def parse_args():
  import argparse
  parser = argparse.ArgumentParser(description="""\

""", formatter_class = argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument("--version", action="version", version='%(prog)s 0.0.1')
  parser.add_argument("-s", "--start-project", action="store_true", help="start project")
  parser.add_argument("-u", "--cfn-update", metavar="settings-json", help="update cludformation stack")
  parser.add_argument("-d", "--cfn-delete", metavar="settings-json", help="delete cludformation stack")
  parser.add_argument("-c", "--cfn-create", metavar="settings-json", help="create cludformation stack")
  parser.add_argument("-Y", "--generate-cfn-yaml", metavar="settings-json", help="settings.json file")
  parser.add_argument("-A", "--generate-cfn-yaml-add", metavar="yaml-file", help="yaml file to add to the generated yaml file")
  parser.add_argument("-H", "--generate-handlers", metavar="settings-json", help="settings.json file")
  parser.add_argument("-a", "--handlers2s3", metavar="settings-json", help="settings.json file")
  parser.add_argument("-p", "--project2s3", metavar="settings-json", help="settings.json file")
  parser.add_argument("-e", "--external2s3", metavar="settings-json", help="settings.json file")
  # parser.add_argument("-o", "--output", metavar="output-file", default="output", help="output file")
  # parser.add_argument("-", "--", action="store_true", help="")
  # parser.add_argument("file", metavar="input-file", help="input file")
  options = parser.parse_args()
  # if not os.path.isfile(options.file): 
  #   raise Exception("The input file does not exist.") 
  return options

# def project_path_append(settings_json_path):
#   with open(settings_json_path) as f:
#     settings_json = json.load(f)
#   CURRENT_DIR = os.path.dirname(settings_json_path)
#   sys.path.append(
#     os.path.join(CURRENT_DIR, settings_json["layer"]["directory"], settings_json["layer"]["path"])
#   )

def main():
  options = parse_args()
  if options.start_project:
    print("===== Start Project =====")
    from had.start import start_project
    start_project()
  elif options.cfn_update:
    print("===== Update CloudFormation =====")
    from had.scripts import cfn_update
    cfn_update(options.cfn_update)
  elif options.cfn_delete:
    print("===== Delete CloudFormation =====")
    from had.scripts import cfn_delete
    cfn_delete(options.cfn_delete)
  elif options.cfn_create:
    print("===== Create CloudFormation =====")
    from had.scripts import cfn_create
    cfn_create(options.cfn_create)
  elif options.generate_cfn_yaml:
    print("===== Generate CloudFormation YAML =====")
    from had.cfn import gen_yaml
    gen_yaml(options.generate_cfn_yaml, options.generate_cfn_yaml_add)
  elif options.generate_handlers:
    print("===== Generate Handlers =====")
    from had.scripts import gen_handlers
    gen_handlers(options.generate_handlers)
  else:
    if options.handlers2s3:
      print("===== Handlers to S3 =====")
      from had.scripts import handlers2s3
      handlers2s3(options.handlers2s3)
    if options.project2s3:
      print("===== Project to S3 =====")
      from had.scripts import layers2s3
      layers2s3(options.project2s3, project_upload=True)
    if options.external2s3:
      print("===== External to S3 =====")
      from had.scripts import layers2s3
      layers2s3(options.external2s3, external_upload=True)

if __name__ == '__main__':
  main()
