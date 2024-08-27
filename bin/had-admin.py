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
  parser.add_argument("-s", "--start-project", metavar="project-name", help="project name")
  parser.add_argument("-Y", "--generate-cfn-yaml", metavar="settings-json", help="settings.json file")
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

def main():
  options = parse_args()
  if options.generate_cfn_yaml:
    print("===== Generate CloudFormation YAML =====")
    from had.cfn import gen_yaml
    gen_yaml(options.generate_cfn_yaml)
  elif options.generate_handlers:
    print("===== Generate Handlers =====")
    from had.handler import gen_handlers
    gen_handlers(options.generate_handlers)
  else:
    if options.handlers2s3:
      print("===== Handlers to S3 =====")
      from had.scripts import handlers2s3
      handlers2s3(options.handlers2s3)
    if options.project1s3:
      print("===== Project to S3 =====")
      from had.scripts import project2s3
      project2s3(options.project2s3, project_upload=True)
    if options.external2s3:
      print("===== External to S3 =====")
      from had.scripts import external2s3
      external2s3(options.external2s3)

if __name__ == '__main__':
  main()
