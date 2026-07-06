# containers/views.py
from decimal import Decimal
import logging
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum, Count
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
import json
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import Container, Inventory_List
from daily_sale.models import DailySaleTransaction
import csv
from django.http import HttpResponse, JsonResponse

logger = logging.getLogger(__name__)


@login_required
def container_list(request):
    """صفحه اصلی لیست کانتینرها با تمام محاسبات خودکار"""
    
    # دریافت پارامترهای فیلتر
    search = request.GET.get('search', '').strip()
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # کوئری پایه
    containers = Container.objects.all().order_by('-arrival_date', '-created_at')
    
    # اعمال فیلترها
    if search:
        containers = containers.filter(
            Q(container_no__icontains=search) |
            Q(supplier__icontains=search) |
            Q(code__icontains=search)
        )
    
    if date_from:
        containers = containers.filter(arrival_date__gte=date_from)
    if date_to:
        containers = containers.filter(arrival_date__lte=date_to)
    
    # محاسبه آمار برای هر کانتینر (از DailySaleTransaction)
    container_data = []
    total_items_count = 0
    total_inventory_value = Decimal('0')
    total_sales_sum = Decimal('0')
    total_expenses_sum = Decimal('0')
    
    for container in containers:
        # محاسبه فروش از DailySale
        sales_total = DailySaleTransaction.objects.filter(
            container=container
        ).aggregate(total=Sum('total'))['total'] or Decimal('0')
        
        # به‌روزرسانی خودکار total_sales اگر تغییر کرده باشد
        if container.total_sales != sales_total:
            container.total_sales = sales_total
            container.save(update_fields=['total_sales'])
        
        # ارزش موجودی کانتینر
        inventory_value = Decimal('0')
        items_count = 0
        for item in container.inventory_items.all():
            items_count += 1
            # فرض می‌کنیم current_value یک property است
            inventory_value += item.current_value if hasattr(item, 'current_value') else (item.in_stock_qty * item.unit_price)
        
        total_items_count += items_count
        total_inventory_value += inventory_value
        total_sales_sum += container.total_sales or 0
        total_expenses_sum += container.total_expenses or 0
        
        container_data.append({
            'id': container.id,
            'container_no': container.container_no,
            'supplier': container.supplier,
            'code': container.code,
            'arrival_date': container.arrival_date,
            'total_sales': container.total_sales,
            'total_expenses': container.total_expenses,
            'net_value': (container.total_sales or 0) - (container.total_expenses or 0),
            'items_count': items_count,
            'inventory_value': inventory_value,
        })
    
    # صفحه‌بندی
    paginator = Paginator(container_data, 25)
    page_number = request.GET.get('page', 1)
    
    try:
        page_obj = paginator.page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)
    
    # آمار کارت‌ها
    total_containers = containers.count()
    
    context = {
        'containers': page_obj.object_list,
        'page_obj': page_obj,
        'paginator': paginator,
        'is_paginated': paginator.num_pages > 1,
        'total_containers': total_containers,
        'total_items': total_items_count,
        'total_value': total_inventory_value,
        'total_sales': total_sales_sum,
        'total_expenses': total_expenses_sum,
        'search': search,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'container/container_list.html', context)


# containers/views.py

@login_required
def container_detail(request, pk):
    """صفحه جزئیات کانتینر با اطلاعات کامل"""
    container = get_object_or_404(Container, pk=pk)
    
    # به‌روزرسانی total_sales از DailySale
    sales_total = DailySaleTransaction.objects.filter(
        container=container
    ).aggregate(total=Sum('total'))['total'] or Decimal('0')
    
    if container.total_sales != sales_total:
        container.total_sales = sales_total
        container.save(update_fields=['total_sales', 'updated_at'])
    
    # موجودی کانتینر
    inventory_items = container.inventory_items.select_related().all()
    
    # محاسبه ارزش کل موجودی
    inventory_total_value = Decimal('0')
    for item in inventory_items:
        # ✅ محاسبه موجودی فعلی
        current_stock = item.in_stock_qty - item.total_sold_qty
        # ✅ محاسبه ارزش آیتم
        item_value = current_stock * item.unit_price
        inventory_total_value += item_value
        
        # ✅ اضافه کردن به object برای استفاده در قالب
        item.current_stock = current_stock
        item.item_value = item_value
    
    # تراکنش‌های فروش مرتبط با این کانتینر
    sales_transactions = DailySaleTransaction.objects.filter(
        container=container
    ).select_related('item', 'created_by').order_by('-date', '-created_at')
    
    # آمار فروش کانتینر
    sales_stats = sales_transactions.aggregate(
        total_sales=Sum('total'),
        total_paid=Sum('paid'),
        total_discount=Sum('discount'),
        total_qty=Sum('qty'),
        transaction_count=Count('id')
    )
    
    context = {
        'container': container,
        'inventory_items': inventory_items,
        'inventory_total_value': inventory_total_value,
        'sales_transactions': sales_transactions,
        'sales_stats': {
            'total_sales': sales_stats['total_sales'] or 0,
            'total_paid': sales_stats['total_paid'] or 0,
            'total_discount': sales_stats['total_discount'] or 0,
            'total_qty': sales_stats['total_qty'] or 0,
            'transaction_count': sales_stats['transaction_count'] or 0,
        },
    }
    
    return render(request, 'container/container_detail.html', context)


# containers/views.py

@login_required
def inventory_list(request):
    """صفحه لیست موجودی"""
    items = Inventory_List.objects.select_related('container').all().order_by('-created_at')
    
    # فیلتر جستجو
    search = request.GET.get('search', '')
    if search:
        items = items.filter(
            Q(product_name__icontains=search) |
            Q(code__icontains=search) |
            Q(container__container_no__icontains=search)
        )
    
    # فیلتر بر اساس کانتینر
    container_id = request.GET.get('container', '')
    if container_id:
        items = items.filter(container_id=container_id)
    
    # محاسبه مقادیر برای هر آیتم
    item_data = []
    total_in_stock = 0
    total_sold = 0
    total_value = Decimal('0')
    
    for item in items:
        # محاسبه موجودی فعلی
        current_stock = item.in_stock_qty - item.total_sold_qty
        
        # ارزش کل
        item_value = current_stock * item.unit_price
        
        total_in_stock += current_stock
        total_sold += item.total_sold_qty
        total_value += item_value
        
        item_data.append({
            'id': item.id,
            'product_name': item.product_name,
            'code': item.code,
            'container': item.container,
            'container_no': item.container.container_no if item.container else '',
            'in_stock_qty': item.in_stock_qty,
            'total_sold_qty': item.total_sold_qty,
            'current_stock': current_stock,
            'unit_price': item.unit_price,
            'total_value': item_value,
        })
    
    # ✅ لیست کانتینرها برای فیلتر (این خط را اضافه کن)
    containers = Container.objects.all().order_by('container_no')
    
    context = {
        'items': item_data,
        'containers': containers,  # ✅ این خط مهم است
        'search': search,
        'container_filter': container_id,
        'stats': {
            'total_items': items.count(),
            'total_in_stock': total_in_stock,
            'total_sold': total_sold,
            'total_value': total_value,
        }
    }
    
    return render(request, 'container/inventory_list.html', context)


@login_required
@require_POST
def container_create_ajax(request):
    try:
        container_no = request.POST.get('container_no', '').strip() 
        supplier = request.POST.get('supplier', '').strip()
        code = request.POST.get('code', '').strip()
        arrival_date = request.POST.get('arrival_date', '').strip()
        
        print("=== DEBUG CREATE CONTAINER ===")
        print(f"container_no: {container_no}")
        print(f"supplier: {supplier}")
        print(f"code: {code}")
        print(f"arrival_date: {arrival_date}")
        
        if not container_no:
            return JsonResponse({'success': False, 'error': 'Container number is required'})
        
        # بررسی تکراری نبودن
        if Container.objects.filter(container_no=container_no).exists():
            return JsonResponse({'success': False, 'error': 'Container number already exists'})
        
        # ایجاد کانتینر جدید
        container = Container.objects.create(
            container_no=container_no,
            supplier=supplier if supplier else '',
            code=code if code else None,
            arrival_date=arrival_date if arrival_date else None,
        )
        
        print(f"Container created: {container.id}")
        
        return JsonResponse({
            'success': True,
            'id': str(container.id),
            'container_no': container.container_no,
            'supplier': container.supplier,
            'code': container.code,
            'arrival_date': container.arrival_date,
            'message': 'Container created successfully'
        })
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})



@require_GET
def container_get_ajax(request, pk):
    """دریافت اطلاعات یک کانتینر برای ویرایش"""
    try:
        container = get_object_or_404(Container, pk=pk)
        return JsonResponse({
            'success': True,
            'container': {
                'id': str(container.id),
                'supplier': container.supplier,
                'container_no': container.container_no,
                'code': container.code,
                'arrival_date': container.arrival_date,
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# containers/views.py
@require_POST
def container_update_ajax(request, pk):
    try:
        container = get_object_or_404(Container, pk=pk)
        data = json.loads(request.body)
        
        if 'container_no' in data:
            container.container_no = data['container_no']
        if 'supplier' in data:
            container.supplier = data['supplier']
        if 'code' in data:
            container.code = data['code']
        if 'arrival_date' in data:
            container.arrival_date = data['arrival_date']
        
        container.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Container updated successfully'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_POST
def container_delete_ajax(request, pk):
    """حذف کانتینر"""
    try:
        container = get_object_or_404(Container, pk=pk)
        container_no = container.container_no
        container.delete()
        return JsonResponse({'success': True, 'message': f'Container {container_no} deleted'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_POST
def inventory_update_ajax(request, pk):
    """به‌روزرسانی آیتم موجودی"""
    try:
        item = get_object_or_404(Inventory_List, pk=pk)
        data = json.loads(request.body)
        
        if 'product_name' in data:
            item.product_name = data['product_name']
        if 'code' in data:
            item.code = data['code'] or None
        if 'in_stock_qty' in data:
            item.in_stock_qty = Decimal(str(data['in_stock_qty']))
        if 'total_sold_qty' in data:
            item.total_sold_qty = Decimal(str(data['total_sold_qty']))
        if 'unit_price' in data:
            item.unit_price = Decimal(str(data['unit_price']))
        
        item.save()
        
        return JsonResponse({'success': True, 'message': 'Item updated'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_POST
def inventory_delete_ajax(request, pk):
    """حذف آیتم موجودی"""
    try:
        item = get_object_or_404(Inventory_List, pk=pk)
        item.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_GET
def export_containers_csv(request):
    """خروجی CSV از کانتینرها"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="containers_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Container No.', 'Supplier', 'Code', 'Arrival Date', 'Total Sales', 'Total Expenses', 'Net Value'])
    
    containers = Container.objects.all().order_by('-arrival_date')
    for c in containers:
        writer.writerow([
            c.container_no,
            c.supplier or '',
            c.code or '',
            c.arrival_date or '',
            # ❌ حذف c.get_transport_status_display()
            float(c.total_sales or 0),
            float(c.total_expenses or 0),
            float((c.total_sales or 0) - (c.total_expenses or 0)),
        ])
    
    return response

@login_required
@require_GET
def container_stats_api(request):
    """API برای آمار لحظه‌ای کانتینرها"""
    container_id = request.GET.get('container_id')
    
    if container_id:
        container = get_object_or_404(Container, pk=container_id)
        sales_total = DailySaleTransaction.objects.filter(container=container).aggregate(total=Sum('total'))['total'] or 0
        
        data = {
            'id': str(container.id),
            'container_no': container.container_no,
            'total_sales': float(sales_total),
            'total_expenses': float(container.total_expenses or 0),
            'net_value': float(sales_total - (container.total_expenses or 0)),
        }
    else:
        containers = Container.objects.all()
        total_sales = 0
        total_expenses = 0
        
        for c in containers:
            sales = DailySaleTransaction.objects.filter(container=c).aggregate(total=Sum('total'))['total'] or 0
            total_sales += float(sales)
            total_expenses += float(c.total_expenses or 0)
        
        data = {
            'total_sales': total_sales,
            'total_expenses': total_expenses,
            'total_net': total_sales - total_expenses,
            'container_count': containers.count(),
        }
    
    return JsonResponse({'success': True, 'data': data})


@login_required
@require_POST
def inventory_create_ajax(request):
    """ایجاد آیتم موجودی جدید"""
    try:
        product_name = request.POST.get('product_name', '').strip()
        if not product_name:
            return JsonResponse({'success': False, 'error': 'Product name is required'})
        
        container_id = request.POST.get('container')
        container = None
        if container_id:
            container = get_object_or_404(Container, id=container_id)
        
        item = Inventory_List.objects.create(
            product_name=product_name,
            code=request.POST.get('code', '').strip() or None,
            in_stock_qty=Decimal(request.POST.get('in_stock_qty', 0)),
            unit_price=Decimal(request.POST.get('unit_price', 0)),
            container=container
        )
        
        return JsonResponse({
            'success': True,
            'id': str(item.id),
            'product_name': item.product_name,
            'code': item.code,
            'in_stock_qty': float(item.in_stock_qty),
            'unit_price': float(item.unit_price),
            'container_no': item.container.container_no if item.container else '',
            'message': 'Item created successfully'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

import csv
from decimal import Decimal
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST, require_GET
from django.db.models import Sum, Q
import json

from .models import Container, Inventory_List, Payment
from employee.models import Person

@login_required
def payment_list(request):
    """صفحه لیست پرداخت‌ها (مثل اکسل)"""
    # ❌ این خط را حذف کن
    # from .models import PaymentCategory
    
    payments = Payment.objects.select_related('container').all().order_by('-date')
    
    # فیلترها
    search = request.GET.get('search', '').strip()
    if search:
        payments = payments.filter(
            Q(description__icontains=search) |
            Q(paid_by__icontains=search) |
            Q(received_by__icontains=search)
        )
    
    date_from = request.GET.get('date_from')
    if date_from:
        payments = payments.filter(date__gte=date_from)
    
    date_to = request.GET.get('date_to')
    if date_to:
        payments = payments.filter(date__lte=date_to)
    
    # محاسبه مجموع
    total_cash_in = payments.aggregate(total=Sum('cash_in'))['total'] or Decimal('0')
    total_cash_out = payments.aggregate(total=Sum('cash_out'))['total'] or Decimal('0')
    net_balance = total_cash_in - total_cash_out
    
    # دریافت لیست کانتینرها برای فیلتر
    containers = Container.objects.all().order_by('container_no')
    
    context = {
        'payments': payments,
        'total_cash_in': total_cash_in,
        'total_cash_out': total_cash_out,
        'net_balance': net_balance,
        'containers': containers,
        'search': search,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'container/payment.html', context)

# containers/views.py - اضافه کن

@login_required
@require_POST
def payment_create_ajax(request):
    """ایجاد Payment جدید با AJAX"""
    try:
        payment = Payment.objects.create(
            date=request.POST.get('date', ''),
            description=request.POST.get('description', ''),
            rate=Decimal(request.POST.get('rate', 0)),
            nzd=Decimal(request.POST.get('nzd', 0)),
            paid_by=request.POST.get('paid_by', ''),
            received_by=request.POST.get('received_by', ''),
            cash_in=Decimal(request.POST.get('cash_in', 0)),
            cash_out=Decimal(request.POST.get('cash_out', 0)),
            container_id=request.POST.get('container') or None,
        )
        
        # اگر Payment مربوط به کانتینر است، total_expenses را به‌روز کن
        if payment.container and payment.cash_out:
            container = payment.container
            container.total_expenses = (container.total_expenses or 0) + payment.cash_out
            container.save(update_fields=['total_expenses', 'updated_at'])
        
        return JsonResponse({
            'success': True,
            'id': str(payment.id),
            'date': payment.date,
            'description': payment.description,
            'cash_in': float(payment.cash_in),
            'cash_out': float(payment.cash_out),
            'message': 'Payment created successfully'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_POST
def payments_save_ajax(request):
    """ذخیره دسته‌جمعی Payments (از جدول اکسل-لایک)"""
    try:
        data = json.loads(request.POST.get('data', '[]'))
        
        for item in data:
            payment_id = item.get('id')
            
            defaults = {
                'date': item.get('date', ''),
                'description': item.get('description', ''),
                'cash_in': Decimal(str(item.get('cash_in', 0))),
                'cash_out': Decimal(str(item.get('cash_out', 0))),
                'rate': Decimal(str(item.get('rate', 0))),
                'nzd': Decimal(str(item.get('nzd', 0))),
                'is_percentage': item.get('is_percentage', False),
            }
            
            if item.get('category'):
                defaults['category_id'] = item.get('category')
            if item.get('paid_by'):
                defaults['paid_by_id'] = item.get('paid_by')
            if item.get('received_by'):
                defaults['received_by_id'] = item.get('received_by')
            if item.get('container'):
                defaults['container_id'] = item.get('container')
            
            if payment_id:
                Payment.objects.update_or_create(id=payment_id, defaults=defaults)
            else:
                Payment.objects.create(**defaults)
        
        return JsonResponse({'success': True, 'message': 'Saved successfully'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# containers/views.py - اضافه کن (بعد از payment_list)

@login_required
@require_POST
def payment_update_ajax(request, pk):
    """ویرایش Payment با AJAX (Inline Edit)"""
    try:
        payment = get_object_or_404(Payment, pk=pk)
        data = json.loads(request.body)
        
        # فیلدهای قابل ویرایش
        editable_fields = ['date', 'description', 'rate', 'nzd', 'paid_by', 'received_by', 'cash_in', 'cash_out']
        
        for field, value in data.items():
            if field in editable_fields:
                if field in ['rate', 'nzd', 'cash_in', 'cash_out']:
                    value = Decimal(str(value)) if value else Decimal('0')
                setattr(payment, field, value)
        
        payment.save()
        
        # به‌روزرسانی container.total_expenses اگر payment مربوط به کانتینر باشد
        if payment.container and payment.cash_out:
            container = payment.container
            container.total_expenses = (container.total_expenses or 0) + payment.cash_out
            container.save(update_fields=['total_expenses', 'updated_at'])
        
        return JsonResponse({
            'success': True,
            'message': 'Payment updated successfully'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_POST
def payment_delete_ajax(request, pk):
    """حذف یک Payment"""
    try:
        payment = get_object_or_404(Payment, pk=pk)
        payment.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_GET
def export_inventory_csv(request):
    """خروجی CSV از موجودی"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="inventory.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Product Name', 'Code', 'Container', 'In Stock', 'Sold', 'Unit Price', 'Total Value'])
    
    items = Inventory_List.objects.select_related('container').all()
    for item in items:
        # جایگزین خطوط 438-443
        writer.writerow([
            item.product_name,
            item.code or '',
            item.container.container_no if item.container else '',
            item.in_stock_qty - item.total_sold_qty,  # محاسبه مستقیم
            item.total_sold_qty,
            float(item.unit_price),
            float((item.in_stock_qty - item.total_sold_qty) * item.unit_price),
        ])
    
    return response


@login_required
@require_GET
def export_payments_csv(request):
    """خروجی CSV از پرداخت‌ها"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="payments.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Date', 'Description', 'Paid By', 'Received By', 'Category', 'Cash-In', 'Cash-Out', 'Rate', 'NZD'])
    
    payments = Payment.objects.select_related('paid_by', 'received_by', 'category').all()
    for p in payments:
        writer.writerow([
            p.date,
            p.description,
            p.paid_by.name if p.paid_by else '',
            p.received_by.name if p.received_by else '',
            p.category.name if p.category else '',
            float(p.cash_in or 0),
            float(p.cash_out or 0),
            float(p.rate),
            float(p.nzd),
        ])
    
    return response

# containers/views.py

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
import json
from decimal import Decimal

from .models import Expense, ExpenseCategory, Container
from employee.models import Person

# containers/views.py

@login_required
def expense_list(request):
    """صفحه لیست هزینه‌ها - Excel-like (Add, Edit, Delete در یک صفحه)"""
    
    expenses = Expense.objects.select_related(
        'category', 'paid_by', 'received_by', 'container'
    ).all().order_by('-date')
    
    # ===== فیلتر جستجو =====
    search = request.GET.get('search', '').strip()
    if search:
        expenses = expenses.filter(
            Q(description__icontains=search) |
            Q(category__name__icontains=search) |
            Q(paid_by__name__icontains=search) |
            Q(received_by__name__icontains=search)
        )
    
    # فیلتر بر اساس دسته‌بندی
    category_filter = request.GET.get('category')
    if category_filter:
        expenses = expenses.filter(category_id=category_filter)
    
    # فیلتر بر اساس تاریخ
    date_from = request.GET.get('date_from')
    if date_from:
        expenses = expenses.filter(date__gte=date_from)
    date_to = request.GET.get('date_to')
    if date_to:
        expenses = expenses.filter(date__lte=date_to)
    
    # محاسبه مجموع
    total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    context = {
        'expenses': expenses,
        'total_expenses': total_expenses,
        'categories': ExpenseCategory.objects.filter(is_active=True),
        'people': Person.objects.all(),
        'containers': Container.objects.all(),
        'search': search,  # ✅ این خط مهم است
        'category_filter': category_filter,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'container/expense_list.html', context)


@login_required
@require_POST
def expense_create_ajax(request):
    """ایجاد هزینه جدید (AJAX)"""
    try:
        expense = Expense.objects.create(
            date=request.POST.get('date', ''),
            description=request.POST.get('description', ''),
            amount=Decimal(request.POST.get('amount', 0)),
            category_id=request.POST.get('category') or None,
            paid_by_id=request.POST.get('paid_by') or None,
            received_by_id=request.POST.get('received_by') or None,
            container_id=request.POST.get('container') or None,
            notes=request.POST.get('notes', ''),
        )
        
        return JsonResponse({
            'success': True,
            'id': str(expense.id),
            'date': expense.date,
            'description': expense.description,
            'amount': float(expense.amount),
            'category': expense.category.name if expense.category else '',
            'paid_by': expense.paid_by.name if expense.paid_by else '',
            'received_by': expense.received_by.name if expense.received_by else '',
            'container': expense.container.container_no if expense.container else '',
            'message': 'Expense created successfully'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@csrf_exempt
@require_POST
def expense_update_ajax(request, pk):
    """ویرایش هزینه (AJAX)"""
    try:
        expense = get_object_or_404(Expense, pk=pk)
        data = json.loads(request.body)
        
        if 'date' in data:
            expense.date = data['date']
        if 'description' in data:
            expense.description = data['description']
        if 'amount' in data:
            expense.amount = Decimal(data['amount'])
        if 'category' in data:
            expense.category_id = data['category'] or None
        if 'paid_by' in data:
            expense.paid_by_id = data['paid_by'] or None
        if 'received_by' in data:
            expense.received_by_id = data['received_by'] or None
        if 'container' in data:
            expense.container_id = data['container'] or None
        if 'notes' in data:
            expense.notes = data['notes']
        
        expense.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Expense updated successfully'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_POST
def expense_delete_ajax(request, pk):
    """حذف هزینه (AJAX)"""
    try:
        expense = get_object_or_404(Expense, pk=pk)
        expense.delete()
        return JsonResponse({'success': True, 'message': 'Expense deleted'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    
# containers/views.py

@login_required
@require_POST
def expense_category_create_ajax(request):
    """ایجاد دسته‌بندی جدید (AJAX)"""
    try:
        name = request.POST.get('name', '').strip()
        if not name:
            return JsonResponse({'success': False, 'error': 'Category name is required'})
        
        if ExpenseCategory.objects.filter(name__iexact=name).exists():
            return JsonResponse({'success': False, 'error': 'Category already exists'})
        
        category = ExpenseCategory.objects.create(
            name=name,
            description=request.POST.get('description', ''),
            is_active=True
        )
        
        return JsonResponse({
            'success': True,
            'id': str(category.id),
            'name': category.name,
            'message': 'Category created successfully'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})