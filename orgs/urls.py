from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("organizations/", views.organizations_list, name="organizations_list"),
    path("organizations/new/", views.organization_create, name="organization_create"),
    path("organizations/export/csv/", views.organizations_export_csv, name="organizations_export_csv"),
    path("organizations/<int:pk>/", views.organization_detail, name="organization_detail"),
    path("organizations/<int:pk>/edit/", views.organization_update, name="organization_update"),
    path("map/", views.organizations_map, name="organizations_map"),
    path("geo-insights/", views.geo_insights, name="geo_insights"),
    path("geo-insights/data/", views.geo_insights_data, name="geo_insights_data"),
    path("geo-insights/export/", views.geo_insights_export, name="geo_insights_export"),
]
