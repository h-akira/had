from . import views
from had.urls import path

# app_name = "test"

urlpatterns = [
  path("css/{item}", views.css, name="css", methods=["GET"], integration="s3"),
  path("js/{item}", views.js, name="js", methods=["GET"], integration="s3"),
]
