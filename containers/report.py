from django.db.models import Sum, Count, F, Q,Avg
from .models import Container, Inventory_List, ContainerTransaction

def container_inventory_summary(company_id=None):
    """خلاصه موجودی کانتینرها"""
    qs = Container.objects.all()
    if company_id:
        qs = qs.filter(company_id=company_id)

    qs = qs.annotate(
        products_count=Count('inventory_items', distinct=True),  # ✅ اصلاح شد
        total_in_stock_qty=Sum('inventory_items__in_stock_qty'),
        total_inventory_value=Sum(F('inventory_items__in_stock_qty') * F('inventory_items__unit_price'))
    ).values(
        'id', 'container_number', 'products_count', 'total_in_stock_qty', 'total_inventory_value'
    )
    return qs


def container_financial_summary(container_id=None, company_id=None, start_date=None, end_date=None):
    """خلاصه مالی یک کانتینر"""
    tx_qs = ContainerTransaction.objects.all()  # ✅ از ContainerTransaction استفاده کن
    
    if container_id:
        tx_qs = tx_qs.filter(container_id=container_id)
    if company_id:
        tx_qs = tx_qs.filter(container__company_id=company_id)  # ✅ از container__company_id استفاده کن
    if start_date:
        tx_qs = tx_qs.filter(created_at__gte=start_date)
    if end_date:
        tx_qs = tx_qs.filter(created_at__lte=end_date)

    summary = tx_qs.aggregate(
        total_income=Sum('total_price', filter=Q(sale_status__in=['sold_to_company', 'sold_to_customer'])),
        total_expenses=Sum('total_price', filter=Q(sale_status='purchase')),  # ✅ اگه purchase داری
        total_transactions=Count('id'),
        total_sold_qty=Sum('quantity'),
        avg_transaction_value=Avg('total_price'),  # ✅ میانگین
    )
    
    # اضافه کردن سود خالص
    summary['net_profit'] = (summary['total_income'] or 0) - (summary['total_expenses'] or 0)
    
    return summary


def total_container_transactions_report(company_id=None, start_date=None, end_date=None):
    """گزارش کلی تراکنش‌های کانتینرها"""
    tx_qs = ContainerTransaction.objects.select_related('container').all()  # ✅ از ContainerTransaction استفاده کن
    
    if company_id:
        tx_qs = tx_qs.filter(container__company_id=company_id)
    if start_date:
        tx_qs = tx_qs.filter(created_at__gte=start_date)
    if end_date:
        tx_qs = tx_qs.filter(created_at__lte=end_date)

    # گروه‌بندی بر اساس وضعیت‌ها
    return tx_qs.values(
        'sale_status', 
        'transport_status', 
        'payment_status'
    ).annotate(
        total_amount=Sum('total_price'),
        total_quantity=Sum('quantity'),
        transaction_count=Count('id')
    ).order_by('-total_amount')


def container_transactions_detail(container_id, start_date=None, end_date=None):
    """جزئیات تراکنش‌های یک کانتینر"""
    tx_qs = ContainerTransaction.objects.filter(container_id=container_id)
    
    if start_date:
        tx_qs = tx_qs.filter(created_at__gte=start_date)
    if end_date:
        tx_qs = tx_qs.filter(created_at__lte=end_date)
    
    return tx_qs.order_by('-created_at')

def inventory_summary(container_id=None, company_id=None):
    """خلاصه کلی موجودی"""
    qs = Inventory_List.objects.all()
    
    if container_id:
        qs = qs.filter(container_id=container_id)
    if company_id:
        qs = qs.filter(container__company_id=company_id)
    
    summary = qs.aggregate(
        total_items=Count('id'),
        total_qty=Sum('in_stock_qty'),
        total_sold_qty=Sum('total_sold_qty'),
        total_value=Sum(F('in_stock_qty') * F('unit_price')),
        avg_price=Avg('unit_price'),
    )
    
    # محاسبه موجودی فعلی
    summary['in_stock'] = (summary['total_qty'] or 0) - (summary['total_sold_qty'] or 0)
    
    return summary


def inventory_by_status(company_id=None):
    """گزارش موجودی بر اساس وضعیت"""
    qs = Inventory_List.objects.all()
    if company_id:
        qs = qs.filter(container__company_id=company_id)
    
    return qs.values('status').annotate(
        count=Count('id'),
        total_qty=Sum('in_stock_qty'),
        total_sold=Sum('total_sold_qty'),
        total_value=Sum(F('in_stock_qty') * F('unit_price'))
    ).order_by('status')


def inventory_by_container(company_id=None):
    """گزارش موجودی بر اساس کانتینر"""
    qs = Inventory_List.objects.select_related('container').all()
    if company_id:
        qs = qs.filter(container__company_id=company_id)
    
    return qs.values(
        'container__id', 
        'container__container_number'
    ).annotate(
        items_count=Count('id'),
        total_qty=Sum('in_stock_qty'),
        total_sold=Sum('total_sold_qty'),
        total_value=Sum(F('in_stock_qty') * F('unit_price'))
    ).order_by('-total_value')


def low_stock_items(threshold=10, company_id=None):
    """گزارش آیتم‌های کم موجود"""
    qs = Inventory_List.objects.all()
    if company_id:
        qs = qs.filter(container__company_id=company_id)
    
    # محاسبه موجودی فعلی و فیلتر
    items = []
    for item in qs:
        in_stock = item.in_stock
        if in_stock <= threshold:
            items.append({
                'id': item.id,
                'product_name': item.product_name,
                'code': item.code,
                'container': item.container.container_number if item.container else None,
                'in_stock': in_stock,
                'total_qty': item.in_stock_qty,
                'unit_price': item.unit_price,
                'status': item.status,
            })
    
    return sorted(items, key=lambda x: x['in_stock'])