from django.urls import path
from . import views

urlpatterns = [
    path("", views.organizations_list, name="organizations_list"),
    path("map/", views.organizations_map, name="organizations_map"),
    path("geo-insights/", views.geo_insights, name="geo_insights"),
    path("geo-insights/data/", views.geo_insights_data, name="geo_insights_data"),
    path("geo-insights/export/", views.geo_insights_export, name="geo_insights_export"),
    path("<int:pk>/", views.organization_detail, name="organization_detail"),
]