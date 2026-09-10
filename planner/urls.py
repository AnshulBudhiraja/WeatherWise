from django.urls import path
from . import views


urlpatterns = [
    path("", views.home, name="home"),
    path("api/plan/", views.plan_trip, name="plan_trip"),
]
