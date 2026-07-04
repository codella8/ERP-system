# daily_sale/report.py
from decimal import Decimal
from datetime import date, timedelta
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncDay, TruncMonth, TruncWeek
from .models import DailySaleTransaction


def parse_date_param(value):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def get_sales_summary(start_date=None, end_date=None):
    qs = DailySaleTransaction.objects.all()

    if start_date:
        qs = qs.filter(date__gte=start_date)
    if end_date:
        qs = qs.filter(date__lte=end_date)

    agg = qs.aggregate(
        total_sales=Sum("sales"),
        total_discount=Sum("discount"),
        total_paid=Sum("paid"),
        total_qty=Sum("qty"),
        transactions_count=Count("id"),
    )

    total_sales = agg["total_sales"] or Decimal("0.00")
    total_discount = agg["total_discount"] or Decimal("0.00")
    total_paid = agg["total_paid"] or Decimal("0.00")
    total_qty = agg["total_qty"] or 0
    transactions_count = agg["transactions_count"] or 0
    net_total = total_sales - total_discount
    if net_total < 0:
        net_total = Decimal("0.00")
    total_balance = net_total - total_paid
    if total_balance < 0:
        total_balance = Decimal("0.00")
    paid_count = qs.filter(payment_status="paid").count()
    partial_count = qs.filter(payment_status="partial").count()
    unpaid_count = qs.filter(payment_status="unpaid").count()

    return {
        "total_sales": total_sales,
        "total_discount": total_discount,
        "net_total": net_total,
        "total_paid": total_paid,
        "total_balance": total_balance,
        "total_qty": total_qty,
        "transactions_count": transactions_count,
        "paid_count": paid_count,
        "partial_count": partial_count,
        "unpaid_count": unpaid_count,
    }


def get_sales_summary_by_code(start_date=None, end_date=None):
    qs = DailySaleTransaction.objects.all()

    if start_date:
        qs = qs.filter(date__gte=start_date)
    if end_date:
        qs = qs.filter(date__lte=end_date)

    summary = qs.values("code").annotate(
        total_sales=Sum("sales"),
        total_discount=Sum("discount"),
        total_paid=Sum("paid"),
        total_qty=Sum("qty"),
        transaction_count=Count("id"),
        not_sold=Count("id", filter=Q(sales=0) | Q(qty=0)),
    ).order_by("code")

    for item in summary:
        item["net_total"] = (item["total_sales"] or Decimal("0")) - (item["total_discount"] or Decimal("0"))
        if item["net_total"] < 0:
            item["net_total"] = Decimal("0")

    return list(summary)


def get_sales_summary_by_customer(start_date=None, end_date=None, limit=20):
    qs = DailySaleTransaction.objects.exclude(customer_name__isnull=True).exclude(customer_name="")

    if start_date:
        qs = qs.filter(date__gte=start_date)
    if end_date:
        qs = qs.filter(date__lte=end_date)

    summary = qs.values("customer_name").annotate(
        total_sales=Sum("sales"),
        total_discount=Sum("discount"),
        total_paid=Sum("paid"),
        total_qty=Sum("qty"),
        transaction_count=Count("id"),
    ).order_by("-total_sales")[:limit]

    for customer in summary:
        customer["net_total"] = (customer["total_sales"] or Decimal("0")) - (customer["total_discount"] or Decimal("0"))
        if customer["net_total"] < 0:
            customer["net_total"] = Decimal("0")
        if customer["net_total"] > 0:
            customer["paid_percentage"] = ((customer["total_paid"] or Decimal("0")) / customer["net_total"] * 100).quantize(Decimal("0.01"))
        else:
            customer["paid_percentage"] = Decimal("0")

    return list(summary)


def sales_timeseries(start_date=None, end_date=None, group_by="day"):
    qs = DailySaleTransaction.objects.all()

    if start_date:
        qs = qs.filter(date__gte=start_date)
    if end_date:
        qs = qs.filter(date__lte=end_date)

    if group_by == "month":
        series = (
            qs.annotate(month=TruncMonth("date"))
            .values("month")
            .annotate(
                total_sales=Sum("sales"),
                total_discount=Sum("discount"),
                total_paid=Sum("paid"),
                total_qty=Sum("qty"),
                transaction_count=Count("id"),
            )
            .order_by("month")
        )
    elif group_by == "week":
        series = (
            qs.annotate(week=TruncWeek("date"))
            .values("week")
            .annotate(
                total_sales=Sum("sales"),
                total_discount=Sum("discount"),
                total_paid=Sum("paid"),
                total_qty=Sum("qty"),
                transaction_count=Count("id"),
            )
            .order_by("week")
        )
    else:
        series = (
            qs.annotate(day=TruncDay("date"))
            .values("day")
            .annotate(
                total_sales=Sum("sales"),
                total_discount=Sum("discount"),
                total_paid=Sum("paid"),
                total_qty=Sum("qty"),
                transaction_count=Count("id"),
            )
            .order_by("day")
        )

    result = []
    for item in series:
        net_total = (item["total_sales"] or Decimal("0")) - (item["total_discount"] or Decimal("0"))
        if net_total < 0:
            net_total = Decimal("0")
        
        result.append({
            "date": item.get("day") or item.get("week") or item.get("month"),
            "total_sales": item["total_sales"] or Decimal("0"),
            "total_discount": item["total_discount"] or Decimal("0"),
            "net_total": net_total,
            "total_paid": item["total_paid"] or Decimal("0"),
            "total_qty": item["total_qty"] or 0,
            "transaction_count": item["transaction_count"] or 0,
        })

    return result


def get_payment_status_summary(start_date=None, end_date=None):
    qs = DailySaleTransaction.objects.all()

    if start_date:
        qs = qs.filter(date__gte=start_date)
    if end_date:
        qs = qs.filter(date__lte=end_date)

    summary = qs.values("payment_status").annotate(
        count=Count("id"),
        total_sales=Sum("sales"),
        total_paid=Sum("paid"),
        total_balance=Sum("balance"),
        total_qty=Sum("qty"),
    ).order_by("payment_status")

    result = {
        "paid": {"count": 0, "total_sales": Decimal("0"), "total_paid": Decimal("0"), "total_balance": Decimal("0"), "total_qty": 0},
        "partial": {"count": 0, "total_sales": Decimal("0"), "total_paid": Decimal("0"), "total_balance": Decimal("0"), "total_qty": 0},
        "unpaid": {"count": 0, "total_sales": Decimal("0"), "total_paid": Decimal("0"), "total_balance": Decimal("0"), "total_qty": 0},
    }

    for item in summary:
        status = item["payment_status"]
        if status in result:
            result[status]["count"] = item["count"] or 0
            result[status]["total_sales"] = item["total_sales"] or Decimal("0")
            result[status]["total_paid"] = item["total_paid"] or Decimal("0")
            result[status]["total_balance"] = item["total_balance"] or Decimal("0")
            result[status]["total_qty"] = item["total_qty"] or 0

    return result


def get_daily_report(date_obj=None):
    if date_obj is None:
        date_obj = date.today()

    transactions = DailySaleTransaction.objects.filter(date=date_obj).order_by("-created_at")

    agg = transactions.aggregate(
        total_sales=Sum("sales"),
        total_discount=Sum("discount"),
        total_paid=Sum("paid"),
        total_qty=Sum("qty"),
        transaction_count=Count("id"),
    )

    total_sales = agg["total_sales"] or Decimal("0")
    total_discount = agg["total_discount"] or Decimal("0")
    net_total = total_sales - total_discount
    if net_total < 0:
        net_total = Decimal("0")

    return {
        "date": date_obj,
        "total_sales": total_sales,
        "total_discount": total_discount,
        "net_total": net_total,
        "total_paid": agg["total_paid"] or Decimal("0"),
        "total_qty": agg["total_qty"] or 0,
        "transaction_count": agg["transaction_count"] or 0,
        "transactions": transactions,
        "code_summary": get_sales_summary_by_code(date_obj, date_obj),
    }