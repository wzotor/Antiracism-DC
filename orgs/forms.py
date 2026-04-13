from django import forms

from .models import Organization


class OrganizationCSVUploadForm(forms.Form):
    csv_file = forms.FileField(
        widget=forms.ClearableFileInput(
            attrs={
                "accept": ".csv,text/csv",
            }
        )
    )


class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = [
            "organization_id",
            "organization_name",
            "organization_type",
            "website",
            "address",
            "zip_code",
            "ward",
            "latitude",
            "longitude",
            "primary_contact_person",
            "contact_person_role",
            "contact_person_email",
            "mobile_contact",
            "anti_racism_focus",
            "primary_anti_racist_engagement_type",
            "core_organizational_activities",
            "description_of_anti_racist_activities",
        ]
        widgets = {
            "organization_id": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. ORG-001"}),
            "organization_name": forms.TextInput(attrs={"class": "form-control"}),
            "organization_type": forms.TextInput(attrs={"class": "form-control"}),
            "website": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "zip_code": forms.TextInput(attrs={"class": "form-control"}),
            "ward": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Ward 5"}),
            "latitude": forms.NumberInput(attrs={"class": "form-control", "step": "any", "placeholder": "e.g. 38.9072"}),
            "longitude": forms.NumberInput(attrs={"class": "form-control", "step": "any", "placeholder": "e.g. -77.0369"}),
            "primary_contact_person": forms.TextInput(attrs={"class": "form-control"}),
            "contact_person_role": forms.TextInput(attrs={"class": "form-control"}),
            "contact_person_email": forms.EmailInput(attrs={"class": "form-control"}),
            "mobile_contact": forms.TextInput(attrs={"class": "form-control"}),
            "anti_racism_focus": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "primary_anti_racist_engagement_type": forms.TextInput(attrs={"class": "form-control"}),
            "core_organizational_activities": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "description_of_anti_racist_activities": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }
