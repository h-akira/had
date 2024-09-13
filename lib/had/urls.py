import re

def path(url, function=None, name=None, methods=['GET'], role=None, integration="lambda", login_required=False):
  if name is None:
    raise ValueError('name is required')
  # 大文字に変換
  methods = [method.upper() for method in methods]
  # チェック
  for method in methods:
    if method not in ['GET', 'POST']:
      raise ValueError('Invalid method: {}'.format(method))
  if integration.lower() not in ['lambda', 's3', 'cloudformation']:
    raise ValueError('Invalid integration: {}'.format(integration))
  # if integration == 's3' and path is None:
  #   raise ValueError('bucket_key is required')
  # if integration == 'lambda' and function is None:
  #   raise ValueError('function is required')
  return {
    'url': url,
    'function': function,
    'name': name,
    'methods': methods,
    'role':role,
    'integration':integration,
    'login_required':login_required,
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

# urlpatterns = [
#   path('/hello/{aaa}/{bbb}', 'hello', 'hello', ['GET']),
#   path('/world', 'world', 'world', ['POST']),
# ]
#
# urlpatterns_checker(urlpatterns)
