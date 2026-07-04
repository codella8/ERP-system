# reports/utils.py
"""
reports/utils.py
--------------
All the real-time aggregation logic for the Reports dashboard lives here so
that views.py stays thin. Every function takes a (start_date, end_date)
pair (inclusive) and pulls straight from the live database - nothing is
cached or pre-computed.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum, Count, F, Q, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce

from daily_sale.models import DailySaleTransaction
from containers.models import Payment, Expense, Inventory_List, Container

ZERO = Decimal("0.00")
MONEY_FIELD = DecimalField(max_digits=24, decimal_places=2)
QUICK_RANGES = ("today", "week", "month", "year")


def parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def get_date_range(request):
    today = date.today()
    quick = request.GET.get("range")
    start_param = parse_date(request.GET.get("start"))
    end_param = parse_date(request.GET.get("end"))

    if start_param and end_param:
        if start_param > end_param:
            start_param, end_param = end_param, start_param
        return start_param, end_param, "custom"

    if quick == "today":
        return today, today, "today"

    if quick == "week":
        start = today - timedelta(days=today.weekday())  # Monday
        return start, today, "week"

    if quick == "year":
        return date(today.year, 1, 1), today, "year"

    if quick == "month":
        return date(today.year, today.month, 1), today, "month"

    # default -> this month
    return date(today.year, today.month, 1), today, "month"

def get_kpis(start_date, end_date):
    sales_qs = DailySaleTransaction.objects.filter(
        date__gte=start_date, date__lte=end_date
    )
    total_sales = sales_qs.aggregate(v=Sum('total'))['v'] or Decimal('0')
    start_str = start_date.strftime('%d-%b-%y')
    end_str = end_date.strftime('%d-%b-%y')
    
    expenses_qs = Expense.objects.filter(
        date__gte=start_str, date__lte=end_str
    )
    total_expenses = expenses_qs.aggregate(v=Sum('amount'))['v'] or Decimal('0')
    cash_in_qs = Payment.objects.filter(
        date__gte=start_str, date__lte=end_str
    )
    total_cash_in = cash_in_qs.aggregate(v=Sum('cash_in'))['v'] or Decimal('0')
    cash_out_qs = Payment.objects.filter(
        date__gte=start_str, date__lte=end_str
    )
    total_cash_out = cash_out_qs.aggregate(v=Sum('cash_out'))['v'] or Decimal('0')
    inventory_qs = Inventory_List.objects.all()
    total_inventory_value = Decimal('0')
    for item in inventory_qs:
        in_stock = item.in_stock_qty - item.total_sold_qty
        total_inventory_value += in_stock * item.unit_price
    
    total_items = inventory_qs.count()
    total_containers = Container.objects.count()
    
    return {
        'total_sales': total_sales,
        'total_expenses': total_expenses,
        'net_profit': total_sales - total_expenses,
        'total_cash_in': total_cash_in,
        'total_cash_out': total_cash_out,
        'total_inventory_value': total_inventory_value,
        'total_items': total_items,
        'total_containers': total_containers,
    }


def get_financial_summary(start_date, end_date):
    
    start_str = start_date.strftime('%d-%b-%y')
    end_str = end_date.strftime('%d-%b-%y')
    sales_by_day = {
        row['date']: row['v']
        for row in DailySaleTransaction.objects.filter(
            date__gte=start_date, date__lte=end_date
        ).values('date').annotate(v=Sum('total'))
    }
    expenses_by_day = {
        row['date']: row['v']
        for row in Expense.objects.filter(
            date__gte=start_str, date__lte=end_str
        ).values('date').annotate(v=Sum('amount'))
    }
    cash_in_by_day = {
        row['date']: row['v']
        for row in Payment.objects.filter(
            date__gte=start_str, date__lte=end_str
        ).values('date').annotate(v=Sum('cash_in'))
    }
    
    cash_out_by_day = {
        row['date']: row['v']
        for row in Payment.objects.filter(
            date__gte=start_str, date__lte=end_str
        ).values('date').annotate(v=Sum('cash_out'))
    }
    all_days = sorted(
        set(sales_by_day) | set(expenses_by_day) | set(cash_in_by_day) | set(cash_out_by_day),
        reverse=True
    )
    
    rows = []
    totals = {'sales': Decimal('0'), 'expenses': Decimal('0'), 
              'profit': Decimal('0'), 'cash_in': Decimal('0'), 'cash_out': Decimal('0')}
    
    for d in all_days:
        sales = sales_by_day.get(d, Decimal('0'))
        expenses = expenses_by_day.get(d, Decimal('0'))
        cash_in = cash_in_by_day.get(d, Decimal('0'))
        cash_out = cash_out_by_day.get(d, Decimal('0'))
        profit = sales - expenses
        
        rows.append({
            'date': d,
            'sales': sales,
            'expenses': expenses,
            'profit': profit,
            'cash_in': cash_in,
            'cash_out': cash_out,
        })
        
        totals['sales'] += sales
        totals['expenses'] += expenses
        totals['profit'] += profit
        totals['cash_in'] += cash_in
        totals['cash_out'] += cash_out
    chart_rows = list(reversed(rows))
    chart_labels = [r['date'].strftime("%d-%b-%y") for r in chart_rows]
    chart_sales = [float(r['sales']) for r in chart_rows]
    chart_expenses = [float(r['expenses']) for r in chart_rows]
    
    return rows, totals, {
        'labels': chart_labels,
        'sales': chart_sales,
        'expenses': chart_expenses,
    }

def get_financial_summary(start_date, end_date):
    # Sales by day
    sales_by_day = {
        row["date"]: row["v"]
        for row in DailySaleTransaction.objects.filter(
            date__gte=start_date, date__lte=end_date
        )
        .values("date")
        .annotate(v=Sum("total"))
    }

    # Expenses by day
    expenses_by_day = {
        row["date"]: row["v"]
        for row in Expense.objects.filter(date__gte=start_date, date__lte=end_date)
        .values("date")
        .annotate(v=Sum("amount"))
    }

    # Cash-In by day
    cash_in_by_day = {
        row["date"]: row["v"]
        for row in Payment.objects.filter(date__gte=start_date, date__lte=end_date)
        .values("date")
        .annotate(v=Sum("cash_in"))
    }

    # Cash-Out by day
    cash_out_by_day = {
        row["date"]: row["v"]
        for row in Payment.objects.filter(date__gte=start_date, date__lte=end_date)
        .values("date")
        .annotate(v=Sum("cash_out"))
    }

    all_days = sorted(
        set(sales_by_day) | set(expenses_by_day) | set(cash_in_by_day) | set(cash_out_by_day),
        reverse=True,
    )

    rows = []
    totals = {"sales": ZERO, "expenses": ZERO, "profit": ZERO, "cash_in": ZERO, "cash_out": ZERO}

    for d in all_days:
        sales = sales_by_day.get(d, ZERO) or ZERO
        expenses = expenses_by_day.get(d, ZERO) or ZERO
        cash_in = cash_in_by_day.get(d, ZERO) or ZERO
        cash_out = cash_out_by_day.get(d, ZERO) or ZERO
        profit = sales - expenses

        rows.append({
            "date": d,
            "sales": sales,
            "expenses": expenses,
            "profit": profit,
            "cash_in": cash_in,
            "cash_out": cash_out,
        })

        totals["sales"] += sales
        totals["expenses"] += expenses
        totals["profit"] += profit
        totals["cash_in"] += cash_in
        totals["cash_out"] += cash_out
        
    chart_rows = list(reversed(rows))
    chart_labels = [r["date"].strftime("%d-%b-%y") for r in chart_rows]
    chart_sales = [float(r["sales"]) for r in chart_rows]
    chart_expenses = [float(r["expenses"]) for r in chart_rows]

    return rows, totals, {
        "labels": chart_labels,
        "sales": chart_sales,
        "expenses": chart_expenses,
    }
def get_inventory_summary():
    items = Inventory_List.objects.select_related("container").all().order_by(
        "container__container_no", "product_name"
    )

    rows = []
    totals = {"in_stock": ZERO, "sold": ZERO, "total_value": ZERO}

    for item in items:
        in_stock = item.in_stock_qty - item.total_sold_qty
        sold = item.total_sold_qty or ZERO
        unit_price = item.unit_price or ZERO
        total_value = in_stock * unit_price

        if in_stock <= 0:
            status = "Out of Stock"
        elif in_stock < 5:
            status = "Low Stock"
        else:
            status = "In Stock"

        rows.append({
            "product": item.product_name,
            "code": item.code,
            "container": item.container.container_no if item.container else "-",
            "in_stock": in_stock,
            "sold": sold,
            "unit_price": unit_price,
            "total_value": total_value,
            "status": status,
        })

        totals["in_stock"] += in_stock
        totals["sold"] += sold
        totals["total_value"] += total_value

    return rows, totals


def get_container_summary(start_date, end_date):
    sales_by_container = {
        row["container"]: row["v"]
        for row in DailySaleTransaction.objects.filter(
            date__gte=start_date,
            date__lte=end_date,
            container__isnull=False,
        )
        .values("container")
        .annotate(v=Sum("total"))
    }

    containers = Container.objects.all().order_by("-created_at")

    rows = []
    totals = {"sales": ZERO, "expenses": ZERO, "profit": ZERO, "items": 0, "inventory_value": ZERO}

    for c in containers:
        sales = sales_by_container.get(c.id, ZERO) or ZERO
        expenses = c.total_expenses or ZERO
        profit = sales - expenses
        items_count = c.inventory_items.count()
        inventory_value = Decimal('0')
        for item in c.inventory_items.all():
            in_stock = item.in_stock_qty - item.total_sold_qty
            inventory_value += in_stock * item.unit_price

        rows.append({
            "name": c.container_no,
            "code": c.code or '-',
            "supplier": c.supplier or '-',
            "sales": sales,
            "expenses": expenses,
            "profit": profit,
            "items": items_count,
            "inventory_value": inventory_value,
        })

        totals["sales"] += sales
        totals["expenses"] += expenses
        totals["profit"] += profit
        totals["items"] += items_count
        totals["inventory_value"] += inventory_value

    return rows, totals