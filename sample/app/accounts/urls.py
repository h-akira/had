from . import views
from had.urls import path

urlpatterns = [
  path("signup", views.signup, name="signup", methods=["GET", "POST"]),
  path("login", views.login, name="login", methods=["GET", "POST"]),
  path("logout", views.logout, name="logout", methods=["GET"])
]

