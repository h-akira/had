import re

def path(url, function=None, name=None, methods=['GET'], role=None, integration="lambda", login_required=False, apigw=0):
  if name is None:
    raise ValueError('name is required')
  # 大文字に変換
  methods = [method.upper() for method in methods]
  # チェック
  for method in methods:
    if method not in ['GET', 'POST']:
      raise ValueError('Invalid method: {}'.format(method))
  if integration.lower() not in ['lambda', 's3', 'cloudfront']:
    raise ValueError('Invalid integration: {}'.format(integration))
  return {
    'url': url,
    'function': function,
    'name': name,
    'methods': methods,
    'role':role,
    'integration':integration,
    'login_required':login_required,
    'apigw':apigw  # int型ならリストの番号、str柄ならnameを取る
  }

def urlpatterns_checker(urlpatterns):
  pattern = r'\{.*?\}'
  urls = [ re.sub(pattern, '{}', i["url"]) for i in urlpatterns ]
  print(re.sub(pattern, '{}', "/hello/{aaa}/{bbb}"))
  names = [ i["name"] for i in urlpatterns ]
  # 重複チェック
  if len(urls) != len(set(urls)):
    raise ValueError('Duplicate url: {}'.format(urls))
  if len(names) != len(set(names)):
    raise ValueError('Duplicate name: {}'.format(names))
  return True
