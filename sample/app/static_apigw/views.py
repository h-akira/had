from had.shourtcuts import s3_integration

def css():
  return s3_integration('static/css/{item}', "text/css", ["item"])

def js():
  return s3_integration('static/js/{item}', "text/js", ["item"])
