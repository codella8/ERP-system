from decimal import Decimal, ROUND_HALF_UP
import logging
from django.db.models import Sum, Count, Q

logger = logging.getLogger(__name__)


class CalculationService:
    
    @staticmethod
    def calculate_transaction_amounts(sales, discount, paid):
        sales_amount = Decimal(str(sales)) if sales else Decimal('0')
        discount_amount = Decimal(str(discount)) if discount else Decimal('0')
        paid_amount = Decimal(str(paid)) if paid else Decimal('0')
        total = (sales_amount - discount_amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if total < 0:
            total = Decimal('0')
        balance = (total - paid_amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if balance < 0:
            balance = Decimal('0')
        if balance <= 0 and total > 0:
            payment_status = "paid"
        elif paid_amount > 0:
            payment_status = "partial"
        else:
            payment_status = "unpaid"
        
        return {
            "total": total,
            "balance": balance,
            "payment_status": payment_status,
        }
    
    @staticmethod
    def validate_transaction_data(sales, discount, paid):
        if sales < 0:
            return False, "Sales cannot be negative"
        if discount < 0:
            return False, "Discount cannot be negative"
        if discount > sales:
            return False, "Discount cannot be greater than Sales"
        if paid < 0:
            return False, "Paid cannot be negative"
        return True, "OK"


class SummaryService:
    
    @staticmethod
    def get_transaction_stats(queryset):
        total_sales = queryset.aggregate(total=Sum('sales'))['total'] or Decimal('0')
        total_discount = queryset.aggregate(total=Sum('discount'))['total'] or Decimal('0')
        total_paid = queryset.aggregate(total=Sum('paid'))['total'] or Decimal('0')
        total_qty = queryset.aggregate(total=Sum('qty'))['total'] or 0
        transaction_count = queryset.count()
        
        net_total = total_sales - total_discount
        if net_total < 0:
            net_total = Decimal('0')
        
        avg_transaction = Decimal('0')
        if transaction_count > 0:
            avg_transaction = (net_total / transaction_count).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        return {
            'total_sales': total_sales,
            'total_discount': total_discount,
            'net_total': net_total,
            'total_paid': total_paid,
            'total_qty': total_qty,
            'transaction_count': transaction_count,
            'avg_transaction': avg_transaction,
        }
    
    @staticmethod
    def get_daily_summary(queryset, date):
        day_transactions = queryset.filter(date=date)
        
        sales_sum = day_transactions.aggregate(
            total_sales=Sum('sales'),
            total_discount=Sum('discount'),
            total_paid=Sum('paid'),
            total_qty=Sum('qty'),
            transaction_count=Count('id')
        )
        
        total_sales = sales_sum['total_sales'] or Decimal('0')
        total_discount = sales_sum['total_discount'] or Decimal('0')
        net_total = total_sales - total_discount
        if net_total < 0:
            net_total = Decimal('0')
        
        return {
            'date': date,
            'total_sales': total_sales,
            'total_discount': total_discount,
            'net_total': net_total,
            'total_paid': sales_sum['total_paid'] or Decimal('0'),
            'total_qty': sales_sum['total_qty'] or 0,
            'transaction_count': sales_sum['transaction_count'] or 0,
            'transactions': day_transactions.order_by('-created_at'),
        }
    
    @staticmethod
    def get_code_summary(queryset, date=None):
        qs = queryset
        if date:
            qs = qs.filter(date=date)
        
        summary = qs.values('code').annotate(
            total_sales=Sum('sales'),
            total_qty=Sum('qty'),
            transaction_count=Count('id'),
            not_sold=Count('id', filter=Q(sales=0) | Q(qty=0))
        ).order_by('code')
        
        for item in summary:
            item['net_total'] = item['total_sales'] or Decimal('0')
        
        return summary 