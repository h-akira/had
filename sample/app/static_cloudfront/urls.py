from had.urls import path

urlpatterns = [
  path("css/{item}", name="css", integration="cloudfront"),
  path("js/{item}", name="js", integration="cloudfront"),
  path("images/{item}", name="images", integration="cloudfront")
]
