from django import forms


class OrganizationCSVUploadForm(forms.Form):
    csv_file = forms.FileField(
        widget=forms.ClearableFileInput(
            attrs={
                "accept": ".csv,text/csv",
            }
        )
    )