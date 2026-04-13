from django.contrib import admin
from django.urls import include, path
from django.http import HttpResponse


# Admin branding (safe to set here, not in settings.py)
admin.site.site_header = "Anti-racism-DC Admin"
admin.site.site_title = "Anti-racism-DC Admin"
admin.site.index_title = "System Administration"


def home(request):
    return HttpResponse("Anti-racism-DC is running.")


urlpatterns = [
    path("admin/", admin.site.urls),

    # Django authentication
    path("accounts/", include("django.contrib.auth.urls")),

    # App routes
    path("", include("orgs.urls")),
]