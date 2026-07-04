from uuid import uuid4
from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from django.utils import timezone
from django.conf import settings
from django.core.validators import MinValueValidator
import logging

logger = logging.getLogger(__name__)


class DailySaleTransaction(models.Model):
    
    PAYMENT_STATUS_CHOICES = [
        ('unpaid', 'Unpaid'),
        ('partial', 'Partial'),
        ('paid', 'Paid'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    invoice_number = models.CharField(max_length=64, unique=True, blank=True, null=True, db_index=True)
    date = models.DateField(default=timezone.now, db_index=True)
    customer_name = models.CharField(max_length=255, blank=True, null=True)
    code = models.CharField(max_length=50, blank=True, null=True)
    item_description = models.CharField(max_length=500, blank=True, null=True)
    item = models.ForeignKey(
        'containers.Inventory_List',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="daily_sales"
    )
    container = models.ForeignKey(
        'containers.Container',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="daily_sales"
    )
    qty = models.IntegerField(default=1, validators=[MinValueValidator(0)])
    sales = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0'))
    paid = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0'))
    discount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0'))
    total = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0'))
    balance = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0'))
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='unpaid')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'daily_sale_transaction'
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['invoice_number']),
            models.Index(fields=['customer_name']),
            models.Index(fields=['code']),
            models.Index(fields=['item']),
            models.Index(fields=['container']),
        ]
    
    def __str__(self):
        return f"{self.invoice_number or 'INV'} | {self.date} | {self.customer_name}"
    
    def calculate_amounts(self):
        """محاسبه total و balance و payment_status"""
        total_calc = self.sales - self.discount
        if total_calc < 0:
            total_calc = Decimal('0')
        
        balance_calc = total_calc - self.paid
        if balance_calc < 0:
            balance_calc = Decimal('0')
        
        if balance_calc <= 0 and total_calc > 0:
            payment_status = 'paid'
        elif self.paid > 0:
            payment_status = 'partial'
        else:
            payment_status = 'unpaid'
        
        return {
            'total': total_calc.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'balance': balance_calc.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'payment_status': payment_status,
        }
    
    def update_inventory_stock(self, decrease=True):
        if self.item:
            if decrease:
                self.item.in_stock_qty -= self.qty
                self.item.total_sold_qty += self.qty
            else:
                self.item.in_stock_qty += self.qty
                self.item.total_sold_qty -= self.qty
            self.item.save(update_fields=['in_stock_qty', 'total_sold_qty'])
            logger.info(f"Stock updated for item {self.item.id}: new stock={self.item.in_stock_qty}")
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        amounts = self.calculate_amounts()
        self.total = amounts['total']
        self.balance = amounts['balance']
        self.payment_status = amounts['payment_status']
        if self.item and self.sales == 0:
            self.sales = self.item.unit_price * self.qty
        if not self.invoice_number:
            date_str = self.date.strftime('%Y%m%d')
            prefix = "INV"
            
            last_inv = DailySaleTransaction.objects.filter(
                invoice_number__startswith=f"{prefix}-{date_str}-"
            ).order_by('-invoice_number').first()
            
            if last_inv and last_inv.invoice_number:
                try:
                    last_num = int(last_inv.invoice_number.split('-')[-1])
                    new_num = last_num + 1
                except (ValueError, IndexError):
                    new_num = 1
            else:
                new_num = 1
            
            self.invoice_number = f"{prefix}-{date_str}-{new_num:04d}"
        
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
    
    @property
    def paid_percentage(self):
        if self.total > 0:
            return ((self.paid / self.total) * 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return Decimal('0')


class CodeSummary(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    date = models.DateField(db_index=True)
    code = models.CharField(max_length=50, db_index=True)
    product_name = models.CharField(max_length=255, blank=True, null=True)
    container_no = models.CharField(max_length=100, blank=True, null=True)
    total_sales = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    total_discount = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    total_paid = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    total_qty = models.IntegerField(default=0)
    transaction_count = models.IntegerField(default=0)
    not_sold = models.IntegerField(default=0)
    net_total = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    container_no = models.CharField(max_length=100, blank=True, null=True)
    item_id = models.UUIDField(null=True, blank=True)
    container_id = models.UUIDField(null=True, blank=True)
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [['date', 'code']]
        ordering = ['date', 'code']
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['code']),
        ]
    
    def __str__(self):
        return f"{self.date} - {self.code}: {self.net_total}"
    @classmethod
    def update_for_date(cls, date):
        from django.db.models import Sum, Count, Q
        from .models import DailySaleTransaction
        cls.objects.filter(date=date).delete()
        transactions = DailySaleTransaction.objects.filter(date=date).exclude(code__isnull=True).exclude(code='')
        
        if not transactions.exists():
            return []
        
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
            
            cls.objects.create(
                date=date,
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

   