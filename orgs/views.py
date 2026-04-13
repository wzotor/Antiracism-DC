import json
import os
from datetime import date

from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string

from .models import Organization


@login_required
def organizations_list(request):
    qs = Organization.objects.all()

    # Optional filters
    org_type = request.GET.get("organization_type", "").strip()
    ward = request.GET.get("ward", "").strip()
    focus = request.GET.get("anti_racism_focus", "").strip()

    if org_type:
        qs = qs.filter(organization_type__icontains=org_type)
    if ward:
        qs = qs.filter(ward__icontains=ward)
    if focus:
        qs = qs.filter(anti_racism_focus__icontains=focus)

    context = {
        "organizations": qs,
        "filters": {
            "organization_type": org_type,
            "ward": ward,
            "anti_racism_focus": focus,
        },
    }
    return render(request, "orgs/organizations_list.html", context)


@login_required
def organization_detail(request, pk):
    org = get_object_or_404(Organization, pk=pk)
    return render(request, "orgs/organization_detail.html", {"org": org})


@login_required
def organizations_map(request):
    qs = Organization.objects.all().order_by("organization_name")

    organizations = []
    for o in qs:
        organizations.append(
            {
                # keep id for future use (detail links, etc.)
                "id": o.id,

                # use the same keys your template expects
                "organization_id": o.organization_id,
                "organization_name": o.organization_name,
                "organization_type": o.organization_type,
                "ward": o.ward,
                "zip_code": o.zip_code,
                "address": o.address,
                "website": o.website or "",

                "primary_anti_racist_engagement_type": o.primary_anti_racist_engagement_type,
                "core_organizational_activities": o.core_organizational_activities,
                "description_of_anti_racist_activities": o.description_of_anti_racist_activities,

                # IMPORTANT: these names must match the template: latitude / longitude
                "latitude": o.latitude,
                "longitude": o.longitude,
            }
        )

    return render(request, "orgs/organizations_map.html", {"organizations": organizations})


def _build_org_geo_data():
    """Return a list of org dicts suitable for the geo insights map."""
    qs = Organization.objects.exclude(latitude=None).exclude(longitude=None)
    data = []
    for o in qs:
        data.append({
            "organization_name": o.organization_name or "",
            "organization_type": o.organization_type or "",
            "address": o.address or "",
            "ward": o.ward or "",
            "website": o.website or "",
            "anti_racism_focus": o.anti_racism_focus or "",
            "primary_anti_racist_engagement_type": o.primary_anti_racist_engagement_type or "",
            "latitude": o.latitude,
            "longitude": o.longitude,
        })
    return data


def _load_ward_geojson():
    path = os.path.join(settings.BASE_DIR, "orgs", "static", "geo", "dc_wards.geojson")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@login_required
def geo_insights(request):
    org_data = _build_org_geo_data()
    context = {
        "org_data_json": json.dumps(org_data),
    }
    return render(request, "orgs/geo_insights.html", context)


@login_required
def geo_insights_export(request):
    org_data = _build_org_geo_data()
    ward_geojson = _load_ward_geojson()
    html = render_to_string("orgs/geo_insights_export.html", {
        "org_data_json": json.dumps(org_data),
        "ward_geojson_json": json.dumps(ward_geojson),
        "export_date": date.today().strftime("%B %d, %Y"),
    }, request=request)
    response = HttpResponse(html, content_type="text/html")
    response["Content-Disposition"] = 'attachment; filename="geo_insights.html"'
    return response