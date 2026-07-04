# daily_sale/utils.py
import logging
from decimal import Decimal
from datetime import timedelta
from django.db.models import Sum, Count, Q
from django.utils import timezone
from .models import DailySaleTransaction

logger = logging.getLogger(__name__)


def _aggregate_transactions(qs):
    result = qs.aggregate(
        total_sales=Sum('sales'),
        total_discount=Sum('discount'),
        total_paid=Sum('paid'),
        total_qty=Sum('qty'),
        transaction_count=Count('id'),
    )

    result['total_sales'] = result['total_sales'] or Decimal('0')
    result['total_discount'] = result['total_discount'] or Decimal('0')
    result['total_paid'] = result['total_paid'] or Decimal('0')
    result['total_qty'] = result['total_qty'] or 0
    result['transaction_count'] = result['transaction_count'] or 0
    result['net_total'] = result['total_sales'] - result['total_discount']
    if result['net_total'] < 0:
        result['net_total'] = Decimal('0')
    
    return result


def get_sales_summary(start_date, end_date):
    try:
        qs = DailySaleTransaction.objects.filter(date__range=[start_date, end_date])
        result = _aggregate_transactions(qs)
        unpaid_balance = qs.filter(balance__gt=0).aggregate(
            total=Sum('balance')
        )['total'] or Decimal('0')
        paid_count = qs.filter(payment_status='paid').count()
        partial_count = qs.filter(payment_status='partial').count()
        unpaid_count = qs.filter(payment_status='unpaid').count()
        
        return {
            'total_sales': result['total_sales'],
            'total_discount': result['total_discount'],
            'net_total': result['net_total'],
            'total_paid': result['total_paid'],
            'total_qty': result['total_qty'],
            'transaction_count': result['transaction_count'],
            'unpaid_balance': unpaid_balance,
            'paid_count': paid_count,
            'partial_count': partial_count,
            'unpaid_count': unpaid_count,
        }
        
    except Exception as e:
        logger.exception(f"Error in get_sales_summary: {e}")
        return {
            'total_sales': Decimal('0'),
            'total_discount': Decimal('0'),
            'net_total': Decimal('0'),
            'total_paid': Decimal('0'),
            'total_qty': 0,
            'transaction_count': 0,
            'unpaid_balance': Decimal('0'),
            'paid_count': 0,
            'partial_count': 0,
            'unpaid_count': 0,
        }


def sales_timeseries(start_date, end_date, group_by='day'):
    try:
        timeseries = []
        current_date = start_date
        
        while current_date <= end_date:
            if group_by == 'day':
                date_end = current_date
                next_date = current_date + timedelta(days=1)
            elif group_by == 'week':
                date_end = current_date + timedelta(days=6)
                next_date = current_date + timedelta(days=7)
            else:  # month
                if current_date.month == 12:
                    next_date = current_date.replace(year=current_date.year + 1, month=1, day=1)
                else:
                    next_date = current_date.replace(month=current_date.month + 1, day=1)
                date_end = next_date - timedelta(days=1)
            
            qs = DailySaleTransaction.objects.filter(date__range=[current_date, date_end])
            agg = _aggregate_transactions(qs)
            
            timeseries.append({
                'date_start': current_date,
                'date_end': date_end,
                'label': str(current_date),
                'total_sales': agg['total_sales'],
                'net_total': agg['net_total'],
                'transaction_count': agg['transaction_count'],
                'total_qty': agg['total_qty'],
            })
            
            current_date = next_date
        
        return timeseries
        
    except Exception as e:
        logger.exception(f"Error in sales_timeseries: {e}")
        return []


def get_daily_summary_from_transactions(date):
    try:
        qs = DailySaleTransaction.objects.filter(date=date)
        agg = _aggregate_transactions(qs)
        code_summary = qs.values('code').annotate(
            total_sales=Sum('sales'),
            total_qty=Sum('qty'),
            transaction_count=Count('id')
        ).order_by('code')
        
        return {
            'date': date,
            'total_sales': agg['total_sales'],
            'total_discount': agg['total_discount'],
            'net_total': agg['net_total'],
            'total_paid': agg['total_paid'],
            'total_qty': agg['total_qty'],
            'transaction_count': agg['transaction_count'],
            'transactions': qs.order_by('-created_at'),
            'code_summary': list(code_summary),
        }
        
    except Exception as e:
        logger.exception(f"Error in get_daily_summary_from_transactions: {e}")
        return {
            'date': date,
            'total_sales': Decimal('0'),
            'total_discount': Decimal('0'),
            'net_total': Decimal('0'),
            'total_paid': Decimal('0'),
            'total_qty': 0,
            'transaction_count': 0,
            'transactions': [],
            'code_summary': [],
        }


def get_top_items(limit=10, start_date=None, end_date=None):
    try:
        qs = DailySaleTransaction.objects.filter(item__isnull=False)
        
        if start_date:
            qs = qs.filter(date__gte=start_date)
        if end_date:
            qs = qs.filter(date__lte=end_date)
        
        top_items = qs.values('item__id', 'item__product_name', 'item__code').annotate(
            total_qty=Sum('qty'),
            total_sales=Sum('sales'),
            transaction_count=Count('id')
        ).order_by('-total_sales')[:limit]
        
        return list(top_items)
        
    except Exception as e:
        logger.exception(f"Error in get_top_items: {e}")
        return []


def get_top_customers(limit=10, start_date=None, end_date=None):
    try:
        qs = DailySaleTransaction.objects.exclude(customer_name__isnull=True).exclude(customer_name='')
        
        if start_date:
            qs = qs.filter(date__gte=start_date)
        if end_date:
            qs = qs.filter(date__lte=end_date)
        
        top_customers = qs.values('customer_name').annotate(
            total_sales=Sum('sales'),
            net_total=Sum('sales') - Sum('discount'),
            total_paid=Sum('paid'),
            transaction_count=Count('id'),
            total_qty=Sum('qty')
        ).order_by('-net_total')[:limit]

        for customer in top_customers:
            if customer['net_total'] > 0:
                customer['paid_percentage'] = (customer['total_paid'] / customer['net_total'] * 100).quantize(Decimal('0.01'))
            else:
                customer['paid_percentage'] = Decimal('0')
        
        return list(top_customers)
        
    except Exception as e:
        logger.exception(f"Error in get_top_customers: {e}")
        return []


def update_inventory_stock(transaction, decrease=True):
    try:
        if transaction.item:
            if decrease:
                transaction.item.in_stock_qty -= transaction.qty
                transaction.item.total_sold_qty += transaction.qty
            else:
                transaction.item.in_stock_qty += transaction.qty
                transaction.item.total_sold_qty -= transaction.qty
            
            transaction.item.save(update_fields=['in_stock_qty', 'total_sold_qty'])
            logger.info(f"Stock updated for item {transaction.item.id}: new stock={transaction.item.in_stock_qty}")
            return True
            
    except Exception as e:
        logger.error(f"Error updating inventory stock: {e}")
    
    return False


def check_stock_availability(item_id, requested_qty):
    try:
        from containers.models import Inventory_List
        item = Inventory_List.objects.get(pk=item_id)
        return item.in_stock_qty >= requested_qty, item.in_stock_qty
    except Exception as e:
        logger.error(f"Error checking stock: {e}")
        return False, 0


def get_payment_status_stats(queryset=None):
    if queryset is None:
        queryset = DailySaleTransaction.objects.all()
    
    stats = {
        'paid': queryset.filter(payment_status='paid').count(),
        'partial': queryset.filter(payment_status='partial').count(),
        'unpaid': queryset.filter(payment_status='unpaid').count(),
    }
    
    stats['total'] = stats['paid'] + stats['partial'] + stats['unpaid']
    paid_amount = queryset.filter(payment_status='paid').aggregate(total=Sum('total'))['total'] or Decimal('0')
    partial_amount = queryset.filter(payment_status='partial').aggregate(total=Sum('balance'))['total'] or Decimal('0')
    unpaid_amount = queryset.filter(payment_status='unpaid').aggregate(total=Sum('total'))['total'] or Decimal('0')
    
    stats['paid_amount'] = paid_amount
    stats['partial_amount'] = partial_amount
    stats['unpaid_amount'] = unpaid_amount
    
    return stats


def parse_date_param(date_str):
    if not date_str:
        return None
    try:
        from datetime import datetime
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return None