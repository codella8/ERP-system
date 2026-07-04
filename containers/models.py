from django.db import models
from django.utils import timezone
from uuid import uuid4
from django.db.models import Sum
from django.core.validators import MinValueValidator
from decimal import Decimal

class Container(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    supplier = models.CharField(max_length=150, blank=True)
    container_no = models.CharField(max_length=64, unique=True, db_index=True)
    code = models.CharField(max_length=100, blank=True, null=True)
    arrival_date = models.CharField(max_length=50, blank=True, null=True)
    
    total_sales = models.DecimalField(max_digits=15, decimal_places=0, default=0)
    total_expenses = models.DecimalField(max_digits=15, decimal_places=0, default=0)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Container"
        verbose_name_plural = "Containers"

    @property
    def net_value(self):
        return (self.total_sales or 0) - (self.total_expenses or 0)

    def update_from_transactions(self):
        """به‌روزرسانی total_sales از DailySaleTransaction ها"""
        from daily_sale.models import DailySaleTransaction
        
        # ✅ حذف is_deleted
        total = DailySaleTransaction.objects.filter(
            container=self
        ).aggregate(total_sales=Sum('total'))['total_sales'] or 0
        
        if self.total_sales != total:
            self.total_sales = total
            self.save(update_fields=['total_sales', 'updated_at'])
        return self.total_sales

    def __str__(self):
        return f"{self.code} - {self.container_no}"
    
    def update_expenses(self):
        """به‌روزرسانی total_expenses از Expense های مرتبط"""
        from django.contrib.contenttypes.models import ContentType
        
        ct = ContentType.objects.get_for_model(self)
        total = Expense.objects.filter(
            content_type=ct,
            object_id=self.id
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        if self.total_expenses != total:
            self.total_expenses = total
            self.save(update_fields=['total_expenses', 'updated_at'])

class Inventory_List(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    product_name = models.CharField(max_length=255)
    code = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    container = models.ForeignKey(
        Container, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='inventory_items'
    )
    
    in_stock_qty = models.DecimalField(max_digits=18, decimal_places=0, default=0, validators=[MinValueValidator(0)])
    total_sold_qty = models.DecimalField(max_digits=18, decimal_places=0, default=0)
    
    unit_price = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    sold_price = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Inventory Item"
        verbose_name_plural = "Inventory Items"
        indexes = [models.Index(fields=['code']), models.Index(fields=['product_name'])]

    @property
    def in_stock(self):
        """موجودی فعلی"""
        return self.in_stock_qty - self.total_sold_qty

    @property
    def current_value(self):
        """ارزش کل موجودی"""
        return self.in_stock * self.unit_price

    @property
    def status(self):
        if self.in_stock <= 0:
            return 'sold_out'
        elif self.total_sold_qty > 0:
            return 'partial'
        else:
            return 'available'
    
    def get_status_display(self):
        status_map = {
            'available': '✅ Available',
            'partial': '⚠️ Partial',
            'sold_out': '❌ Sold Out',
        }
        return status_map.get(self.status, '📦 In Stock')


class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    date = models.CharField(max_length=50)
    description = models.CharField(max_length=255)
    rate = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    nzd = models.DecimalField(max_digits=15, decimal_places=3, default=0)
    paid_by = models.CharField(max_length=100, blank=True)
    received_by = models.CharField(max_length=100, blank=True)
    cash_in = models.DecimalField(max_digits=15, decimal_places=0, default=0, null=True, blank=True)
    cash_out = models.DecimalField(max_digits=15, decimal_places=0, default=0, null=True, blank=True)
    
    container = models.ForeignKey(
        Container, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='payments'
    )
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.date} - {self.description}"


class ExpenseCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        verbose_name = "Expense Category"
        verbose_name_plural = "Expense Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Expense(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    
    date = models.CharField(max_length=50, db_index=True)
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='expenses'
    )
    description = models.CharField(max_length=255)
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=0,
        default=0,
        validators=[MinValueValidator(0)]
    )
    notes = models.TextField(blank=True)
    
    # ارتباط با People
    paid_by = models.ForeignKey(
        'employee.Person',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='expenses_paid'
    )
    received_by = models.ForeignKey(
        'employee.Person',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='expenses_received'
    )
    
    # ارتباط با Container (اختیاری)
    container = models.ForeignKey(
        'Container',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='expenses'
    )
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Expense"
        verbose_name_plural = "Expenses"
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['category']),
        ]
    
    def __str__(self):
        return f"{self.date} - {self.category.name if self.category else 'No Category'} - {self.amount}"
    
    def save(self, *args, **kwargs):
        # اگر هزینه مربوط به کانتینر است، total_expenses را به‌روز کن
        if self.container and self.amount:
            container = self.container
            container.total_expenses = (container.total_expenses or 0) + self.amount
            container.save(update_fields=['total_expenses', 'updated_at'])
        super().save(*args, **kwargs)