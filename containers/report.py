# containers/report.py
from decimal import Decimal
from django.db.models import Sum, Count, F, Q, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Container, Inventory_List
from daily_sale.models import DailySaleTransaction
from expenses.models import Expense  # اگر اپ expenses دارید


# ============================================
# گزارش‌های مربوط به کانتینرها
# ============================================

def container_inventory_summary(container_id=None):
    """
    خلاصه موجودی کانتینرها
    returns: لیست دیکشنری با فیلدهای id, container_no, code, items_count, total_in_stock, total_inventory_value
    """
    qs = Container.objects.all()
    
    if container_id:
        qs = qs.filter(id=container_id)
    
    summary = []
    for container in qs:
        # محاسبه مستقیم از inventory_items
        inventory_qs = container.inventory_items.all()
        
        items_count = inventory_qs.count()
        total_in_stock = sum(item.in_stock for item in inventory_qs)
        total_inventory_value = sum(item.current_value for item in inventory_qs)
        
        summary.append({
            'id': str(container.id),
            'container_no': container.container_no,
            'code': container.code,
            'supplier': container.supplier,
            'items_count': items_count,
            'total_in_stock': total_in_stock,
            'total_inventory_value': float(total_inventory_value),
            'arrival_date': container.arrival_date,
        })
    
    return summary


def container_financial_summary(container_id=None, start_date=None, end_date=None):
    """
    خلاصه مالی یک کانتینر بر اساس DailySaleTransaction
    returns: دیکشنری با total_sales, total_expenses, net_profit, transaction_count, total_qty_sold
    """
    # فیلتر تراکنش‌های فروش
    sales_qs = DailySaleTransaction.objects.all()
    
    if container_id:
        sales_qs = sales_qs.filter(container_id=container_id)
    if start_date:
        sales_qs = sales_qs.filter(date__gte=start_date)
    if end_date:
        sales_qs = sales_qs.filter(date__lte=end_date)
    
    # آمار فروش
    sales_stats = sales_qs.aggregate(
        total_sales=Sum('total'),
        total_paid=Sum('paid'),
        total_discount=Sum('discount'),
        total_qty=Sum('qty'),
        transaction_count=Count('id'),
    )
    
    total_sales = sales_stats['total_sales'] or Decimal('0')
    total_paid = sales_stats['total_paid'] or Decimal('0')
    total_discount = sales_stats['total_discount'] or Decimal('0')
    total_balance = total_sales - total_paid
    
    # هزینه‌های مرتبط با کانتینر (از اپ expenses)
    expenses_total = Decimal('0')
    if container_id:
        expenses_total = Expense.objects.filter(
            container_id=container_id
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # اگر کانتینر مشخص نبود، هزینه‌ها را نمی‌شود محاسبه کرد
    if not container_id:
        expenses_total = None
    
    return {
        'total_sales': float(total_sales),
        'total_paid': float(total_paid),
        'total_balance': float(total_balance),
        'total_discount': float(total_discount),
        'total_expenses': float(expenses_total) if expenses_total is not None else None,
        'net_profit': float(total_sales - expenses_total) if expenses_total is not None else None,
        'total_qty_sold': int(sales_stats['total_qty'] or 0),
        'transaction_count': sales_stats['transaction_count'] or 0,
    }


def container_daily_sales_report(container_id, date=None):
    """
    گزارش فروش روزانه یک کانتینر خاص
    returns: لیست تراکنش‌های آن روز + مجموع
    """
    if date is None:
        date = timezone.now().date()
    
    transactions = DailySaleTransaction.objects.filter(
        container_id=container_id,
        date=date
    ).select_related('item').order_by('-created_at')
    
    total_sales = transactions.aggregate(total=Sum('total'))['total'] or Decimal('0')
    total_qty = transactions.aggregate(total=Sum('qty'))['total'] or 0
    
    return {
        'date': date,
        'transactions': transactions,
        'total_sales': float(total_sales),
        'total_qty': total_qty,
        'count': transactions.count(),
    }


def container_monthly_summary(container_id=None, year=None, month=None):
    """
    گزارش خلاصه ماهانه فروش کانتینرها
    returns: لیست روزهای ماه با مجموع فروش هر روز
    """
    if year is None:
        year = timezone.now().year
    if month is None:
        month = timezone.now().month
    
    # ساخت محدوده تاریخ
    start_date = datetime(year, month, 1).date()
    if month == 12:
        end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
    else:
        end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
    
    # فیلتر فروش‌ها
    qs = DailySaleTransaction.objects.filter(
        date__gte=start_date,
        date__lte=end_date
    )
    
    if container_id:
        qs = qs.filter(container_id=container_id)
    
    # گروه‌بندی بر اساس روز
    daily_summary = qs.values('date').annotate(
        total_sales=Sum('total'),
        total_qty=Sum('qty'),
        transaction_count=Count('id')
    ).order_by('date')
    
    return {
        'year': year,
        'month': month,
        'start_date': start_date,
        'end_date': end_date,
        'daily_summary': list(daily_summary),
        'total_month_sales': qs.aggregate(total=Sum('total'))['total'] or 0,
        'total_month_qty': qs.aggregate(total=Sum('qty'))['total'] or 0,
    }


def all_containers_performance_report(start_date=None, end_date=None):
    """
    گزارش عملکرد همه کانتینرها (مقایسه‌ای)
    returns: لیست کانتینرها با total_sales, total_expenses, net_profit, items_count
    """
    containers = Container.objects.all()
    
    report = []
    for container in containers:
        # فروش کانتینر
        sales_qs = DailySaleTransaction.objects.filter(container=container)
        if start_date:
            sales_qs = sales_qs.filter(date__gte=start_date)
        if end_date:
            sales_qs = sales_qs.filter(date__lte=end_date)
        
        total_sales = sales_qs.aggregate(total=Sum('total'))['total'] or Decimal('0')
        
        # موجودی کانتینر
        inventory_value = container.total_inventory_value
        
        report.append({
            'id': str(container.id),
            'container_no': container.container_no,
            'code': container.code,
            'supplier': container.supplier,
            'total_sales': float(total_sales),
            'total_expenses': float(container.total_expenses or 0),
            'net_profit': float(total_sales - (container.total_expenses or 0)),
            'inventory_value': float(inventory_value),
            'items_count': container.inventory_items.count(),
        })
    
    # مرتب‌سازی بر اساس سود خالص (بیشترین اول)
    report.sort(key=lambda x: x['net_profit'], reverse=True)
    
    return report


# ============================================
# گزارش‌های مربوط به موجودی (Inventory)
# ============================================

def inventory_summary(container_id=None):
    """
    خلاصه کلی موجودی
    returns: دیکشنری با total_items, total_in_stock, total_sold, total_value, avg_price
    """
    qs = Inventory_List.objects.select_related('container')
    
    if container_id:
        qs = qs.filter(container_id=container_id)
    
    total_items = qs.count()
    total_in_stock_qty = 0
    total_sold_qty = 0
    total_value = Decimal('0')
    total_price_sum = Decimal('0')
    
    for item in qs:
        in_stock = item.in_stock
        total_in_stock_qty += in_stock
        total_sold_qty += item.total_sold_qty
        item_value = in_stock * item.unit_price
        total_value += item_value
        total_price_sum += item.unit_price
    
    avg_price = total_price_sum / total_items if total_items > 0 else Decimal('0')
    
    return {
        'total_items': total_items,
        'total_in_stock': total_in_stock_qty,
        'total_sold': total_sold_qty,
        'total_value': float(total_value),
        'avg_price': float(avg_price),
    }


def inventory_by_container():
    """
    گزارش موجودی بر اساس کانتینر
    returns: لیست کانتینرها با خلاصه موجودی
    """
    containers = Container.objects.prefetch_related('inventory_items').all()
    
    report = []
    for container in containers:
        items = container.inventory_items.all()
        total_in_stock = sum(item.in_stock for item in items)
        total_value = sum(item.current_value for item in items)
        
        report.append({
            'container_id': str(container.id),
            'container_no': container.container_no,
            'code': container.code,
            'items_count': items.count(),
            'total_in_stock': total_in_stock,
            'total_value': float(total_value),
        })
    
    return report


def low_stock_items(threshold=10):
    """
    گزارش آیتم‌های کم موجود (موجودی کمتر یا مساوی آستانه)
    returns: لیست آیتم‌های با موجودی کم
    """
    items = Inventory_List.objects.select_related('container').all()
    
    low_stock = []
    for item in items:
        in_stock = item.in_stock
        if in_stock <= threshold:
            low_stock.append({
                'id': str(item.id),
                'product_name': item.product_name,
                'code': item.code,
                'container': item.container.container_no if item.container else None,
                'in_stock': in_stock,
                'unit_price': float(item.unit_price),
                'total_value': float(in_stock * item.unit_price),
            })
    
    return sorted(low_stock, key=lambda x: x['in_stock'])


def top_selling_items(limit=10, start_date=None, end_date=None):
    """
    گزارش پرفروش‌ترین آیتم‌ها بر اساس DailySaleTransaction
    returns: لیست آیتم‌ها با مجموع فروش و تعداد
    """
    qs = DailySaleTransaction.objects.filter(item__isnull=False)
    
    if start_date:
        qs = qs.filter(date__gte=start_date)
    if end_date:
        qs = qs.filter(date__lte=end_date)
    
    top_items = qs.values('item_id', 'item__product_name', 'item__code').annotate(
        total_sales=Sum('total'),
        total_qty=Sum('qty'),
        transaction_count=Count('id')
    ).order_by('-total_sales')[:limit]
    
    result = []
    for item in top_items:
        result.append({
            'item_id': str(item['item_id']) if item['item_id'] else None,
            'product_name': item['item__product_name'],
            'code': item['item__code'],
            'total_sales': float(item['total_sales'] or 0),
            'total_qty': int(item['total_qty'] or 0),
            'transaction_count': item['transaction_count'],
        })
    
    return result


# ============================================
# گزارش‌های ترکیبی و داشبورد
# ============================================

def dashboard_summary():
    """
    خلاصه کلی برای داشبورد اصلی
    returns: دیکشنری با آمار کلی
    """
    # آمار کانتینرها
    total_containers = Container.objects.count()
    
    # آمار فروش (از DailySale)
    sales_stats = DailySaleTransaction.objects.aggregate(
        total_sales=Sum('total'),
        total_paid=Sum('paid'),
        total_discount=Sum('discount'),
        total_transactions=Count('id'),
        total_qty=Sum('qty'),
    )
    
    total_sales = sales_stats['total_sales'] or Decimal('0')
    total_paid = sales_stats['total_paid'] or Decimal('0')
    total_discount = sales_stats['total_discount'] or Decimal('0')
    
    # آمار موجودی
    inventory_stats = inventory_summary()
    
    # ۵ کانتینر برتر از نظر فروش
    top_containers = all_containers_performance_report()[:5]
    
    return {
        'total_containers': total_containers,
        'total_sales': float(total_sales),
        'total_paid': float(total_paid),
        'total_balance': float(total_sales - total_paid),
        'total_discount': float(total_discount),
        'total_transactions': sales_stats['total_transactions'] or 0,
        'total_items_sold': int(sales_stats['total_qty'] or 0),
        'inventory_stats': inventory_stats,
        'top_containers': top_containers,
    }