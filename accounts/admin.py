# accounts/admin.py
import csv
from django.contrib import admin
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from . import models

User = get_user_model()
def export_as_csv(fields):
    """Reusable export action"""
    def export(modeladmin, queryset):
        model = modeladmin.model._meta
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename={model.model_name}.csv'
        writer = csv.writer(response)

        writer.writerow(fields)

        for obj in queryset:
            row = []
            for f in fields:
                value = obj
                for part in f.split("__"):
                    value = getattr(value, part, "")
                row.append(str(value))
            writer.writerow(row)

        return response

    export.short_description = "Export selected as CSV"
    return export

def verify_profiles(modeladmin, request, queryset):
    updated = queryset.update(is_verified=True)
    modeladmin.message_user(request, f"{updated} profiles marked as verified.")

verify_profiles.short_description = "Mark selected profiles as verified"


def deactivate_profiles(modeladmin, request, queryset):
    updated = queryset.update(is_active=False)
    modeladmin.message_user(request, f"{updated} profiles deactivated.")

deactivate_profiles.short_description = "Deactivate selected profiles"

@admin.register(models.Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name']