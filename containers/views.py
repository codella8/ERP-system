# containers/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, F
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.utils import timezone
from datetime import datetime
from decimal import Decimal
import json
import logging

from .models import Container, Inventory_List

logger = logging.getLogger(__name__)


@login_required
def container_list(request):
    """صفحه اصلی لیست کانتینرها - مثل Daily Sale"""
    # دریافت همه کانتینرها
    containers = Container.objects.all().order_by('-arrival_date', '-created_at')
    
    # جستجو
    search = request.GET.get('search', '')
    if search:
        containers = containers.filter(
            Q(container_number__icontains=search) |
            Q(supplier__icontains=search) |
            Q(code__icontains=search)
        )
    
    # فیلتر وضعیت
    status = request.GET.get('status', '')
    if status:
        containers = containers.filter(transport_status=status)
    
    # فیلتر تاریخ
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        containers = containers.filter(arrival_date__gte=date_from)
    if date_to:
        containers = containers.filter(arrival_date__lte=date_to)
    
    # آمار برای کارت‌ها
    total_containers = containers.count()
    in_transit_count = containers.filter(transport_status='in_transit').count()
    arrived_count = containers.filter(transport_status='arrived').count()
    awaiting_count = containers.filter(transport_status='awaiting').count()
    
    # محاسبه总值
    total_items = 0
    total_value = 0
    total_sales = 0
    total_expenses = 0
    
    for container in containers:
        if hasattr(container, 'inventory_items'):
            # مجموع آیتم‌ها
            item_total = container.inventory_items.aggregate(total=Sum('in_stock_qty'))['total'] or 0
            total_items += item_total
            
            # ارزش کل موجودی
            total_value += container.total_inventory_value
        
        # مجموع فروش و هزینه
        total_sales += container.total_sales or 0
        total_expenses += container.total_expenses or 0
    
    context = {
        'containers': containers,
        'total_containers': total_containers,
        'in_transit_count': in_transit_count,
        'arrived_count': arrived_count,
        'awaiting_count': awaiting_count,
        'total_items': total_items,
        'total_value': total_value,
        'total_sales': total_sales,
        'total_expenses': total_expenses,
        'search': search,
        'status_filter': status,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'container/container_list.html', context)


@login_required
@require_POST
def container_create_ajax(request):
    """ایجاد کانتینر جدید - ذخیره دائمی"""
    try:
        print("Creating container with data:", request.POST)  # برای دیباگ
        
        container = Container.objects.create(
            container_number=request.POST.get('container_number'),
            supplier=request.POST.get('supplier', ''),
            code=request.POST.get('code', ''),
            transport_status=request.POST.get('transport_status', 'awaiting'),
            arrival_date=request.POST.get('arrival_date') or None,
            total_sales=Decimal(request.POST.get('total_sales', '0')),
            total_expenses=Decimal(request.POST.get('total_expenses', '0')),
        )
        
        print(f"Container created with ID: {container.id}")
        
        return JsonResponse({
            'success': True, 
            'id': str(container.id),
            'container_number': container.container_number,
            'message': 'کانتینر با موفقیت ایجاد شد'
        })
        
    except Exception as e:
        print(f"Error creating container: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def container_update_ajax(request, pk):
    """ویرایش کانتینر - ذخیره دائمی در دیتابیس"""
    try:
        container = get_object_or_404(Container, pk=pk)
        data = json.loads(request.body)
        
        print(f"Updating container {pk} with data:", data)  # برای دیباگ
        
        # فیلدهای قابل ویرایش
        editable_fields = [
            'container_number', 'supplier', 'code', 
            'transport_status', 'total_sales', 'total_expenses'
        ]
        
        changes_made = False
        
        for field, value in data.items():
            if field in editable_fields and hasattr(container, field):
                if field == 'arrival_date' and value:
                    try:
                        # تبدیل تاریخ به فرمت درست
                        container.arrival_date = datetime.strptime(value, '%Y-%m-%d').date()
                        changes_made = True
                    except ValueError as e:
                        print(f"Date error: {e}")
                        
                elif field in ['total_sales', 'total_expenses'] and value:
                    try:
                        # تبدیل به Decimal
                        setattr(container, field, Decimal(str(value)))
                        changes_made = True
                    except:
                        pass
                        
                elif value is not None:
                    # فیلدهای متنی
                    setattr(container, field, value)
                    changes_made = True
        
        if changes_made:
            container.save()  # ذخیره در دیتابیس
            print(f"Container {pk} saved successfully")
            
            # محاسبه سود خالص
            net_value = (container.total_sales or 0) - (container.total_expenses or 0)
            
            return JsonResponse({
                'success': True,
                'message': 'تغییرات با موفقیت ذخیره شد',
                'id': str(container.id),
                'container_number': container.container_number,
                'supplier': container.supplier,
                'code': container.code,
                'transport_status': container.transport_status,
                'total_sales': float(container.total_sales or 0),
                'total_expenses': float(container.total_expenses or 0),
                'net_value': float(net_value),
                'arrival_date': container.arrival_date.strftime('%Y-%m-%d') if container.arrival_date else None,
            })
        else:
            return JsonResponse({
                'success': True,
                'message': 'No changes made',
            })
        
    except Container.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'کانتینر یافت نشد'}, status=404)
    except Exception as e:
        print(f"Error updating container: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def container_detail(request, pk):
    """صفحه جزئیات کانتینر"""
    container = get_object_or_404(Container, pk=pk)
    
    # محاسبات برای صفحه جزئیات
    inventory_items = container.inventory_items.all()
    total_items = inventory_items.count()
    total_qty = sum(item.in_stock_qty for item in inventory_items)
    total_value = container.total_inventory_value
    
    context = {
        'container': container,
        'inventory_items': inventory_items,
        'total_items': total_items,
        'total_qty': total_qty,
        'total_value': total_value,
    }
    
    return render(request, 'container/container_detail.html', context)



@login_required
def inventory_list(request):
    """صفحه اصلی لیست موجودی - Excel-like view"""
    # دریافت همه آیتم‌های موجودی
    items = Inventory_List.objects.select_related('container').all().order_by('-created_at')
    
    # جستجو
    search = request.GET.get('search', '')
    if search:
        items = items.filter(
            Q(product_name__icontains=search) |
            Q(code__icontains=search) |
            Q(container__container_number__icontains=search)
        )
    
    # فیلتر بر اساس کانتینر
    container_id = request.GET.get('container', '')
    if container_id:
        items = items.filter(container_id=container_id)
    
    # فیلتر بر اساس وضعیت
    status = request.GET.get('status', '')
    if status:
        items = items.filter(status=status)
    
    # آمار برای کارت‌ها
    total_items = items.count()
    total_qty = items.aggregate(total=Sum('in_stock_qty'))['total'] or 0
    total_sold_qty = items.aggregate(total=Sum('total_sold_qty'))['total'] or 0
    total_value = sum(item.total_value for item in items)
    
    # آمار وضعیت‌ها
    available_count = items.filter(status='available').count()
    partial_count = items.filter(status='partial').count()
    sold_out_count = items.filter(status='sold_out').count()
    
    # لیست کانتینرها برای فیلتر
    containers = Container.objects.all().order_by('container_number')
    
    context = {
        'items': items,
        'total_items': total_items,
        'total_qty': total_qty,
        'total_sold_qty': total_sold_qty,
        'total_value': total_value,
        'available_count': available_count,
        'partial_count': partial_count,
        'sold_out_count': sold_out_count,
        'containers': containers,
        'search': search,
        'container_filter': container_id,
        'status_filter': status,
    }
    
    return render(request, 'container/inventory_list.html', context)


@login_required
@require_POST
def inventory_create_ajax(request):
    """ایجاد آیتم جدید در موجودی"""
    try:
        container_id = request.POST.get('container')
        container = None
        if container_id:
            container = get_object_or_404(Container, id=container_id)
        
        item = Inventory_List.objects.create(
            container=container,
            product_name=request.POST.get('product_name'),
            code=request.POST.get('code', ''),
            make=request.POST.get('make', ''),
            model=request.POST.get('model', ''),
            in_stock_qty=Decimal(request.POST.get('in_stock_qty', '0')),
            unit_price=Decimal(request.POST.get('unit_price', '0')),
            price=Decimal(request.POST.get('price', '0')),
            description=request.POST.get('description', ''),
        )
        
        return JsonResponse({
            'success': True,
            'id': str(item.id),
            'message': 'Item created successfully'
        })
        
    except Exception as e:
        logger.error(f"Error creating inventory item: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def inventory_update_ajax(request, pk):
    """ویرایش آیتم موجودی"""
    try:
        item = get_object_or_404(Inventory_List, pk=pk)
        data = json.loads(request.body)
        
        # فیلدهای قابل ویرایش
        editable_fields = [
            'product_name', 'code', 'make', 'model',
            'in_stock_qty', 'unit_price', 'price',
            'total_sold_qty', 'description'
        ]
        
        for field, value in data.items():
            if field in editable_fields and hasattr(item, field):
                if field in ['in_stock_qty', 'unit_price', 'price', 'total_sold_qty']:
                    try:
                        setattr(item, field, Decimal(str(value)))
                    except:
                        pass
                else:
                    setattr(item, field, value)
        
        item.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Item updated successfully',
            'id': str(item.id),
            'product_name': item.product_name,
            'code': item.code,
            'in_stock_qty': float(item.in_stock_qty),
            'total_sold_qty': float(item.total_sold_qty),
            'in_stock': float(item.in_stock),
            'unit_price': float(item.unit_price),
            'total_value': float(item.total_value),
            'status': item.status,
        })
        
    except Inventory_List.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Item not found'}, status=404)
    except Exception as e:
        logger.error(f"Error updating inventory item: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def inventory_detail(request, pk):
    """صفحه جزئیات آیتم موجودی"""
    item = get_object_or_404(Inventory_List, pk=pk)
    context = {'item': item}
    return render(request, 'container/inventory_detail.html', context)


@login_required
@require_POST
def inventory_sell_ajax(request, pk):
    """ثبت فروش برای آیتم"""
    try:
        item = get_object_or_404(Inventory_List, pk=pk)
        quantity = Decimal(request.POST.get('quantity', '0'))
        
        if quantity <= 0:
            return JsonResponse({'success': False, 'error': 'Quantity must be positive'})
        
        if quantity > item.in_stock:
            return JsonResponse({'success': False, 'error': f'Only {item.in_stock} items available'})
        
        # بروزرسانی موجودی
        item.total_sold_qty += quantity
        if request.POST.get('sold_price'):
            item.sold_price = Decimal(request.POST.get('sold_price'))
        
        item.save()
        
        return JsonResponse({
            'success': True,
            'message': f'{quantity} items sold',
            'in_stock': float(item.in_stock),
            'total_sold_qty': float(item.total_sold_qty),
            'status': item.status,
        })
        
    except Inventory_List.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Item not found'}, status=404)
    except Exception as e:
        logger.error(f"Error selling item: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    
# containers/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Container, Inventory_List, ContainerTransaction
import json


@login_required
def container_daily_report(request):
    """گزارش خلاصه روزانه کانتینرها - مطابق عکس کارفرما"""
    
    # دریافت تاریخ از کاربر یا پیش‌فرض امروز
    selected_date = request.GET.get('date', timezone.now().date().strftime('%Y-%m-%d'))
    
    try:
        report_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
    except ValueError:
        report_date = timezone.now().date()
    
    # ========== گزارش روزانه ==========
    # تمام تراکنش‌های این روز
    daily_transactions = ContainerTransaction.objects.filter(
        created_at__date=report_date
    ).select_related('container')
    
    # خلاصه بر اساس کد محصول
    daily_summary = daily_transactions.values(
        'product'
    ).annotate(
        total_sales=Sum('total_price'),
        total_qty=Sum('quantity'),
        transaction_count=Count('id')
    ).order_by('-total_sales')
    
    # ========== آمار کلی روز ==========
    total_sales = daily_transactions.aggregate(
        total=Sum('total_price')
    )['total'] or 0
    
    total_transactions = daily_transactions.count()
    total_items_sold = daily_transactions.aggregate(
        total=Sum('quantity')
    )['total'] or 0
    
    # ========== محاسبه Not Sold (آیتم‌های فروش نرفته) ==========
    # تمام آیتم‌های موجود در این روز
    inventory_items = Inventory_List.objects.filter(
        created_at__date=report_date
    )
    
    not_sold_count = inventory_items.filter(
        total_sold_qty=0
    ).count()
    
    # ========== داده برای نمودار ==========
    chart_labels = []
    chart_data = []
    
    for item in daily_summary[:10]:  # ۱۰ مورد اول
        chart_labels.append(item['product'] or 'No Code')
        chart_data.append(float(item['total_sales'] or 0))
    
    # ========== جستجو ==========
    search_query = request.GET.get('search', '')
    if search_query:
        daily_summary = [
            item for item in daily_summary 
            if search_query.lower() in (item['product'] or '').lower()
        ]
    
    context = {
        'report_date': report_date,
        'daily_summary': daily_summary,
        'total_sales': total_sales,
        'total_transactions': total_transactions,
        'total_items_sold': total_items_sold,
        'not_sold_count': not_sold_count,
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data),
        'search_query': search_query,
        
        # تاریخ‌های قبل و بعد برای ناوبری
        'prev_date': (report_date - timedelta(days=1)).strftime('%Y-%m-%d'),
        'next_date': (report_date + timedelta(days=1)).strftime('%Y-%m-%d'),
        'today': timezone.now().date().strftime('%Y-%m-%d'),
    }
    
    return render(request, 'container/daily_report.html', context)


@login_required
def container_monthly_summary(request):
    """گزارش خلاصه ماهانه"""
    
    # دریافت ماه و سال از کاربر
    year = int(request.GET.get('year', timezone.now().year))
    month = int(request.GET.get('month', timezone.now().month))
    
    start_date = datetime(year, month, 1).date()
    if month == 12:
        end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
    else:
        end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
    
    # تراکنش‌های این ماه
    monthly_transactions = ContainerTransaction.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    )
    
    # خلاصه روزانه
    daily_report = monthly_transactions.values(
        'created_at__date'
    ).annotate(
        total_sales=Sum('total_price'),
        transaction_count=Count('id'),
        items_sold=Sum('quantity')
    ).order_by('created_at__date')
    
    context = {
        'year': year,
        'month': month,
        'month_name': start_date.strftime('%B'),
        'daily_report': daily_report,
        'total_sales': monthly_transactions.aggregate(total=Sum('total_price'))['total'] or 0,
        'total_transactions': monthly_transactions.count(),
    }
    
    return render(request, 'container/monthly_report.html', context)