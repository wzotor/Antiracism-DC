from django.urls import path
from . import views

urlpatterns = [
    path("", views.organizations_list, name="organizations_list"),
    path("map/", views.organizations_map, name="organizations_map"),
    path("<int:pk>/", views.organization_detail, name="organization_detail"),
]