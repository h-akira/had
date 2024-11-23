import os
from http.cookies import SimpleCookie

def reverse(app_name, **kwargs):
  import importlib
  from project import settings
  if app_name.count(":") != 1:
    raise ValueError("App name should be in the format `app_name:url_name`")
  app, name = app_name.split(":")
  for APP in settings.APPS:
    if APP["name"] == app:
      app_url = APP["url"]
      break
  else:
    raise ValueError(f"App `{app}` does not exist")
  urls = importlib.import_module(f"{app}.urls")
  for urlpattern in urls.urlpatterns:
    if urlpattern["name"] == name:
      return "/" + os.path.join(settings.MAPPING_PATH, app_url, urlpattern["url"].format(**kwargs))
  else:
    raise ValueError(f"URL `{name}` does not exist in app `{app}`")

def redirect(app_name, set_cookie=None, **kwargs):
  if set_cookie:
    return {
      "statusCode": 302,
      "headers": {
        "Location": reverse(app_name, **kwargs),
        # "Set-Cookie": set_cookie
      },
      "multiValueHeaders": {
        "Set-Cookie": set_cookie
      }
    }
  else:
    return {
      "statusCode": 302,
      "headers": {
        "Location": reverse(app_name, **kwargs)
      }
    }

class RenderSettings:
  import jinja2
  templates_dir = "/opt/templates"
  env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(templates_dir)
  )
  env.filters['url'] = reverse

def json_render(request, body, code=200):
  import json
  if request.refresh:
    # CookieにJWTトークンをセット
    return {
      "statusCode": code,
      "headers": {
        "Content-Type": "application/json; charset=UTF-8"
      },
      "multiValueHeaders": {
        "Set-Cookie": request.get_cookies_to_refresh()
      },
      "body": json.dumps(body)
    }
  else:
    return {
      "statusCode": code,
      "headers": {
        "Content-Type": "application/json; charset=UTF-8"
      },
      "body": json.dumps(body)
    }

def image_render(request, image_body, content_type, isBase64Encoded=False, reflesh=False):
  import json
  if request.refresh and reflesh:
    # CookieにJWTトークンをセット
    return {
      "statusCode": 200,
      "headers": {
        "Content-Type": content_type
      },
      "multiValueHeaders": {
        "Set-Cookie": request.get_cookies_to_refresh()
      },
      # "body": json.dumps(image_body),
      "body": image_body,
      "isBase64Encoded": isBase64Encoded
    }
  else:
    return {
      "statusCode": 200,
      "headers": {
        "Content-Type": content_type
      },
      # "body": json.dumps(image_body),
      "body": image_body,
      "isBase64Encoded": isBase64Encoded
    }

def render(request, template, context={}):
  template = RenderSettings.env.get_template(template)
  if "request" not in context.keys():
    context["request"] = request
  if request.refresh:
    # CookieにJWTトークンをセット
    return {
      "statusCode": 200,
      "headers": {
        "Content-Type": "text/html; charset=UTF-8"
      },
      "multiValueHeaders": {
        "Set-Cookie": request.get_cookies_to_refresh()
      },
      "body": template.render(**context)
    }
  else:
    return {
      "statusCode": 200,
      "headers": {
        "Content-Type": "text/html; charset=UTF-8"
      },
      "body": template.render(**context)
    }

def s3_integration(path, content_type="text/html", parameters=[]):
  if parameters.__class__ != list:
    parameters = [parameters]
  return {
    "path": path,  # settings.pyで設定したkey/integration/このpath
    "content_type": content_type,  # デフォルトはtext/html
    "parameters": parameters  # リストで指定
  }

def error_render(request=None, error_message=None):
  from project import settings
  if settings.DEBUG:
    error_html= """\
<h1>Error</h1>
<h3>Error Message</h3>
{error_message}
<h3>event</h3>
{event}
<h3>Context</h3>
{context}
"""
    if not request:
      return {
        "statusCode": 500,
        "headers": {
          "Content-Type": "text/html; charset=UTF-8"
        },
        "body": error_html.format(error_message=error_message, event="None", context="None")
      }
    else:
      return {
        "statusCode": 500,
        "headers": {
          "Content-Type": "text/html; charset=UTF-8"
        },
        "body": error_html.format(error_message=error_message, event=request.event, context=request.context)
      }
  else:
    error_html= """\
<h1>Error</h1>
<p>Sorry, an error occurred.</p>
<p>Please try again later, or contact the administrator.</p>
"""
    return {
      "statusCode": 500,
      "headers": {
        "Content-Type": "text/html; charset=UTF-8"
      },
      "body": error_html
    }


