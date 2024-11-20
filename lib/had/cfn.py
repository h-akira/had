import os
import sys
import json
import importlib

LAMBDA = """\
  # Lambda関数の作成
  MyLambdaFunction{index}:
    Type: 'AWS::Lambda::Function'
    Properties:
      FunctionName: {prefix}-{app}-{name}
      Handler: lambda_function.lambda_handler
      Role: !GetAtt LambdaExecutionRole.Arn
      Code:
        S3Bucket: {S3_BUCKET}
        S3Key: {S3_KEY}/handlers/v{handlers_version:04d}/{app}/{name}.zip
      Runtime: python3.12
      Timeout: 10
      FileSystemConfigs: []
      Layers:
      - !Ref LambdaLayerExternal
      - !Ref LambdaLayerProject
      Architectures:
      - "x86_64"
"""
LAMBDA_PERMISSION = """\
  # LambdaにAPI Gatewayからの呼び出し権限を付与
  LambdaInvokePermission{permission_index}:
    Type: 'AWS::Lambda::Permission'
    Properties:
      FunctionName: !Ref MyLambdaFunction{index}
      Action: 'lambda:InvokeFunction'
      Principal: 'apigateway.amazonaws.com'
      SourceArn: !Sub
        arn:aws:execute-api:${{AWS::Region}}:${{AWS::AccountId}}:${{MyApiGateway{apigw_index}}}/*/{method}/{myresource}
"""

APIGW_METHOD_S3 = """\
  MyApiGatewayMethod{method_index}:
    Type: 'AWS::ApiGateway::Method'
    Properties:
      AuthorizationType: 'NONE'
      HttpMethod: 'GET'
      ResourceId: {ResourceId}
      RestApiId: !Ref MyApiGateway{apigw_index}
      RequestParameters:
        "method.request.path.item": true
      Integration:
        IntegrationHttpMethod: 'GET'
        Type: 'AWS'
        Uri:
          Fn::Sub: 'arn:aws:apigateway:${{AWS::Region}}:s3:path/{S3_BUCKET}/{S3_KEY}'
        Credentials:
          Fn::GetAtt:
            - APIGW2S3Role
            - Arn
        {RequestParameters}IntegrationResponses:
          - StatusCode: 200
            ResponseParameters:
              method.response.header.Content-Type: "'{CONTENT_TYPE}'"
      MethodResponses:
        - StatusCode: 200
          ResponseParameters:
            method.response.header.Content-Type: true

"""
APIGW_RESOURCE = """\
  MyResource{index}:
    Type: "AWS::ApiGateway::Resource"
    Properties:
      ParentId: {ParentId}
      PathPart: "{PathPart}"
      RestApiId: !Ref MyApiGateway{apigw_index}
"""

APIGW_METHOD_LAMBDA= """\
  MyApiGatewayMethod{method_index}:
    Type: 'AWS::ApiGateway::Method'
    Properties:
      AuthorizationType: 'NONE'
      HttpMethod: '{HttpMethod}'
      ResourceId: {ResourceId}
      RestApiId: !Ref MyApiGateway{apigw_index}
      Integration:
        IntegrationHttpMethod: 'POST'
        Type: 'AWS_PROXY'
        Uri: !Sub
          arn:aws:apigateway:${{AWS::Region}}:lambda:path/2015-03-31/functions/${{MyLambdaFunction{index}.Arn}}/invocations
      MethodResponses:
        - StatusCode: '200'
"""

MAIN= """\
AWSTemplateFormatVersion: '2010-09-09'
Resources:
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
      Policies:
        - PolicyName: "CognitoAdminAccess"
          PolicyDocument:
            Version: "2012-10-17"
            Statement:
              - Effect: "Allow"
                Action:
                  - "cognito-idp:AdminCreateUser"
                  - "cognito-idp:AdminGetUser"
                  - "cognito-idp:AdminUpdateUserAttributes"
                  - "cognito-idp:AdminDeleteUser"
                  - "cognito-idp:AdminSetUserPassword"
                Resource: "arn:aws:cognito-idp:ap-northeast-1:534449283880:userpool/{userPoolID}"
  
  # API GatewayからS3を参照するためのロール
  APIGW2S3Role:
    Type: "AWS::IAM::Role"
    Properties:
      Path: "/"
      ManagedPolicyArns:
      - "arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs"
      MaxSessionDuration: 3600
      RoleName: "{role_apigw2s3_name}"
      Description: "Allows API Gateway to push logs to CloudWatch Logs."
      Policies:
      - PolicyDocument:
          Version: "2012-10-17"
          Statement:
          - Resource: "arn:aws:s3:::{S3_BUCKET}/*"
            Action: "s3:GetObject"
            Effect: "Allow"
        PolicyName: "{policy_apigw2s3_name}"
      AssumeRolePolicyDocument:
        Version: "2012-10-17"
        Statement:
        - Action: "sts:AssumeRole"
          Effect: "Allow"
          Principal:
            Service: "apigateway.amazonaws.com"
          Sid: ""

  # Lambda Layerの作成
  LambdaLayerExternal:
    Type: "AWS::Lambda::LayerVersion"
    Properties: 
      LayerName: "{layer_name_external}"
      Description: "external library layer"
      Content: 
        S3Bucket: "{S3_BUCKET}"
        S3Key: "{S3_KEY}/layers/external/v{external_version:04d}.zip"
      CompatibleRuntimes: 
        - "python{PYTHON_VERSION}"

  LambdaLayerProject:
    Type: "AWS::Lambda::LayerVersion"
    Properties: 
      LayerName: "{layer_name_project}"
      Description: "external library layer"
      Content: 
        S3Bucket: "{S3_BUCKET}"
        S3Key: "{S3_KEY}/layers/project/v{project_version:04d}.zip"
      CompatibleRuntimes: 
        - "python{PYTHON_VERSION}"
"""
APIGW = """\
  # API Gateway REST APIの作成
  MyApiGateway{index}:
    Type: 'AWS::ApiGateway::RestApi'
    Properties:
      Name: '{api_name}'
      EndpointConfiguration:
        Types:
          - REGIONAL
"""

# DEPLOYMENT = """\
#   MyApiDeployment:
#     Type: 'AWS::ApiGateway::Deployment'
#     Properties:
#       RestApiId: !Ref MyApiGateway
#       StageName: {StageName}
# """
# """
#   # Optional: Stage-specific settings
#   MyStage:
#     Type: 'AWS::ApiGateway::Stage'
#     Properties:
#       DeploymentId: !Ref MyApiDeployment
#       RestApiId: !Ref MyApiGateway
#       StageName: {StageName}
#       Description: Deployment for version 1 of the API
#       MethodSettings:
#         - DataTraceEnabled: true
#           HttpMethod: "*"
#           LoggingLevel: INFO
#           ResourcePath: "/*"
#           MetricsEnabled: true
# """

def resource2index(resource):
  return resource.replace("/","XxXQq00qQXxX").replace("{","QXxQ00").replace("}","00QxXQ").replace("_","XqqxQ0QxqqX")

def lambdaname2index(lambdaname):
  return lambdaname.replace("-","Qx6QqX").replace("_","xQ4xXq").replace(":","Q2Qqxq")

def method2index(method):
  return method.replace("GET","QQQxq").replace("POST","XqQQQQXQq")

def apigw2index(apigw, gateways=None):
  if apigw.__class__ is int:
    if gateways is None:
      raise ValueError("gateways is None")
    else:
      apigw = gateways[apigw]["name"]
  return apigw.replace("-","Qx6QqX").replace("_","xQ4xXq")

def gen_yaml(settings_json_path, yaml_add=None, versions=None):
  with open(settings_json_path, "r") as f:
    settings_json = json.load(f)
  if yaml_add is not None: 
    with open(yaml_add, "r") as f:
      yaml_add = f.read()
  CURRENT_DIR = os.path.dirname(settings_json_path)
  sys.path.append(os.path.join(CURRENT_DIR,settings_json["layer"]["directory"], settings_json["layer"]["path"]))
  from project import settings
  # バージョンを取得
  if versions is None:
    with open(os.path.join(CURRENT_DIR, settings_json["latest_version"]), "r") as f:
      versions = json.load(f)
    if settings_json["layer"]["version"] != "latest":
      versions["project"] = settings_json["layer"]["version"]
    if settings_json["pip"]["layer"]["version"] != "latest":
      versions["external"] = settings_json["pip"]["layer"]["version"]
    if settings_json["handlers"]["version"] != "latest":
      versions["handlers"] = settings_json["handlers"]["version"]
  # 型を確認し、文字列の場合は置換
  global MAIN
  global LAMBDA
  if versions["project"].__class__ is str:
    MAIN = MAIN.replace("v{project_version:04d}", "{project_version}")
  if versions["external"].__class__ is str:
    MAIN = MAIN.replace("v{external_version:04d}", "{external_version}")
  if versions["handlers"].__class__ is str:
    LAMBDA = LAMBDA.replace("v{handlers_version:04d}", "{handlers_version}")
  # YAMLを生成開始
  YAML = MAIN.format(
    S3_BUCKET=settings_json["S3"]["bucket"],
    S3_KEY=settings_json["S3"]["key"],
    project_version=versions["project"],
    external_version=versions["external"],
    layer_name_project=settings_json["layer"]["name"],
    layer_name_external=settings_json["pip"]["layer"]["name"],
    # api_name=settings.AWS["API Gateway"]["name"],
    role_lambda_name=settings.AWS["Lambda"]["role"]["name"],
    role_apigw2s3_name=settings.AWS["API"]["role2s3"]["name"],
    policy_apigw2s3_name=settings.AWS["API"]["role2s3"]["policy"]["name"],
    userPoolID=settings.AWS["cognito"]["userPoolID"],
    PYTHON_VERSION=settings.PYTHON_VERSION
  )
  # API Gatewayを追加
  for apigw in settings.AWS["API"]["gateways"]:
    if apigw["override"]:
      YAML += apigw["override"]
    else:
      YAML += APIGW.format(
        index=apigw2index(apigw["name"]),
        api_name=apigw["name"]
      )
      if "binary-media-types" in apigw.keys() and len(apigw["binary-media-types"]) > 0:
        YAML += f"""\
      BinaryMediaTypes:
"""
        for binary_media_type in apigw["binary-media-types"]:
          if binary_media_type == "*/*":
            binary_media_type="'*/*'"
          YAML += """\
        - {}
""".format(binary_media_type)

  # Lambdaを追加
  lambda_list=[]
  # lambda_permission_counter = 0
  for APP in settings.APPS:
    urls = importlib.import_module(f"{APP['name']}.urls")
    for urlpattern in urls.urlpatterns:
      if urlpattern["integration"] == "lambda":
        prefix=settings.AWS["Lambda"]["prefix"]
        lambda_list.append(f"{APP['name']}:{urlpattern['name']}")
        myresource=os.path.join(APP["url"],urlpattern["url"])
        if myresource != "":
          if myresource[-1] == "/":
            myresource = myresource[:-1]
        YAML += LAMBDA.format(
          app=APP["name"],
          prefix=settings.AWS["Lambda"]["prefix"],
          name=urlpattern["name"],
          handlers_version=versions["handlers"],
          S3_BUCKET=settings_json["S3"]["bucket"],
          S3_KEY=settings_json["S3"]["key"],
          # index=lambda_list.index(f"{APP['name']}:{urlpattern['name']}")
          index=lambdaname2index(f"{APP['name']}:{urlpattern['name']}")
        )
        for method in urlpattern["methods"]:
          YAML += LAMBDA_PERMISSION.format(
            # index=lambda_list.index(f"{APP['name']}:{urlpattern['name']}"),
            index=lambdaname2index(f"{APP['name']}:{urlpattern['name']}"),
            # permission_index=lambda_permission_counter,
            permission_index=lambdaname2index(f"{APP['name']}:{urlpattern['name']}") + method2index(method),
            myresource=myresource,
            apigw_index=apigw2index(urlpattern["apigw"], settings.AWS["API"]["gateways"]),
            method=method
          )
          # lambda_permission_counter += 1
  # Resourceを作る
  for i, apigw in enumerate(settings.AWS["API"]["gateways"]):
    resource_list = [""]
    for APP in settings.APPS:
      root_resource = APP["url"]
      urls = importlib.import_module(f"{APP['name']}.urls")
      exist_name = []
      for urlpattern in urls.urlpatterns:
        if urlpattern["integration"].lower() == "cloudfront":
          continue
        if urlpattern["apigw"].__class__ is int and urlpattern["apigw"] != i:
          continue
        elif urlpattern["apigw"].__class__ is str and urlpattern["apigw"] != apigw["name"]:
          continue
        if urlpattern["name"] in exist_name:
          raise ValueError(f"Duplicate name: {urlpattern['name']}")
        exist_name.append(urlpattern["name"])
        URL = os.path.join(root_resource,urlpattern["url"])
        if URL == "":
          URL_SPLIT = [""]
        elif URL[-1] == "/":
          URL_SPLIT=URL[:-1].split("/")
        else:
          URL_SPLIT=URL.split("/")
        resource = ""
        for u in URL_SPLIT:
          if u == "":
            continue
          if resource == "":
            resource += u
          else:
            resource += "/" + u
          if resource not in resource_list:
            resource_list.append(resource)
            if "/" in resource:
              parent_resource = "/".join(resource.split("/")[:-1])
              # ParentId = "!Ref MyResource" + str(resource_list.index(parent_resource))
              ParentId = "!Ref MyResource" + resource2index(parent_resource)
            else:
              ParentId = f"!GetAtt MyApiGateway{apigw2index(apigw['name'])}.RootResourceId"
            YAML += APIGW_RESOURCE.format(
              # index=resource_list.index(resource),
              apigw_index=apigw2index(apigw["name"]),
              index=resource2index(resource),
              ParentId=ParentId,
              PathPart=u
            )
        else:
          # methodを作る
          if resource == "":
            ResourceId = f"!GetAtt MyApiGateway{apigw2index(apigw['name'])}.RootResourceId"
          else:
            # ResourceId = "!Ref MyResource" + str(resource_list.index(resource))
            ResourceId = "!Ref MyResource" + resource2index(resource)
          for method in urlpattern["methods"]:
            if urlpattern["integration"].lower() == "s3":
              DIC=urlpattern["function"]()
              if len(DIC["parameters"]) > 0:
                RequestParameters = "RequestParameters:\n"
                for key in DIC["parameters"]:
                  RequestParameters += """\
            "integration.request.path.{key}": "method.request.path.{key}"
""".format(key=key)
                else:
                  RequestParameters += """\
          """
              else:
                RequestParameters = ""
              YAML += APIGW_METHOD_S3.format(
                ResourceId=ResourceId,
                S3_BUCKET=settings_json["S3"]["bucket"],
                S3_KEY=os.path.join(settings_json["S3"]["key"], "integration", DIC["path"]),
                RequestParameters=RequestParameters,
                CONTENT_TYPE=DIC["content_type"],
                apigw_index=apigw2index(apigw["name"]),
                method_index = resource2index(resource) + method2index(method)
              )
            elif urlpattern["integration"].lower() == "lambda":
              YAML += APIGW_METHOD_LAMBDA.format(
                HttpMethod=method,
                ResourceId=ResourceId,
                name=urlpattern["name"],
                apigw_index=apigw2index(apigw["name"]),
                app=APP["name"],
                # index=lambda_list.index(f"{APP['name']}:{urlpattern['name']}"),

                index=lambdaname2index(f"{APP['name']}:{urlpattern['name']}"),
                method_index = resource2index(resource) + method2index(method)
              )
            elif urlpattern["integration"].lower() == "cloudfront":
              pass
            else:
              raise ValueError(f"Invalid integration: {urlpattern['integration']}")
  # YAML += DEPLOYMENT.format(
  #   StageName=settings.AWS["API Gateway"]["stage"]
  # )
  if yaml_add is not None:
    YAML += "\n" + yaml_add
  with open(settings_json["CloudFormation"]["template"], "w") as f:
    f.write(YAML)
  print("Complete!")

if __name__ == '__main__':
  main()

