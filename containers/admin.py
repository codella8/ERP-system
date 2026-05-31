# containers/admin.py
from django.contrib import admin
from .models import Container, Inventory_List, ContainerTransaction
from django.http import HttpResponse
import csv
from django.utils.translation import gettext_lazy as _

@admin.register(Container)
class ContainerAdmin(admin.ModelAdmin):
    list_display = ("container_number", "name", "company", "price", "created_at")
    search_fields = ("container_number", "name", "company__name")
    list_filter = ("company",)
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
    actions = ["export_selected_csv"]
 
    def export_selected_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="containers.csv"'
        writer = csv.writer(response)
        writer.writerow(['Container Number', 'Name', 'Company', 'Price', 'Created At'])
        for obj in queryset:
            writer.writerow([
                obj.container_number,
                obj.name,
                obj.company.name if obj.company else '',
                obj.price,
                obj.created_at.strftime('%Y-%m-%d %H:%M')
            ])
        return response
    export_selected_csv.short_description = "Export selected containers to CSV"

@admin.register(Inventory_List)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ("product_name", "code", "container", "in_stock_qty", "unit_price", "price", "date_added")
    search_fields = ("product_name", "code", "container__container_number")
    list_filter = ("container", "date_added")
    readonly_fields = ("total_sold_qty", "total_sold_count")
    ordering = ("-date_added",)
    list_per_page = 50

    def export_selected_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=inventory.csv"
        writer = csv.writer(response)
        writer.writerow(["id","code","product_name","container","in_stock_qty","unit_price","price","date_added"])
        for obj in queryset:
            writer.writerow([str(obj.id), obj.code, obj.product_name, str(obj.container or ""), str(obj.in_stock_qty), str(obj.unit_price), str(obj.price), obj.date_added.isoformat()])
        return response
    export_selected_csv.short_description = _("Export selected inventory")


@admin.register(ContainerTransaction)
class ContainerTransactionAdmin(admin.ModelAdmin):
    list_display = ("container", "product", "quantity", "sale_status", "transport_status", "payment_status", "created_at")
    list_filter = ("sale_status", "transport_status", "payment_status", "arrival_date")
    search_fields = ("container__container_number", "product", "customer__user__username")
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"