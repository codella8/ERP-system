# daily_sale/views.py
from decimal import Decimal
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction as db_transaction
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Sum, Q, Count
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from datetime import datetime, timedelta
from containers.models import Inventory_List, Container
import json

from .models import DailySaleTransaction
from .signals import CodeSummary
from .services import SummaryService
from containers.models import Inventory_List, Container

logger = logging.getLogger(__name__)

@login_required
@db_transaction.atomic
def transaction_create(request):
    if request.method == "POST":
        date_str = request.POST.get('date')
        from datetime import datetime
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        customer_name = request.POST.get('customer_name', '').strip()
        invoice_number = request.POST.get('invoice_number', '')
        code = request.POST.get('code', '')
        description = request.POST.get('description', '')
        qty = Decimal(request.POST.get('qty', 1))
        sales = Decimal(request.POST.get('sales', 0))
        paid = Decimal(request.POST.get('paid', 0))
        discount = Decimal(request.POST.get('discount', 0))
        item_id = request.POST.get('item_id')
        container_id = request.POST.get('container_id')
        item = None
        container = None
        
        if item_id:
            try:
                item = Inventory_List.objects.get(pk=item_id)
                if not container_id and item.container:
                    container = item.container
            except Inventory_List.DoesNotExist:
                messages.error(request, 'Item not found')
                return redirect('daily_sale:transaction_create')
        
        if container_id:
            try:
                container = Container.objects.get(pk=container_id)
            except Container.DoesNotExist:
                pass
        if item and qty > 0:
            current_stock = item.in_stock_qty - item.total_sold_qty
            if qty > current_stock:
                messages.error(request, f'Not enough stock! Available: {current_stock}')
                return redirect('daily_sale:transaction_create')
        if qty == 0:
            messages.warning(request, '⚠️ QTY is zero. No stock will be deducted.')
        transaction = DailySaleTransaction(
            date=date_obj,
            customer_name=customer_name,
            invoice_number=invoice_number if invoice_number else None,
            code=code,
            item_description=description,
            qty=int(qty),
            sales=sales,
            paid=paid,
            discount=discount,
            item=item,
            container=container,
            created_by=request.user
        )
        
        transaction.save()
        
        messages.success(request, f"✅ Transaction saved! Invoice: {transaction.invoice_number}")
        return redirect('daily_sale:transaction_list')
    items = Inventory_List.objects.select_related('container').all().order_by('product_name')
    for item in items:
        item.current_stock = item.in_stock_qty - item.total_sold_qty
    
    return render(request, 'daily_sale/transaction_create.html', {'items': items})

@login_required
def transaction_list(request):
    try:
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        search = request.GET.get('search', '').strip()
        payment_status = request.GET.get('payment_status', '')
        per_page = int(request.GET.get('per_page', 25))
        qs = DailySaleTransaction.objects.select_related('item', 'container').all().order_by('-date', '-created_at')

        if start_date:
            qs = qs.filter(date__gte=start_date)
        if end_date:
            qs = qs.filter(date__lte=end_date)
        if payment_status:
            qs = qs.filter(payment_status=payment_status)
        if search:
            qs = qs.filter(
                Q(customer_name__icontains=search) |
                Q(invoice_number__icontains=search) |
                Q(code__icontains=search) |
                Q(item_description__icontains=search)
            )
        
        stats = SummaryService.get_transaction_stats(qs)
        paginator = Paginator(qs, per_page)
        page_number = request.GET.get('page', 1)
        try:
            page_obj = paginator.page(page_number)
        except (PageNotAnInteger, EmptyPage):
            page_obj = paginator.page(1)
        
        context = {
            'page_obj': page_obj,
            'transactions': page_obj.object_list,
            'stats': stats,
            'start_date': start_date,
            'end_date': end_date,
            'search': search,
            'payment_status_filter': payment_status,
            'per_page': per_page,
            'total_count': qs.count(),
        }
        
        return render(request, 'daily_sale/transaction_list.html', context)
        
    except Exception as e:
        logger.error(f"Error in transaction_list: {str(e)}", exc_info=True)
        messages.error(request, f"Error loading transactions: {str(e)}")
        return render(request, 'daily_sale/transaction_list.html', {'transactions': [], 'stats': {}})

# daily_sale/views.py

@login_required
def daily_summary(request):
    """خلاصه روزانه فروش - با قابلیت کلیک روی کدها"""
    try:
        from django.db.models import Sum, Q, Count
        from decimal import Decimal
        from containers.models import Payment, Container, Expense  # ✅ اضافه شد
        
        date_str = request.GET.get('date')
        selected_code = request.GET.get('code', '')
        
        if date_str:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            selected_date = timezone.now().date()
        
        # ============================================================
        # 1. دریافت یا محاسبه خلاصه کدها
        # ============================================================
        code_summaries = CodeSummary.objects.filter(date=selected_date)
        
        if not code_summaries.exists():
            transactions = DailySaleTransaction.objects.filter(
                date=selected_date
            ).exclude(code__isnull=True).exclude(code='')
            
            if transactions.exists():
                codes = transactions.values_list('code', flat=True).distinct()
                
                for code in codes:
                    qs = transactions.filter(code=code)
                    agg = qs.aggregate(
                        total_sales=Sum('sales'),
                        total_discount=Sum('discount'),
                        total_paid=Sum('paid'),
                        total_qty=Sum('qty'),
                        transaction_count=Count('id'),
                        not_sold=Count('id', filter=Q(sales=0) | Q(qty=0))
                    )
                    
                    total_sales = agg['total_sales'] or 0
                    total_discount = agg['total_discount'] or 0
                    net_total = total_sales - total_discount
                    if net_total < 0:
                        net_total = 0
                    
                    first_tx = qs.first()
                    
                    CodeSummary.objects.create(
                        date=selected_date,
                        code=code,
                        product_name=first_tx.item_description if first_tx else '',
                        container_no=first_tx.container.container_no if first_tx and first_tx.container else '',
                        total_sales=total_sales,
                        total_discount=total_discount,
                        total_paid=agg['total_paid'] or 0,
                        total_qty=agg['total_qty'] or 0,
                        transaction_count=agg['transaction_count'] or 0,
                        not_sold=agg['not_sold'] or 0,
                        net_total=net_total,
                        item_id=first_tx.item_id if first_tx else None,
                        container_id=first_tx.container_id if first_tx else None,
                    )
                
                code_summaries = CodeSummary.objects.filter(date=selected_date)
        
        # ============================================================
        # 2. محاسبه آمار روزانه
        # ============================================================
        daily_transactions = DailySaleTransaction.objects.filter(date=selected_date)
        
        total_sales = daily_transactions.aggregate(total=Sum('total'))['total'] or Decimal('0')
        total_paid = daily_transactions.aggregate(total=Sum('paid'))['total'] or Decimal('0')
        total_discount = daily_transactions.aggregate(total=Sum('discount'))['total'] or Decimal('0')
        total_qty = daily_transactions.aggregate(total=Sum('qty'))['total'] or 0
        transaction_count = daily_transactions.count()
        
        # ============================================================
        # 3. ✅ محاسبه هزینه‌ها (از Expense در containers)
        # ============================================================
        # ✅ با فرمت تاریخ 'DD-MMM-YY' مثل "04-Jul-26"
        date_str_formatted = selected_date.strftime('%d-%b-%y')
        
        # لاگ برای دیباگ
        print(f"🔍 Looking for expenses on: {date_str_formatted}")
        
        total_expense = Expense.objects.filter(
            date=date_str_formatted
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        print(f"💰 Total expense from Expense model: {total_expense}")
        
        # اگر هیچ هزینه‌ای در آن تاریخ نبود، از Payment بگیر
        if total_expense == 0:
            total_expense = Payment.objects.filter(
                date=date_str_formatted,
                cash_out__gt=0
            ).aggregate(total=Sum('cash_out'))['total'] or Decimal('0')
            print(f"💰 Total expense from Payment: {total_expense}")
        
        # اگر باز هم صفر بود، از Container.total_expenses بگیر
        if total_expense == 0:
            containers = Container.objects.filter(
                daily_sales__date=selected_date
            ).distinct()
            for container in containers:
                total_expense += container.total_expenses or Decimal('0')
            print(f"💰 Total expense from Container: {total_expense}")
        
        # ============================================================
        # 4. محاسبه Net Pay
        # ============================================================
        net_pay = total_sales - total_expense
        
        # ============================================================
        # 5. جمع‌بندی بر اساس کد
        # ============================================================
        code_summary = daily_transactions.values('code').annotate(
            total=Sum('total'),
            not_sold=Count('id', filter=Q(sales=0) | Q(qty=0))
        ).order_by('code')
        
        # ============================================================
        # 6. جزئیات کد انتخاب شده
        # ============================================================
        selected_summary = None
        code_transactions = []
        
        if selected_code:
            selected_summary = code_summaries.filter(code=selected_code).first()
            if selected_summary:
                code_transactions = DailySaleTransaction.objects.filter(
                    date=selected_date,
                    code=selected_code
                ).order_by('-created_at')
        
        # ============================================================
        # 7. تاریخ‌های قبلی و بعدی
        # ============================================================
        prev_date = selected_date - timedelta(days=1)
        next_date = selected_date + timedelta(days=1)
        today = timezone.now().date()
        
        # ============================================================
        # 8. جمع کل
        # ============================================================
        grand_total = code_summaries.aggregate(total=Sum('net_total'))['total'] or 0
        total_not_sold = code_summaries.aggregate(total=Sum('not_sold'))['total'] or 0
        
        # ✅ لاگ نهایی
        print(f"📊 Final - total_sales: {total_sales}, total_expense: {total_expense}, net_pay: {net_pay}")
        
        context = {
            'selected_date': selected_date,
            'prev_date': prev_date,
            'next_date': next_date,
            'today': today,
            'code_summaries': code_summaries,
            'code_summary': code_summary,
            'grand_total': grand_total,
            'total_not_sold': total_not_sold,
            'selected_code': selected_code,
            'selected_summary': selected_summary,
            'code_transactions': code_transactions,
            'total_sales': total_sales,
            'total_paid': total_paid,
            'total_discount': total_discount,
            'total_expense': total_expense,
            'net_pay': net_pay,
            'total_qty': total_qty,
            'transaction_count': transaction_count,
        }
        
        return render(request, 'daily_sale/daily_summary.html', context)
        
    except Exception as e:
        logger.error(f"Error in daily_summary: {str(e)}", exc_info=True)
        messages.error(request, f"Error loading summary: {str(e)}")
        return render(request, 'daily_sale/daily_summary.html', {'error': True})

@login_required
def transaction_delete(request, pk):
    try:
        transaction = get_object_or_404(DailySaleTransaction, pk=pk)
        invoice = transaction.invoice_number
        item_name = transaction.item.product_name if transaction.item else None
        container = transaction.container
        if transaction.item:
            transaction.item.in_stock_qty += transaction.qty
            transaction.item.total_sold_qty -= transaction.qty
            transaction.item.save(update_fields=['in_stock_qty', 'total_sold_qty', 'updated_at'])
            logger.info(f"Stock restored: {transaction.item.product_name} -> In Stock: {transaction.item.in_stock_qty}")
        
        transaction.delete()
        if container:
            from django.db.models import Sum
            total_sales = DailySaleTransaction.objects.filter(
                container=container
            ).aggregate(total=Sum('total'))['total'] or Decimal('0')
            
            container.total_sales = total_sales
            container.save(update_fields=['total_sales', 'updated_at'])
            logger.info(f"✅ Container {container.container_no} total_sales updated to {total_sales}")
        
        messages.success(request, f"Transaction {invoice} deleted successfully!")
        if item_name:
            messages.info(request, f"Stock restored for {item_name}")
            
    except Exception as e:
        logger.error(f"Error deleting transaction: {e}")
        messages.error(request, "Error deleting transaction!")
    
    return redirect("daily_sale:transaction_list")

@login_required
@require_POST
def transaction_update_ajax(request, pk):
    try:
        transaction = get_object_or_404(DailySaleTransaction, pk=pk)
        data = json.loads(request.body)
        editable_fields = ['customer_name', 'code', 'item_description', 'qty', 'sales', 'paid', 'discount']
        
        for field, value in data.items():
            if field in editable_fields:
                if field == 'qty':
                    value = int(value) if value else 0
                elif field in ['sales', 'paid', 'discount']:
                    value = Decimal(str(value)) if value else Decimal('0')
                setattr(transaction, field, value)
        amounts = transaction.calculate_amounts()
        transaction.total = amounts['total']
        transaction.balance = amounts['balance']
        transaction.payment_status = amounts['payment_status']
        
        transaction.save()
        if transaction.container:
            from django.db.models import Sum
            total_sales = DailySaleTransaction.objects.filter(
                container=transaction.container
            ).aggregate(total=Sum('total'))['total'] or Decimal('0')
            transaction.container.total_sales = total_sales
            transaction.container.save(update_fields=['total_sales', 'updated_at'])
        
        return JsonResponse({
            'success': True,
            'message': 'Transaction updated successfully',
            'total': float(transaction.total),
            'balance': float(transaction.balance),
            'payment_status': transaction.payment_status,
            'paid': float(transaction.paid),
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def invoice_view(request, pk):
    transaction = get_object_or_404(
        DailySaleTransaction.objects.select_related('item', 'container', 'created_by'),
        pk=pk
    )
    
    context = {
        'transaction': transaction,
        'total': transaction.total,
        'balance': transaction.balance,
        'payment_status': transaction.get_payment_status_display(),
    }
    
    return render(request, 'daily_sale/detail.html', context)


@login_required
def get_item_details(request):
    item_id = request.GET.get('item_id')
    
    if not item_id:
        return JsonResponse({'success': False, 'error': 'Item ID required'})
    
    try:
        item = Inventory_List.objects.select_related('container').get(pk=item_id)
        
        response_data = {
            'success': True,
            'item': {
                'id': str(item.id),
                'code': item.code,
                'product_name': item.product_name,
                'unit_price': float(item.unit_price) if item.unit_price else 0,
                'in_stock_qty': float(item.in_stock_qty) if item.in_stock_qty else 0,
                'total_sold_qty': float(item.total_sold_qty) if item.total_sold_qty else 0,
            }
        }
        
        if item.container:
            response_data['container'] = {
                'id': str(item.container.id),
                'container_no': item.container.container_no,
                'code': item.container.code if hasattr(item.container, 'code') else '',
            }
        
        return JsonResponse(response_data)
        
    except Inventory_List.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Item not found'})
    except Exception as e:
        logger.error(f"Error in get_item_details: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def search_items(request):
    q = request.GET.get('q', '').strip()
    limit = int(request.GET.get('limit', 25))
    
    qs = Inventory_List.objects.select_related('container').all()
    
    if q:
        qs = qs.filter(
            Q(product_name__icontains=q) |
            Q(code__icontains=q) |
            Q(model__icontains=q)
        )
    
    results = []
    for item in qs[:limit]:
        results.append({
            'id': str(item.id),
            'text': f"{item.code} - {item.product_name}" if item.code else item.product_name,
            'code': item.code,
            'product_name': item.product_name,
            'unit_price': float(item.unit_price) if item.unit_price else 0,
            'in_stock_qty': float(item.in_stock_qty) if item.in_stock_qty else 0,
        })
    
    return JsonResponse({'results': results})

@login_required
@require_POST
@db_transaction.atomic
def transaction_create_ajax(request):
    try:
        date = request.POST.get('date')
        customer_name = request.POST.get('customer_name', '').strip()
        code = request.POST.get('code', '')
        item_description = request.POST.get('description', '')
        qty = Decimal(request.POST.get('qty', 1))
        sales = Decimal(request.POST.get('sales', 0))
        paid = Decimal(request.POST.get('paid', 0))
        discount = Decimal(request.POST.get('discount', 0))
        item_id = request.POST.get('item_id')
        container_id = request.POST.get('container_id')
        
        if not customer_name:
            return JsonResponse({'success': False, 'error': 'Customer name is required'})
        
        if qty <= 0:
            return JsonResponse({'success': False, 'error': 'QTY must be greater than 0'})
        item = None
        container = None
        
        if item_id:
            try:
                item = Inventory_List.objects.get(pk=item_id)
                if item.in_stock_qty < qty:
                    return JsonResponse({'success': False, 'error': f'Insufficient stock. Available: {item.in_stock_qty}'})
                
                if not code:
                    code = item.code
                if not item_description:
                    item_description = item.product_name
                if sales == 0:
                    sales = item.unit_price * qty
                    
            except Inventory_List.DoesNotExist:
                pass
        
        if container_id:
            try:
                container = Container.objects.get(pk=container_id)
            except Container.DoesNotExist:
                pass
        
        transaction = DailySaleTransaction(
            date=date,
            customer_name=customer_name,
            code=code,
            item_description=item_description,
            qty=int(qty),
            sales=sales,
            paid=paid,
            discount=discount,
            item=item,
            container=container,
            created_by=request.user
        )
        transaction.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Transaction saved! Invoice: {transaction.invoice_number}',
            'transaction': {
                'id': str(transaction.id),
                'date': str(transaction.date),
                'customer_name': transaction.customer_name,
                'invoice_number': transaction.invoice_number,
                'code': transaction.code or '',
                'item_description': transaction.item_description or '',
                'qty': transaction.qty,
                'sales': float(transaction.sales),
                'paid': float(transaction.paid),
                'discount': float(transaction.discount),
                'total': float(transaction.total),
                'payment_status': transaction.payment_status,
                'item_name': transaction.item.product_name if transaction.item else None,
            }
        })
        
    except Exception as e:
        logger.error(f"Error in transaction_create_ajax: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)})
    
def search_items(request):
    q = request.GET.get('q', '').strip()
    items = Inventory_List.objects.select_related('container').all()
    
    if q:
        items = items.filter(
            Q(product_name__icontains=q) | 
            Q(code__icontains=q) |
            Q(model__icontains=q)
        )
    
    results = []
    for item in items[:25]:
        results.append({
            'id': str(item.id),
            'text': f"{item.code or ''} - {item.product_name} (Stock: {item.in_stock_qty})",
            'stock': float(item.in_stock_qty),
            'unit_price': float(item.unit_price),
        })
    
    return JsonResponse({'results': results})

def get_item_details(request):
    item_id = request.GET.get('item_id')
    
    try:
        item = Inventory_List.objects.select_related('container').get(pk=item_id)
        
        response = {
            'success': True,
            'item': {
                'id': str(item.id),
                'code': item.code or '',
                'product_name': item.product_name,
                'unit_price': float(item.unit_price),
                'in_stock_qty': float(item.in_stock_qty),
            }
        }
        
        if item.container:
            response['container'] = {
                'id': str(item.container.id),
                'container_no': item.container.container_no,
            }
        
        return JsonResponse(response)
        
    except Inventory_List.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Item not found'})

def search_container(request):
    q = request.GET.get('q', '').strip()
    containers = Container.objects.filter(container_no__icontains=q)[:10]
    results = [{'id': str(c.id), 'text': c.container_no} for c in containers]
    return JsonResponse({'results': results})

