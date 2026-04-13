from django.conf import settings
from django.contrib.admin.models import LogEntry
from django.db import models
from simple_history.models import HistoricalRecords


class Organization(models.Model):
    organization_id = models.CharField(max_length=100, unique=True, db_index=True)

    organization_name = models.CharField(max_length=255)
    organization_type = models.CharField(max_length=255)

    website = models.URLField(blank=True, null=True)

    address = models.TextField(blank=True, null=True)
    zip_code = models.CharField(max_length=20, blank=True, null=True)
    ward = models.CharField(max_length=20, blank=True, null=True)

    primary_contact_person = models.CharField(max_length=255, blank=True, null=True)
    contact_person_role = models.CharField(max_length=255, blank=True, null=True)
    contact_person_email = models.EmailField(blank=True, null=True)
    mobile_contact = models.CharField(max_length=50, blank=True, null=True)

    anti_racism_focus = models.TextField(blank=True, null=True)
    primary_anti_racist_engagement_type = models.CharField(max_length=255, blank=True, null=True)

    core_organizational_activities = models.TextField(blank=True, null=True)
    description_of_anti_racist_activities = models.TextField(blank=True, null=True)

    latitude = models.FloatField(blank=True, null=True, verbose_name="Latitude")
    longitude = models.FloatField(blank=True, null=True, verbose_name="Longitude")

    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["organization_name"]

    def __str__(self):
        return self.organization_name


class OrganizationUploadLog(models.Model):
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="org_csv_uploads",
    )

    filename = models.CharField(max_length=255, blank=True, null=True)

    total_rows = models.PositiveIntegerField(default=0)
    valid_rows = models.PositiveIntegerField(default=0)
    invalid_rows = models.PositiveIntegerField(default=0)

    created_count = models.PositiveIntegerField(default=0)
    updated_count = models.PositiveIntegerField(default=0)
    skipped_count = models.PositiveIntegerField(default=0)

    notes = models.TextField(blank=True, null=True)
    error_report = models.JSONField(blank=True, null=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        who = self.uploaded_by.username if self.uploaded_by else "Unknown"
        return f"Org CSV upload by {who} at {self.uploaded_at:%Y-%m-%d %H:%M}"


class ActivityLog(LogEntry):
    class Meta:
        proxy = True
        app_label = "orgs"
        verbose_name = "Activity log"
        verbose_name_plural = "Activity logs"