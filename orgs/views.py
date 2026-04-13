import csv
import json
import os
import time
import urllib.parse
import urllib.request
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.db.models import Count
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from .forms import OrganizationForm
from .models import Organization


# ── Geocoding ─────────────────────────────────────────────────────────────────

def geocode_address(address):
    """
    Look up lat/lng for an address using Nominatim (OpenStreetMap).
    Returns (lat, lng) floats on success, (None, None) on failure.
    Rate-limit: Nominatim allows 1 req/sec; callers should respect this.
    """
    if not address or not address.strip():
        return None, None

    query = address.strip()
    # Append DC context if not already present to improve accuracy
    if "washington" not in query.lower() and "dc" not in query.lower():
        query = f"{query}, Washington, DC"

    encoded = urllib.parse.quote(query)
    url = f"https://nominatim.openstreetmap.org/search?q={encoded}&format=json&limit=1&countrycodes=us"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "AntiracismDC/1.0 (contact@antiracismdc.org)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        pass
    return None, None


# ── Helpers ───────────────────────────────────────────────────────────────────

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


# ── Dashboard ─────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    total_orgs   = Organization.objects.count()
    mapped_orgs  = Organization.objects.exclude(latitude=None).exclude(longitude=None).count()
    wards_covered = (
        Organization.objects
        .exclude(ward=None).exclude(ward="")
        .values("ward").distinct().count()
    )

    by_type = list(
        Organization.objects
        .exclude(organization_type=None).exclude(organization_type="")
        .values("organization_type")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    by_ward = list(
        Organization.objects
        .exclude(ward=None).exclude(ward="")
        .values("ward")
        .annotate(count=Count("id"))
        .order_by("ward")
    )
    by_engagement = list(
        Organization.objects
        .exclude(primary_anti_racist_engagement_type=None)
        .exclude(primary_anti_racist_engagement_type="")
        .values("primary_anti_racist_engagement_type")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    by_focus = list(
        Organization.objects
        .exclude(anti_racism_focus=None).exclude(anti_racism_focus="")
        .values("anti_racism_focus")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    context = {
        "total_orgs":      total_orgs,
        "mapped_orgs":     mapped_orgs,
        "wards_covered":   wards_covered,
        "org_types_count": len(by_type),
        "by_ward_json":       json.dumps(by_ward),
        "by_type_json":       json.dumps(by_type),
        "by_engagement_json": json.dumps(by_engagement),
        "by_focus_json":      json.dumps(by_focus),
    }
    return render(request, "orgs/dashboard.html", context)


# ── Organizations list ────────────────────────────────────────────────────────

@login_required
def organizations_list(request):
    qs = Organization.objects.all()

    org_type = request.GET.get("organization_type", "").strip()
    ward     = request.GET.get("ward", "").strip()
    focus    = request.GET.get("anti_racism_focus", "").strip()

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


# ── CSV export ────────────────────────────────────────────────────────────────

@login_required
def organizations_export_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="organizations_{date.today().strftime("%Y%m%d")}.csv"'
    )

    fieldnames = [
        "organization_id", "organization_name", "organization_type",
        "website", "address", "zip_code", "ward",
        "primary_contact_person", "contact_person_role",
        "contact_person_email", "mobile_contact",
        "anti_racism_focus", "primary_anti_racist_engagement_type",
        "core_organizational_activities", "description_of_anti_racist_activities",
        "latitude", "longitude",
    ]

    writer = csv.DictWriter(response, fieldnames=fieldnames)
    writer.writeheader()

    for o in Organization.objects.all().order_by("organization_name"):
        writer.writerow({f: getattr(o, f) or "" for f in fieldnames})

    return response


# ── Organization detail ───────────────────────────────────────────────────────

@login_required
def organization_detail(request, pk):
    org = get_object_or_404(Organization, pk=pk)
    return render(request, "orgs/organization_detail.html", {"org": org})


# ── Organization create ───────────────────────────────────────────────────────

@login_required
def organization_create(request):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "You do not have permission to add organizations.")
        return redirect("organizations_list")

    geocoded_msg = None

    if request.method == "POST":
        form = OrganizationForm(request.POST)
        if form.is_valid():
            org = form.save(commit=False)

            # Auto-geocode if address provided but coordinates are missing
            if org.address and (org.latitude is None or org.longitude is None):
                lat, lng = geocode_address(org.address)
                if lat and lng:
                    org.latitude  = lat
                    org.longitude = lng
                    geocoded_msg  = f"Coordinates auto-filled from address: {lat:.5f}, {lng:.5f}"

            org.save()
            messages.success(request, f'"{org.organization_name}" was created successfully.')
            return redirect("organization_detail", pk=org.pk)
    else:
        form = OrganizationForm()

    return render(request, "orgs/organization_form.html", {
        "form": form,
        "geocoded_msg": geocoded_msg,
    })


# ── Organization edit ─────────────────────────────────────────────────────────

@login_required
def organization_update(request, pk):
    org = get_object_or_404(Organization, pk=pk)

    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "You do not have permission to edit organizations.")
        return redirect("organization_detail", pk=pk)

    geocoded_msg = None
    prev_address = org.address

    if request.method == "POST":
        form = OrganizationForm(request.POST, instance=org)
        if form.is_valid():
            org = form.save(commit=False)

            # Re-geocode if address changed and coordinates are now missing
            address_changed = org.address != prev_address
            missing_coords  = org.latitude is None or org.longitude is None
            if org.address and (missing_coords or address_changed):
                lat, lng = geocode_address(org.address)
                if lat and lng:
                    org.latitude  = lat
                    org.longitude = lng
                    geocoded_msg  = f"Coordinates updated from address: {lat:.5f}, {lng:.5f}"

            org.save()
            messages.success(request, f'"{org.organization_name}" was updated successfully.')
            return redirect("organization_detail", pk=org.pk)
    else:
        form = OrganizationForm(instance=org)

    return render(request, "orgs/organization_form.html", {
        "form": form,
        "geocoded_msg": geocoded_msg,
    })


# ── Map ───────────────────────────────────────────────────────────────────────

@login_required
def organizations_map(request):
    qs = Organization.objects.all().order_by("organization_name")

    organizations = []
    for o in qs:
        organizations.append(
            {
                "id": o.id,
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
                "latitude": o.latitude,
                "longitude": o.longitude,
            }
        )

    return render(request, "orgs/organizations_map.html", {"organizations": organizations})


# ── Geo Insights ──────────────────────────────────────────────────────────────

@login_required
def geo_insights(request):
    return render(request, "orgs/geo_insights.html")


@login_required
def geo_insights_data(request):
    return JsonResponse(_build_org_geo_data(), safe=False)


@login_required
def geo_insights_export(request):
    org_data     = _build_org_geo_data()
    ward_geojson = _load_ward_geojson()
    html = render_to_string("orgs/geo_insights_export.html", {
        "org_data_json":    json.dumps(org_data),
        "ward_geojson_json": json.dumps(ward_geojson),
        "export_date":      date.today().strftime("%B %d, %Y"),
    }, request=request)
    response = HttpResponse(html, content_type="text/html")
    response["Content-Disposition"] = 'attachment; filename="geo_insights.html"'
    return response
