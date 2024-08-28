class Form:
  def __init__(self, fields):
    if fields.__class__ != dict:
      raise ValueError('fields must be dict')
    self.fields = fields
    for key, value in fields.items():
      if value.name is None:
        value.name = key
      elif key != value.name:
        raise ValueError(f'{key} is not {value.name}')
    # 例
    # fields = {
    #   "field_name": CharField(name="field_name", max_length=255, initial=None, tag_stile=None, tag_class=None, tag_value=None)
    # }
    # form = Form(fields)
  def set_initials(self, initials):
    if initials.__class__ != dict:
      raise ValueError('initials must be dict')
    for key, value in initials.items():
      if key in self.fields.keys():
        self.fields[key].tag_value = value
      else:
        raise ValueError(f'{key} is not in fields')

class CharField:
  def __init__(self, name=None, max_length=127, required=True, tag_style=None, tag_class=None, tag_value=None):
    self.name = name
    self.max_length = max_length
    self.required = required
    self.tag_style = tag_style
    self.tag_class = tag_class
    self.tag_value = tag_value
  def html(self):
    if self.name is None:
      raise ValueError('name must be set')
    if self.required:
      required = ' required'
    else:
      required = ''
    if self.tag_style is not None:
      tag_style = f' style="{self.style}"'
    else:
      tag_style = ''
    if self.tag_class is not None:
      tag_class = f' class="{self.tag_class}"'
    else:
      tag_class = ''
    if self.tag_value is not None:
      tag_value = f' value="{self.tag_value}"'
    else:
      tag_value = ''
    templates = '<input type="text" name="{name}" maxlength="{max_length}" id="id_{name}"{required}{tag_style}{tag_class}{tag_value}>'
    return templates.format(
      name=self.name, 
      max_length=self.max_length, 
      required=required, 
      tag_style=tag_style, 
      tag_class=tag_class, 
      tag_value=tag_value
    )

# form = Form(
#   fields={
#     'test': CharField(max_length=255),
#     'test2': CharField(max_length=255, required=False, tag_class='test_class', tag_value='test_value')
#   }
# )
# print(form.fields["test"].html())
# print(form.fields["test2"].html())



