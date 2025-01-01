import os
import sys
import json
import importlib
import random

class Template:
  LAMBDA_FUNCTION = """\
  # Lambda関数の作成
  MyLambdaFunction{function_index}:
    Type: 'AWS::Lambda::Function'
    Properties:
      FunctionName: {prefix}-{app}-{name}
      Handler: lambda_function.lambda_handler
      Role: !GetAtt LambdaExecutionRole.Arn
      Code:
        S3Bucket: {S3_BUCKET}
        S3Key: {S3_KEY}/handlers/{handlers_version}/{app}/{name}.zip
      Runtime: python3.12
      Timeout: {timeout}
      FileSystemConfigs: []
      Layers:
      - !Ref LambdaLayerExternal
      - !Ref LambdaLayerProject
      Architectures:
      - "x86_64"
      MemorySize: {memory}
"""
  LAMBDA_PERMISSION = """\
  # LambdaにAPI Gatewayからの呼び出し権限を付与
  LambdaInvokePermission{permission_index}:
    Type: 'AWS::Lambda::Permission'
    Properties:
      FunctionName: !Ref MyLambdaFunction{function_index}
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
  MyResource{resource_index}:
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
          arn:aws:apigateway:${{AWS::Region}}:lambda:path/2015-03-31/functions/${{MyLambdaFunction{function_index}.Arn}}/invocations
      MethodResponses:
        - StatusCode: 200
"""
  ROLE_LAMBDA = """\
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
      Description: "lambda-common"
      AssumeRolePolicyDocument:
        Version: "2012-10-17"
        Statement:
        - Action: "sts:AssumeRole"
          Effect: "Allow"
          Principal:
            Service: "lambda.amazonaws.com"
"""
  ROLE_APIGW2S3 = """\
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
"""
  BASE = """\
AWSTemplateFormatVersion: '2010-09-09'
Resources:
  # Lambda Layerの作成
  LambdaLayerExternal:
    Type: "AWS::Lambda::LayerVersion"
    Properties: 
      LayerName: "{layer_name_external}"
      Description: "external library layer"
      Content: 
        S3Bucket: "{S3_BUCKET}"
        S3Key: "{S3_KEY}/layers/external/{external_version}.zip"
      CompatibleRuntimes: 
        - "python{PYTHON_VERSION}"

  LambdaLayerProject:
    Type: "AWS::Lambda::LayerVersion"
    Properties: 
      LayerName: "{layer_name_project}"
      Description: "external library layer"
      Content: 
        S3Bucket: "{S3_BUCKET}"
        S3Key: "{S3_KEY}/layers/project/{project_version}.zip"
      CompatibleRuntimes: 
        - "python{PYTHON_VERSION}"
"""
  APIGW = """\
  MyApiGateway{apigw_index}:
    Type: 'AWS::ApiGateway::RestApi'
    Properties:
      Name: '{api_name}'
      EndpointConfiguration:
        Types:
          - REGIONAL
{binary_media_types}

  MyApiGatewayDeployment{apigw_index}{random_id}:
    DependsOn: 
{depend_methods}
    Type: AWS::ApiGateway::Deployment
    DeletionPolicy: Delete
    Properties:
      RestApiId: !Ref MyApiGateway{apigw_index}

  MyApiGatewayStage{apigw_index}:
    Type: AWS::ApiGateway::Stage
    DeletionPolicy: Delete
    Properties:
      DeploymentId: !GetAtt MyApiGatewayDeployment{apigw_index}{random_id}.DeploymentId
      StageName: stage-01
      TracingEnabled: false
      RestApiId: !Ref MyApiGateway{apigw_index}
      MethodSettings:
        - CacheTtlInSeconds: 300
          LoggingLevel: INFO
          ResourcePath: /*
          CacheDataEncrypted: false
          DataTraceEnabled: true
          ThrottlingBurstLimit: 5000
          CachingEnabled: false
          MetricsEnabled: true
          HttpMethod: '*'
          ThrottlingRateLimit: 10000
      CacheClusterSize: '0.5'
      CacheClusterEnabled: false
"""
  resource2index_dic = {
    "/" : "XsX",
    "{" : "XlX",
    "}" : "XrX",
    "_" : "XuX",
    "." : "XdX",
    "-" : "XhX",
  }
  lambda2index_dic = {
    "-" : "XhX",
    "_" : "XuX",
    ":" : "XcX",
    "." : "XdX"
  }
  method2index_dic = {
    "GET" : "XgX",
    "POST" : "XpX"
  }
  apigw2index_dic = {
    "-" : "XhX",
    "_" : "XuX"
  }
  def replace_all(self, s, dic):
    for i, j in dic.items():
      s = s.replace(i, j)
    return s
  def resource2index(self, resource):
    return self.replace_all(resource, self.resource2index_dic)
  def lambda2index(self, lambdaname):
    return self.replace_all(lambdaname, self.lambda2index_dic)
  def method2index(self, method):
    return self.replace_all(method, self.method2index_dic)
  def apigw2index(self, apigw, gateways=None):
    if apigw.__class__ is int:
      if gateways is None:
        raise ValueError("gateways is None")
      else:
        apigw = gateways[apigw]["name"]
    return self.replace_all(apigw, self.apigw2index_dic)
  def gen_random_id(self, length=8):
    return "".join([random.choice("abcdefghijklmnopqrstuvwxyz0123456789") for i in range(length)])
  def get_latest_versions(self, latest_version_path):
    if os.path.exists(latest_version_path):
      with open(latest_version_path, mode="r") as f:
        return json.load(f)
    else:
      raise FileNotFoundError(f"{latest_version_path} not found")
  def set_versions(self, versions, CURRENT_DIR):
    if versions is None:
      self.versions = {}
      if self.settings_json["handlers"]["version"]=="latest" or \
self.settings_json["layer"]["version"]=="latest" or \
self.settings_json["pip"]["layer"]["version"]=="latest":
        latest_versions = self.get_latest_versions(os.path.join(CURRENT_DIR, self.settings_json["latest_version"]))
      if self.settings_json["handlers"]["version"] == "latest":
        self.versions["handlers"] = latest_versions["handlers"]
      else:
        self.versions["handlers"] = self.settings_json["handlers"]["version"]
      if self.settings_json["layer"]["version"] == "latest":
        self.versions["project"] = latest_versions["project"]
      else:
        self.versions["project"] = self.settings_json["layer"]["version"]
      if self.settings_json["pip"]["layer"]["version"] == "latest":
        self.versions["external"] = latest_versions["external"]
      else:
        self.versions["external"] = self.settings_json["pip"]["layer"]["version"]
    else:
      self.versions = versions
  def gen_kwargs_BASE(self):
    kwargs = dict(
      layer_name_project=self.settings_json["layer"]["name"],
      layer_name_external=self.settings_json["pip"]["layer"]["name"],
      S3_BUCKET=self.settings_json["S3"]["bucket"],
      S3_KEY=self.settings_json["S3"]["key"],
      project_version=self.versions["project"],
      external_version=self.versions["external"],
      PYTHON_VERSION=self.settings.PYTHON_VERSION
    )
    return kwargs
  def gen_kwargs_ROLE_LAMBDA(self):
    kwargs = dict(
      role_lambda_name=self.settings.AWS["Lambda"]["role"]["name"]
    )
    return kwargs
  def gen_kwargs_ROLE_APIGW2S3(self):
    kwargs = dict(
      S3_BUCKET=self.settings_json["S3"]["bucket"],
      role_apigw2s3_name=self.settings.AWS["API"]["role2s3"]["name"],
      policy_apigw2s3_name=self.settings.AWS["API"]["role2s3"]["policy"]["name"],
    )
    return kwargs
  def add_BASE(self):
    kwargs = self.gen_kwargs_BASE()
    self.YAML += self.BASE.format(**kwargs)
  def add_ROLE_LAMBDA(self):
    kwargs = self.gen_kwargs_ROLE_LAMBDA()
    self.YAML += self.ROLE_LAMBDA.format(**kwargs)
  def add_ROLE_APIGW2S3(self):
    kwargs = self.gen_kwargs_ROLE_APIGW2S3()
    self.YAML += self.ROLE_APIGW2S3.format(**kwargs)
  def gen_kwargs_APIGW(self, apigw, depend_method_indexs):
    binary_media_types = ""
    if "binary-media-types" in apigw.keys() and len(apigw["binary-media-types"]) > 0:
      binary_media_types += f"""\
      BinaryMediaTypes:
"""
      for binary_media_type in apigw["binary-media-types"]:
        if binary_media_type == "*/*":
          binary_media_type="'*/*'"
        binary_media_types += """\
        - {}
""".format(binary_media_type)
    depend_methods = ""
    for depend_method_index in depend_method_indexs:
      depend_methods += f"""\
      - MyApiGatewayMethod{depend_method_index}
"""
    else:
      if depend_methods != "" and depend_methods[-1] == "\n":
        depend_methods = depend_methods[:-1]
    kwargs = dict(
      apigw_index=self.apigw2index(apigw["name"]),
      api_name=apigw["name"],
      binary_media_types=binary_media_types,
      depend_methods=depend_methods,
      random_id=self.gen_random_id()
    )
    return kwargs
  def add_APIGW(self, apigw, depends_on_method_index):
    kwargs = self.gen_kwargs_APIGW(apigw, depends_on_method_index)
    self.YAML += self.APIGW.format(**kwargs)
  def gen_kwargs_LAMBDA_FUNCTION(self, APP, urlpattern):
    prefix=self.settings.AWS["Lambda"]["prefix"]
    if urlpattern["timeout"] is None:
      timeout = self.settings.AWS["Lambda"].get("timeout")
      if timeout is None:
        timeout = 10
    else:
      timeout = urlpattern["timeout"]
    if urlpattern["memory"] is None:
      memory = self.settings.AWS["Lambda"].get("memory")
      if memory is None:
        memory = 128
    else:
      memory = urlpattern["memory"]
    kwargs = dict(
      app=APP["name"],
      prefix=prefix,
      name=urlpattern["name"],
      handlers_version=self.versions["handlers"],
      S3_BUCKET=self.settings_json["S3"]["bucket"],
      S3_KEY=self.settings_json["S3"]["key"],
      function_index=self.lambda2index(f"{APP['name']}:{urlpattern['name']}"),
      timeout=timeout,
      memory=memory
    )
    return kwargs
  def add_LAMBDA_FUNCTION(self, APP, urlpattern):
    kwargs = self.gen_kwargs_LAMBDA_FUNCTION(APP, urlpattern)
    self.YAML += self.LAMBDA_FUNCTION.format(**kwargs)
  def gen_kwargs_LAMBDA_PERMISSION(self, APP, urlpattern, method):
    myresource=os.path.join(APP["url"],urlpattern["url"])
    if myresource != "":
      if myresource[-1] == "/":
        myresource = myresource[:-1]
    kwargs = dict(
      function_index=self.lambda2index(f"{APP['name']}:{urlpattern['name']}"),
      permission_index=self.lambda2index(f"{APP['name']}:{urlpattern['name']}") + self.method2index(method),
      myresource=myresource,
      apigw_index=self.apigw2index(urlpattern["apigw"], self.settings.AWS["API"]["gateways"]),
      method=method
    )
    return kwargs
  def add_LAMBDA_PERMISSION(self, APP, urlpattern, method):
    kwargs = self.gen_kwargs_LAMBDA_PERMISSION(APP, urlpattern, method)
    self.YAML += self.LAMBDA_PERMISSION.format(**kwargs)
  def gen_kwargs_APIGW_RESOURCE(self, apigw, resource, ParentId, PathPart):
    kwargs = dict(
      apigw_index=self.apigw2index(apigw["name"]),
      resource_index=self.resource2index(resource),
      ParentId=ParentId,
      PathPart=PathPart
    )
    return kwargs
  def add_APIGW_RESOURCE(self, apigw, resource, ParentId, PathPart):
    kwargs = self.gen_kwargs_APIGW_RESOURCE(apigw, resource, ParentId, PathPart)
    self.YAML += self.APIGW_RESOURCE.format(**kwargs)
  def gen_kwargs_APIGW_METHOD_S3(self, apigw, resource, method, ResourceId, DIC):
    # DIC=urlpattern["function"]()
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
    kwargs = dict(
      ResourceId=ResourceId,
      S3_BUCKET=self.settings_json["S3"]["bucket"],
      S3_KEY=os.path.join(self.settings_json["S3"]["key"], "integration", DIC["path"]),
      RequestParameters=RequestParameters,
      CONTENT_TYPE=DIC["content_type"],
      apigw_index=self.apigw2index(apigw["name"]),
      method_index = self.resource2index(resource) + self.method2index(method)
    )
    return kwargs
  def add_APIGW_METHOD_S3(self, apigw, resource, method, ResourceId, DIC):
    kwargs = self.gen_kwargs_APIGW_METHOD_S3(apigw, resource, method, ResourceId, DIC)
    self.YAML += self.APIGW_METHOD_S3.format(**kwargs)
    return kwargs["method_index"]
  def gen_kwargs_APIGW_METHOD_LAMBDA(self, APP, urlpattern, method, ResourceId, apigw, resource):
    kwargs = dict(
      HttpMethod=method,
      ResourceId=ResourceId,
      name=urlpattern["name"],
      apigw_index=self.apigw2index(apigw["name"]),
      app=APP["name"],
      function_index=self.lambda2index(f"{APP['name']}:{urlpattern['name']}"),
      method_index=self.resource2index(resource)+self.method2index(method)
    )
    return kwargs
  def add_APIGW_METHOD_LAMBDA(self, APP, urlpattern, method, ResourceId, apigw, resource):
    kwargs = self.gen_kwargs_APIGW_METHOD_LAMBDA(APP, urlpattern, method,  ResourceId, apigw, resource)
    self.YAML += self.APIGW_METHOD_LAMBDA.format(**kwargs)
    return kwargs["method_index"]
  def __init__(self, settings_json_path, versions=None):
    self.YAML = ""
    with open(settings_json_path, "r") as f:
      self.settings_json = json.load(f)
    CURRENT_DIR = os.path.dirname(settings_json_path)
    self.set_versions(versions, CURRENT_DIR)
    sys.path.append(
      os.path.join(
        CURRENT_DIR, 
        self.settings_json["layer"]["directory"], 
        self.settings_json["layer"]["path"]
      )
    )
    from project import settings
    self.settings = settings
    # YAMLを生成開始
    self.add_BASE()
    self.add_ROLE_LAMBDA()
    self.add_ROLE_APIGW2S3()
    # Lambdaを追加
    for APP in settings.APPS:
      urls = importlib.import_module(f"{APP['name']}.urls")
      for urlpattern in urls.urlpatterns:
        if urlpattern["integration"] == "lambda":
          self.add_LAMBDA_FUNCTION(APP, urlpattern)
          for method in urlpattern["methods"]:
            self.add_LAMBDA_PERMISSION(APP, urlpattern, method)
    # Resourceを作る
    depends = {}
    for i, apigw in enumerate(settings.AWS["API"]["gateways"]):
      depends[apigw["name"]] = []
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
                ParentId = "!Ref MyResource" + self.resource2index(parent_resource)
              else:
                ParentId = f"!GetAtt MyApiGateway{self.apigw2index(apigw['name'])}.RootResourceId"
              self.add_APIGW_RESOURCE(apigw, resource, ParentId, PathPart=u)
          else:
            # methodを作る
            if resource == "":
              ResourceId = f"!GetAtt MyApiGateway{self.apigw2index(apigw['name'])}.RootResourceId"
            else:
              ResourceId = "!Ref MyResource" + self.resource2index(resource)
            for method in urlpattern["methods"]:
              if urlpattern["integration"].lower() == "s3":
                DIC = urlpattern["function"]()
                method_index = self.add_APIGW_METHOD_S3(apigw, resource, method, ResourceId, DIC)
                depends[apigw["name"]].append(method_index)
              elif urlpattern["integration"].lower() == "lambda":
                method_index = self.add_APIGW_METHOD_LAMBDA(APP, urlpattern, method, ResourceId, apigw, resource)
                depends[apigw["name"]].append(method_index)
              elif urlpattern["integration"].lower() == "cloudfront":
                pass
              else:
                raise ValueError(f"Invalid integration: {urlpattern['integration']}")
    # API Gatewayを追加
    for apigw in settings.AWS["API"]["gateways"]:
      self.add_APIGW(apigw, depends_on_method_index=depends[apigw["name"]])
  def dump_yaml(self):
    with open(self.settings_json["CloudFormation"]["template"], "w") as f:
      f.write(self.YAML)


