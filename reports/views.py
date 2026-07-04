# reports/views.py
import csv
import json

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render

from . import utils


@login_required
def dashboard(request):
    start_date, end_date, active_range = utils.get_date_range(request)

    kpis = utils.get_kpis(start_date, end_date)
    financial_rows, financial_totals, chart_data = utils.get_financial_summary(start_date, end_date)
    inventory_rows, inventory_totals = utils.get_inventory_summary()
    container_rows, container_totals = utils.get_container_summary(start_date, end_date)

    context = {
        "start_date": start_date,
        "end_date": end_date,
        "active_range": active_range,
        "kpis": kpis,
        "financial_rows": financial_rows,
        "financial_totals": financial_totals,
        "inventory_rows": inventory_rows,
        "inventory_totals": inventory_totals,
        "container_rows": container_rows,
        "container_totals": container_totals,
        "chart_labels": json.dumps(chart_data["labels"]),
        "chart_sales": json.dumps(chart_data["sales"]),
        "chart_expenses": json.dumps(chart_data["expenses"]),
    }
    return render(request, "inout/dashboard.html", context)


@login_required
def export_csv(request):
    start_date, end_date, _ = utils.get_date_range(request)

    financial_rows, financial_totals, _ = utils.get_financial_summary(start_date, end_date)
    inventory_rows, inventory_totals = utils.get_inventory_summary()
    container_rows, container_totals = utils.get_container_summary(start_date, end_date)

    response = HttpResponse(content_type="text/csv")
    filename = f"report_{start_date}_to_{end_date}.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)

    writer.writerow([f"Reports ({start_date} to {end_date})"])
    writer.writerow([])

    writer.writerow(["Financial Summary"])
    writer.writerow(["Date", "Sales (AED)", "Expenses (AED)", "Profit (AED)", "Cash-In (AED)", "Cash-Out (AED)"])
    for r in financial_rows:
        writer.writerow([
            r["date"].strftime("%d-%b-%y"), 
            float(r["sales"]), 
            float(r["expenses"]), 
            float(r["profit"]), 
            float(r["cash_in"]), 
            float(r["cash_out"]),
        ])
    writer.writerow([
        "TOTAL", 
        float(financial_totals["sales"]), 
        float(financial_totals["expenses"]),
        float(financial_totals["profit"]), 
        float(financial_totals["cash_in"]), 
        float(financial_totals["cash_out"]),
    ])
    writer.writerow([])

    writer.writerow(["Inventory Summary"])
    writer.writerow(["Product", "Code", "Container", "In Stock", "Sold", "Unit Price (AED)", "Total Value (AED)", "Status"])
    for r in inventory_rows:
        writer.writerow([
            r["product"], r["code"], r["container"], 
            int(r["in_stock"]), int(r["sold"]),
            float(r["unit_price"]), float(r["total_value"]), r["status"],
        ])
    writer.writerow([
        "TOTAL", "", "", 
        int(inventory_totals["in_stock"]), 
        int(inventory_totals["sold"]), 
        "", 
        float(inventory_totals["total_value"]), 
        "",
    ])
    writer.writerow([])

    writer.writerow(["Container Summary"])
    writer.writerow(["Container", "Code", "Supplier", "Sales (AED)", "Expenses (AED)", "Profit (AED)", "Items", "Inventory Value (AED)"])
    for r in container_rows:
        writer.writerow([
            r["name"], r["code"], r["supplier"], 
            float(r["sales"]), float(r["expenses"]),
            float(r["profit"]), r["items"], float(r["inventory_value"]),
        ])
    writer.writerow([
        "TOTAL", "", "", 
        float(container_totals["sales"]), 
        float(container_totals["expenses"]),
        float(container_totals["profit"]), 
        container_totals["items"], 
        float(container_totals["inventory_value"]),
    ])

    return response