import json
import os
import sys
import subprocess

python_shell = """\
#!/bin/zsh
#
# Created:      2024-07-29 23:30:28
set -eu

# このスクリプトがあるディレクトリに移動
cd `dirname $0`
cd ..

VERSION=$(jq -r ".python.version" settings.json)
TARGET=$(realpath $(jq -r ".pip.target" settings.json))
mkdir -p $TARGET
# envディレクトリがない場合は作成
if [ ! -d env ]; then
  python$VERSION -m venv env
  if [ $? -ne 0 ]; then
    echo "Failed to create virtual environment"
    exit 1
  else
    echo "Virtual environment created"
    if [ ! $# -eq 0 ]; then
      echo "Plese run command again."
    fi
  fi
  exit 0
fi
# コマンドライン引数がなければ終了
if [ $# -eq 0 ]; then
  echo "Usage: pip.sh [command] [options]"
  exit 1
fi
# python3のversionが3.12かどうか
if [ `python3 --version | awk '{print $2}' | cut -d. -f1,2` != "$VERSION" ]; then
  echo "Python version is not $VERSION"
  exit 1
fi
source env/bin/activate

PROJECT_REAL_PATH=$(realpath $(jq -r ".target" settings.json))
export PYTHONPATH="$PROJECT_REAL_PATH:$TARGET"
python3 $@
deactivate
"""
pip_shell = """\
#!/bin/zsh
#
# Created:      2024-07-29 23:30:28
set -eu

# このスクリプトがあるディレクトリに移動
cd `dirname $0`
cd ..

VERSION=$(jq -r ".python.version" settings.json)
WHERE=$(jq -r ".pip.target" settings.json)
mkdir -p $WHERE
# envディレクトリがない場合は作成
if [ ! -d env ]; then
  python$VERSION -m venv env
  if [ $? -ne 0 ]; then
    echo "Failed to create virtual environment"
    exit 1
  else
    echo "Virtual environment created"
    if [ ! $# -eq 0 ]; then
      echo "Plese run command again."
    fi
  fi
  exit 0
fi
# コマンドライン引数がなければ終了
if [ $# -eq 0 ]; then
  echo "Usage: pip.sh [command] [options]"
  exit 1
fi
# python3のversionが3.12かどうか
if [ `python3 --version | awk '{print $2}' | cut -d. -f1,2` != "$VERSION" ]; then
  echo "Python version is not $VERSION"
  exit 1
fi
source env/bin/activate

if [ $1 = "install" ]; then
  if [ $2 = "-r" ]; then
    pip install -r $3 -t $WHERE
  else
    pip install $2 -t $WHERE
  fi
elif [ $1 = "install2" ]; then
  if [ $2 = "-r" ]; then
    pip install -r $3 -t $WHERE
    pip install -r $3
  else
    pip install $2 -t $WHERE
    pip install $2
  fi
else
  pip $@
fi
deactivate
"""

settings_json_init = """\
{{
  "name": "{project_name}",
  "stack":"{stack_name}",
  "environment":"{environment}",
  "region":"ap-northeast-1",
  "target":"build/project/python/lib/python{python_version}/site-packages",
  "layer":{{
    "name":"layer-{stack_name}-project",
    "version":"latest",
    "directory":"build/project",
    "path":"python/lib/python{python_version}/site-packages"
  }},
  "latest_version":"latest_version.json",
  "python":{{
    "version": "{python_version}"
  }},
  "pip":{{
    "target":"build/external/python/lib/python{python_version}/site-packages",
    "layer":{{
      "name":"layer-{stack_name}-external",
      "version":"latest",
      "directory":"build/external",
      "path":"python/lib/python{python_version}/site-packages"
    }}
  }},
  "handlers":{{
    "directory":"build/handlers",
    "version":"latest"
  }},
  "S3":{{
    "bucket":"{s3_bucket}",
    "key":"had"
  }},
  "CloudFormation":{{
    "stack_name":"stack-{stack_name}-{environment}",
    "template":"cfn-template.yaml"
  }}
}}"""

settings_py_init = """\
import os

PROJECT_NAME = "{project_name}"
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
HANDLERS_DIR = os.path.join(BASE_DIR, '../handlers')
PYTHON_VERSION = '{python_version}'
# LOGIN_URL = "accounts:login"
# LOGIN_REDIRECT_URL = "XXXXX:XXXXX"
# LOGOUT_REDIRECT_URL = "XXXXX:XXXXX"  
LOCAL = False
LOCAL_TEMPLATES = "build/templates"
MAPPING_PATH = ""  # URL Mapping Path (if you don't use custom domain, this is stage name)
AWS = {{
  "account": "{account}",
  "region": "ap-northeast-1",
  "API":{{
    "role2s3":{{
      "name":"role-{stack}-{environment}-api2s3",
      "policy":{{
        "name":"policy-{stack}-{environment}-api2s3"
      }}
    }},
    "gateways":[
      {{
        "name":"api-{stack}-{environment}",
        "binary-media-types":[]
      }}
    ]
  }},
  "Lambda":{{
    "prefix":"{stack}-{environment}-lambda",
    "timeout":10,
    "memory":128,
    "role":{{
      "name":"role-{stack}-{environment}-lambda-common",
    }}
  }},
  "S3":{{
    "bucket":"{s3_bucket}",
    "key":"had"
  }},
  # "cognito":{{
  #   "userPoolID":"XXXXX",
  #   "clientID":"XXXXX"
  # }}
}}
APPS = [
  # {{
  #   'name': 'accounts',
  #   'url': 'accounts'
  # }},
  # {{
  #   "name": "static",
  #   "url": "static"
  # }}
]
DEBUG = True
"""

cfn_py_init = """\
# This file exists to overwrite the base class when generating a cloud formation template.
# The base class is located at the following URL:
# https://github.com/h-akira/had/blob/main/lib/had/cfn.py

from had.cfn import Template

class MyTemplate(Template):
  ROLE_LAMBDA = \"\"\"\
  # Lambda実行ロールの作成
  LambdaExecutionRole:
    Type: 'AWS::IAM::Role'
    Properties:
      Path: "/"
      ManagedPolicyArns:
      - "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
      - "arn:aws:iam::aws:policy/AmazonS3FullAccess"
      - "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess"
      MaxSessionDuration: 3600
      RoleName: "{role_lambda_name}"
      Description: lambda-common"
      AssumeRolePolicyDocument:
        Version: "2012-10-17"
        Statement:
        - Action: "sts:AssumeRole"
          Effect: "Allow"
          Principal:
            Service: "lambda.amazonaws.com"
\"\"\"
      # Policies:
      #   - PolicyName: "CognitoAdminAccess"
      #     PolicyDocument:
      #       Version: "2012-10-17"
      #       Statement:
      #         - Effect: "Allow"
      #           Action:
      #             - "cognito-idp:AdminCreateUser"
      #             - "cognito-idp:AdminGetUser"
      #             - "cognito-idp:AdminUpdateUserAttributes"
      #             - "cognito-idp:AdminDeleteUser"
      #             - "cognito-idp:AdminSetUserPassword"
      #           Resource: "arn:aws:cognito-idp:{region}:{accountID}:userpool/{userPoolID}"
  def gen_kwargs_ROLE_LAMBDA(self):
    kwargs = dict(
      role_lambda_name=self.settings.AWS["Lambda"]["role"]["name"],
      # region=self.settings.AWS["region"],
      # accountID=self.settings.AWS["account"],
      # userPoolID=self.settings.AWS["cognito"]["userPoolID"],
    )
    return kwargs
  def __init__(self, settings_json_path, versions=None):
    super().__init__(settings_json_path, versions)
"""

def get_account():
  account = subprocess.run(
    ["aws", "sts", "get-caller-identity"],
    stdout=subprocess.PIPE
  ).stdout
  return json.loads(account)["Account"]

def start_project():
  account = get_account()
  project_name = input("Enter project name (Generate a directory with this name): ")
  if os.path.exists(project_name):
    print("Project already exists.")
    return False
  s3_bucket = input("Enter S3 bucket name (It is recommended that it be created in advance.): ")
  while True:
    stack_name = input("Enter stack name (This will be included in the resource name): ")
    if stack_name:
      break
    else:
      print("Stack name is required.")
  environment = input("Enter environment name (Default is 'stg'. This will be included in the resource name): ")
  if not environment:
    environment = "stg"
  python_version = input("Enter Python version (Default is 3.12): ")
  if not python_version:
    python_version = "3.12"
  print("Creating project...")
  os.makedirs(project_name)
  os.makedirs(os.path.join(project_name, "bin"))
  with open(os.path.join(project_name, "bin", "python.sh"), "w") as f:
    f.write(python_shell)
  os.chmod(os.path.join(project_name, "bin", "python.sh"), 0o755)
  with open(os.path.join(project_name, "bin", "pip.sh"), "w") as f:
    f.write(pip_shell)
  os.chmod(os.path.join(project_name, "bin", "pip.sh"), 0o755)
  with open(os.path.join(project_name, "settings.json"), "w") as f:
    f.write(
      settings_json_init.format(
        project_name=project_name, 
        stack_name=stack_name, 
        environment=environment, 
        python_version=python_version, 
        s3_bucket=s3_bucket
      )
    )
  os.makedirs(os.path.join(project_name, "build/handlers"))
  os.makedirs(os.path.join(project_name, "build/project/templates"))
  os.makedirs(os.path.join(project_name, "build/project/python/lib/python{}/site-packages/project".format(python_version)))
  os.makedirs(os.path.join(project_name, "build/external/python/lib/python{}/site-packages".format(python_version)))
  os.symlink(
    "build/project/python/lib/python{}/site-packages".format(python_version), 
    os.path.join(project_name, project_name)
  )
  os.symlink(
    "build/project/templates", 
    os.path.join(project_name, "templates")
  )
  with open(os.path.join(project_name, "build/project/python/lib/python{}/site-packages/project/settings.py".format(python_version)), "w") as f:
    f.write(
      settings_py_init.format(
        project_name=project_name,
        python_version=python_version,
        account=account,
        stack=stack_name,
        environment=environment,
        s3_bucket=s3_bucket
      )
    )
  with open(os.path.join(project_name, "build/project/python/lib/python{}/site-packages/project/cfn.py".format(python_version)), "w") as f:
    f.write(cfn_py_init)


