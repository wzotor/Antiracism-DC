import csv
import io

from django.contrib import admin, messages
from django.contrib.admin.models import CHANGE, LogEntry as DjangoLogEntry
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import redirect, render
from django.urls import path
from simple_history.admin import SimpleHistoryAdmin

from .forms import OrganizationCSVUploadForm
from .models import ActivityLog, Organization


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    date_hierarchy = "action_time"
    list_display = ("action_time", "user", "content_type", "object_repr", "action_flag")
    list_filter = ("action_flag", "content_type", "user")
    search_fields = ("object_repr", "change_message", "user__username")
    ordering = ("-action_time",)

    readonly_fields = (
        "action_time",
        "user",
        "content_type",
        "object_id",
        "object_repr",
        "action_flag",
        "change_message",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Organization)
class OrganizationAdmin(SimpleHistoryAdmin):
    list_display = ("organization_id", "organization_name", "organization_type", "ward", "zip_code")
    search_fields = ("organization_id", "organization_name", "organization_type", "ward", "zip_code")
    list_filter = ("organization_type", "ward")
    ordering = ("organization_name",)

    change_list_template = "admin/orgs/organization/change_list.html"

    # ----------------------------
    # Role control (Priority 1)
    # ----------------------------
    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return request.user.is_staff

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "upload-csv/",
                self.admin_site.admin_view(self.upload_csv),
                name="orgs_organization_upload_csv",
            ),
        ]
        return custom_urls + urls

    def upload_csv(self, request):
        if not request.user.is_superuser:
            self.message_user(request, "Only superusers can upload CSV files.", level=messages.ERROR)
            return redirect("..")

        # ----------------------------
        # Step 2: Confirm import (SAFE)
        # ----------------------------
        if request.method == "POST" and request.POST.get("confirm_import") == "1":
            rows = request.session.get("org_csv_valid_rows", [])
            filename = request.session.get("org_csv_filename", "organizations.csv")

            if not rows:
                self.message_user(
                    request,
                    "Nothing to import. Please upload the CSV again to preview it.",
                    level=messages.ERROR,
                )
                return redirect("..")

            created_count = 0
            updated_count = 0
            failed_rows = []

            for row in rows:
                try:
                    defaults = row["defaults"]

                    _, created = Organization.objects.update_or_create(
                        organization_id=row["organization_id"],
                        defaults=defaults,
                    )

                    if created:
                        created_count += 1
                    else:
                        updated_count += 1

                except Exception as e:
                    failed_rows.append(
                        {
                            "row_number": row.get("row_number", ""),
                            "organization_id": row.get("organization_id", ""),
                            "organization_name": row.get("organization_name", ""),
                            "organization_type": row.get("organization_type", ""),
                            "reasons": [str(e)],
                        }
                    )

            total_valid = len(rows)
            success_count = created_count + updated_count
            failed_count = len(failed_rows)

            DjangoLogEntry.objects.create(
                user_id=request.user.pk,
                content_type_id=ContentType.objects.get_for_model(Organization).pk,
                object_id="",
                object_repr=f"CSV upload: {filename}",
                action_flag=CHANGE,
                change_message=(
                    f"Import confirmed. Success: {success_count} "
                    f"(Created: {created_count}, Updated: {updated_count}), "
                    f"Failed: {failed_count}, Total attempted: {total_valid}"
                ),
            )

            # Clear session so a refresh does not re-import
            request.session.pop("org_csv_valid_rows", None)
            request.session.pop("org_csv_filename", None)

            # If anything failed, show a clear results page (reuse preview template)
            if failed_rows:
                context = {
                    **self.admin_site.each_context(request),
                    "title": "Import Results (Some rows failed)",
                    "filename": filename,
                    "preview_rows": [],
                    "invalid_rows": failed_rows,
                    "summary": {
                        "total_rows": total_valid,
                        "valid_rows": success_count,
                        "invalid_rows": failed_count,
                    },
                }
                self.message_user(
                    request,
                    f"Import finished. Success: {success_count}. Failed: {failed_count}. See details below.",
                    level=messages.WARNING,
                )
                return render(request, "admin/orgs/organization/upload_preview.html", context)

            self.message_user(
                request,
                f"Import complete. Created: {created_count}, Updated: {updated_count}",
                level=messages.SUCCESS,
            )
            return redirect("..")

        # ----------------------------
        # Step 1: Upload and preview
        # ----------------------------
        if request.method == "POST":
            form = OrganizationCSVUploadForm(request.POST, request.FILES)
            if form.is_valid():
                csv_file = form.cleaned_data["csv_file"]

                if not csv_file.name.lower().endswith(".csv"):
                    self.message_user(request, "Please upload a .csv file.", level=messages.ERROR)
                    return redirect(request.path)

                raw_bytes = csv_file.read()

                decoded = None
                for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
                    try:
                        decoded = raw_bytes.decode(enc)
                        break
                    except UnicodeDecodeError:
                        continue

                if decoded is None:
                    self.message_user(
                        request,
                        "Could not decode this CSV. Please re-save it as UTF-8 CSV and try again.",
                        level=messages.ERROR,
                    )
                    return redirect(request.path)

                reader = csv.DictReader(io.StringIO(decoded))

                valid_rows = []
                invalid_rows = []
                preview_rows = []

                def clean(value):
                    if value is None:
                        return None
                    v = str(value).strip()
                    return v if v else None

                def clean_float(value):
                    v = clean(value)
                    if v is None:
                        return None
                    try:
                        return float(v)
                    except ValueError:
                        return None

                for idx, row in enumerate(reader, start=2):
                    organization_id = clean(row.get("organization_id"))
                    name = clean(row.get("organization_name"))
                    org_type = clean(row.get("organization_type"))

                    reasons = []
                    if not organization_id:
                        reasons.append("Missing organization_id")
                    if not name:
                        reasons.append("Missing organization_name")
                    if not org_type:
                        reasons.append("Missing organization_type")

                    lat_raw = row.get("latitude")
                    lng_raw = row.get("longitude")
                    lat = clean_float(lat_raw)
                    lng = clean_float(lng_raw)

                    if clean(lat_raw) is not None and lat is None:
                        reasons.append("Invalid latitude")
                    if clean(lng_raw) is not None and lng is None:
                        reasons.append("Invalid longitude")

                    if reasons:
                        invalid_rows.append(
                            {
                                "row_number": idx,
                                "organization_id": organization_id,
                                "organization_name": name,
                                "organization_type": org_type,
                                "reasons": reasons,
                            }
                        )
                        continue

                    defaults = {
                        "organization_name": name,
                        "organization_type": org_type,
                        "website": clean(row.get("website")),
                        "address": clean(row.get("address")),
                        "zip_code": clean(row.get("zip_code")),
                        "ward": clean(row.get("ward")),
                        "primary_contact_person": clean(row.get("primary_contact_person")),
                        "contact_person_role": clean(row.get("contact_person_role")),
                        "contact_person_email": clean(row.get("contact_person_email")),
                        "mobile_contact": clean(row.get("mobile_contact")),
                        "anti_racism_focus": clean(row.get("anti_racism_focus")),
                        "primary_anti_racist_engagement_type": clean(
                            row.get("primary_anti_racist_engagement_type")
                        ),
                        "core_organizational_activities": clean(row.get("core_organizational_activities")),
                        "description_of_anti_racist_activities": clean(
                            row.get("description_of_anti_racist_activities")
                        ),
                        "latitude": lat,
                        "longitude": lng,
                    }

                    row_data = {
                        "row_number": idx,
                        "organization_id": organization_id,
                        "organization_name": name,
                        "organization_type": org_type,
                        "ward": defaults["ward"],
                        "zip_code": defaults["zip_code"],
                        "latitude": lat,
                        "longitude": lng,
                        "defaults": defaults,
                    }

                    valid_rows.append(row_data)
                    if len(preview_rows) < 10:
                        preview_rows.append(row_data)

                request.session["org_csv_valid_rows"] = valid_rows
                request.session["org_csv_filename"] = csv_file.name

                context = {
                    **self.admin_site.each_context(request),
                    "title": "Preview Organizations CSV",
                    "filename": csv_file.name,
                    "preview_rows": preview_rows,
                    "invalid_rows": invalid_rows,
                    "summary": {
                        "total_rows": len(valid_rows) + len(invalid_rows),
                        "valid_rows": len(valid_rows),
                        "invalid_rows": len(invalid_rows),
                    },
                }

                return render(request, "admin/orgs/organization/upload_preview.html", context)

        else:
            form = OrganizationCSVUploadForm()

        context = {
            **self.admin_site.each_context(request),
            "form": form,
            "title": "Upload Organizations CSV",
        }
        return render(request, "admin/orgs/organization/upload_csv.html", context)