#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created: 2024-08-27 20:51:12

import sys
import os
import json
import datetime
from zoneinfo import ZoneInfo

def parse_args():
  import argparse
  parser = argparse.ArgumentParser(description="""\

""", formatter_class = argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument("--version", action="version", version='%(prog)s 0.0.1')
  parser.add_argument("-s", "--start-project", action="store_true", help="start project")
  parser.add_argument("-u", "--cfn-update", metavar="settings-json", help="update cludformation stack")
  parser.add_argument("-d", "--cfn-delete", metavar="settings-json", help="delete cludformation stack")
  parser.add_argument("-c", "--cfn-create", metavar="settings-json", help="create cludformation stack")
  parser.add_argument("-x", "--cfn-exists", metavar="settings-json", help="check if cludformation stack exists")
  parser.add_argument("-Y", "--generate-cfn-yaml", metavar="settings-json", help="settings.json file")
  parser.add_argument("-A", "--generate-cfn-yaml-add", metavar="yaml-file", help="yaml file to add to the generated yaml file")
  parser.add_argument("-H", "--generate-handlers", metavar="settings-json", help="settings.json file")
  parser.add_argument("-a", "--handlers2s3", metavar="settings-json", help="settings.json file")
  parser.add_argument("-p", "--project2s3", metavar="settings-json", help="settings.json file")
  parser.add_argument("-e", "--external2s3", metavar="settings-json", help="settings.json file")
  parser.add_argument("-D", "--deploy-all", metavar="settings-json", help="do all step to deploy")
  parser.add_argument("-w", "--no-wait", action="store_true", help="do not wait for the completion of \
the operation when execute cloudformation create, update, delete")
  options = parser.parse_args()
  return options

def print_not_executed(options, executed: list):
  if options.start_project and "start_project" not in executed:
    print("-s/--start-project option is not executed.")
  if options.cfn_update and "cfn_update" not in executed:
    print("-u/--cfn-update option is not executed.")
  if options.cfn_delete and "cfn_delete" not in executed:
    print("-d/--cfn-delete option is not executed.")
  if options.cfn_create and "cfn_create" not in executed:
    print("-c/--cfn-create option is not executed.")
  if options.cfn_exists and "cfn_exists" not in executed:
    print("-x/--cfn-exists option is not executed.")
  if options.generate_cfn_yaml and "generate_cfn_yaml" not in executed:
    print("-Y/--generate-cfn-yaml option is not executed.")
  # if options.generate_cfn_yaml_add and "generate_cfn_yaml_add" not in executed:
  #   print("-A/--generate-cfn-yaml-add option is not executed.")
  if options.generate_handlers and "generate_handlers" not in executed:
    print("-H/--generate-handlers option is not executed.")
  if options.handlers2s3 and "handlers2s3" not in executed:
    print("-a/--handlers2s3 option is not executed.")
  if options.project2s3 and "project2s3" not in executed:
    print("-p/--project2s3 option is not executed.")
  if options.external2s3 and "external2s3" not in executed:
    print("-e/--external2s3 option is not executed.")
  if options.deploy_all and "deploy_all" not in executed:
    print("-D/--deploy-all option is not executed.")

def main():
  options = parse_args()
  if options.start_project:
    print("===== Start Project =====")
    from had.start import start_project
    start_project()
    print_not_executed(options, ["start_project"])
    sys.exit()
  if options.deploy_all:
    print("===== Deploy All =====")
    from had.scripts import gen_handlers, handlers2s3, layers2s3, cfn_create, cfn_update, cfn_exists
    from had.cfn import gen_yaml
    now = datetime.datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y%m%d%H%M%S")
    versions = {
      "handlers": now,
      "external": now,
      "project": now
    }
    gen_handlers(options.deploy_all)
    handlers2s3(options.deploy_all, versions=versions)
    layers2s3(options.deploy_all, project_upload=True, external_upload=True, versions=versions)
    gen_yaml(options.deploy_all, yaml_add=options.generate_cfn_yaml_add, versions=versions)
    if cfn_exists(options.deploy_all, print_message=False):
      cfn_update(options.deploy_all, wait=not options.no_wait)
    else:
      cfn_create(options.deploy_all, wait=not options.no_wait)
    print_not_executed(options, ["deploy_all"])
    sys.exit()

  # 複数実行可能
  if options.generate_handlers:
    print("===== Generate Handlers =====")
    from had.scripts import gen_handlers
    gen_handlers(options.generate_handlers)
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
  if options.generate_cfn_yaml:
    print("===== Generate CloudFormation YAML =====")
    from had.cfn import gen_yaml
    gen_yaml(options.generate_cfn_yaml, options.generate_cfn_yaml_add)

  # どれか一つだけ実行可能
  if options.cfn_update:
    print("===== Update CloudFormation =====")
    from had.scripts import cfn_update
    cfn_update(options.cfn_update, wait=not options.no_wait)
    print_not_executed(
      options,
      ["cfn_update", "generate_handlers", "handlers2s3", "project2s3", "external2s3", "generage_cfn_yaml"]
    )
  elif options.cfn_delete:
    print("===== Delete CloudFormation =====")
    from had.scripts import cfn_delete
    cfn_delete(options.cfn_delete, wait=not options.no_wait)
    print_not_executed(
      options,
      ["cfn_delete", "generate_handlers", "handlers2s3", "project2s3", "external2s3", "generage_cfn_yaml"]
    )
  elif options.cfn_create:
    print("===== Create CloudFormation =====")
    from had.scripts import cfn_create
    cfn_create(options.cfn_create, wait=not options.no_wait)
    print_not_executed(
      options,
      ["cfn_create", "generate_handlers", "handlers2s3", "project2s3", "external2s3", "generage_cfn_yaml"]
    )
  elif options.cfn_exists:
    print("===== Check CloudFormation =====")
    from had.scripts import cfn_exists
    cfn_exists(options.cfn_exists)
    print_not_executed(
      options,
      ["cfn_exists", "generate_handlers", "handlers2s3", "project2s3", "external2s3", "generage_cfn_yaml"]
    )

if __name__ == '__main__':
  main()
