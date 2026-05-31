from uuid import uuid4
from decimal import Decimal
from django.db import models
from django.db.models import Sum, F
from django.utils import timezone
from django.core.validators import MinValueValidator
from accounts.models import Company, UserProfile

class Container(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    container_number = models.CharField(max_length=64, unique=True, db_index=True)
    container_product = models.CharField(max_length=100, blank=True, null=True)
    code = models.CharField(max_length=100, blank=True, null=True)
    name = models.CharField(max_length=150, blank=True)
    price = models.DecimalField(max_digits=15, decimal_places=0, default=0)
    
    # فیلدهای جدید
    date = models.DateField(default=timezone.now, db_index=True, null=True, blank=True)
    arrival_date = models.DateField(null=True, blank=True)
    supplier = models.CharField(max_length=150, blank=True)
    total_expenses = models.DecimalField(max_digits=15, decimal_places=2, default=0, null=True, blank=True)
    total_sales = models.DecimalField(max_digits=15, decimal_places=2, default=0, null=True, blank=True)
    
    # وضعیت‌ها
    transport_status = models.CharField(
        max_length=32, 
        choices=[("pending", "Pending"), ("in_transit", "In Transit"), ("in_stock", "In Stock")], 
        default="pending",
        null=True, blank=True
    )
    sale_status = models.CharField(
        max_length=32, 
        choices=[("in_store", "In Store"), ("sold_to_company", "Sold to Company"), ("sold_to_customer", "Sold to Customer")], 
        default="in_store",
        null=True, blank=True
    )
    payment_status = models.CharField(
        max_length=32, 
        choices=[("pending", "Pending"), ("paid", "Paid"), ("partial", "Partial"), ("cancelled", "Cancelled")], 
        default="pending",
        null=True, blank=True
    )
    
    company = models.ForeignKey(
        Company, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="company"
    )
    
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name = "Container"
        verbose_name_plural = "Containers"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.container_number} - {self.name}"
    
    @property
    def total_inventory_value(self):
        """ارزش کل موجودی کانتینر (یکبار تعریف شده)"""
        total = self.inventory_items.aggregate(
            total=Sum(F('in_stock_qty') * F('unit_price'))
        )['total'] or 0
        return total
    
    @property
    def profit(self):
        """محاسبه سود/زیان"""
        return (self.total_sales or 0) - (self.total_expenses or 0)
    
    @property
    def item_count(self):
        """تعداد آیتم‌های داخل کانتینر"""
        return self.inventory_items.count()


CURRENCY_CHOICES = [
    ("usd", "USD"),
    ("eur", "EUR"),
    ("aed", "AED"),
]

class Inventory_List(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('partial', 'Partial'),
        ('sold_out', 'Sold Out'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    container = models.ForeignKey(
        Container, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='inventory_items'
    )
    date_added = models.DateField(default=timezone.now, db_index=True)
    code = models.CharField(max_length=64, blank=True, db_index=True)
    product_name = models.CharField(max_length=255)
    make = models.CharField(max_length=120, blank=True)
    model = models.CharField(max_length=120, blank=True)
    
    # فیلدهای موجودی (همه حفظ شده)
    in_stock_qty = models.DecimalField(max_digits=18, decimal_places=0, default=0, validators=[MinValueValidator(0)])
    unit_price = models.DecimalField(max_digits=14, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    price = models.DecimalField(max_digits=14, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    sold_price = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    
    # آمار فروش
    total_sold_qty = models.DecimalField(max_digits=18, decimal_places=0, default=0)
    total_sold_count = models.PositiveIntegerField(default=0)
    
    # فیلدهای جدید برای سازگاری (اختیاری)
    qty = models.DecimalField(max_digits=18, decimal_places=0, default=0, null=True, blank=True)  # معادل in_stock_qty
    qty_sold = models.DecimalField(max_digits=18, decimal_places=0, default=0, null=True, blank=True)  # معادل total_sold_qty
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='available',
        null=True, blank=True
    )
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Inventory Item" 
        verbose_name_plural = "Inventory Items"
        indexes = [
            models.Index(fields=['code']), 
            models.Index(fields=['product_name'])
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.product_name} - {self.code or 'No Code'}"
    
    @property
    def in_stock(self):
        """موجودی فعلی (محاسبه خودکار)"""
        return self.in_stock_qty - self.total_sold_qty
    
    @property
    def total_value(self):
        """ارزش کل آیتم بر اساس موجودی"""
        return self.in_stock_qty * self.unit_price
    
    @property
    def sold_value(self):
        """ارزش فروش رفته"""
        return self.total_sold_qty * (self.sold_price or self.unit_price)
    
    @property
    def remaining_value(self):
        """ارزش باقیمانده"""
        return self.in_stock * self.unit_price
    
    def update_status(self):
        """بروزرسانی خودکار وضعیت بر اساس موجودی"""
        if self.total_sold_qty >= self.in_stock_qty and self.in_stock_qty > 0:
            self.status = 'sold_out'
        elif self.total_sold_qty > 0:
            self.status = 'partial'
        else:
            self.status = 'available'
    
    def save(self, *args, **kwargs):
        # همگام‌سازی فیلدهای جدید با قدیمی (برای سازگاری)
        if self.qty is None:
            self.qty = self.in_stock_qty
        if self.qty_sold is None:
            self.qty_sold = self.total_sold_qty
        
        self.update_status()
        super().save(*args, **kwargs)


class ContainerTransaction(models.Model):
    SALE_STATUS = [
        ("in_store", "In Store"),
        ("sold_to_company", "Sold to Company"),
        ("sold_to_customer", "Sold to Customer"),
    ]

    TRANSPORT_STATUS = [
        ("pending", "Pending"),
        ("in_transit", "In Transit"),
        ("in_stock", "In Stock"),
    ]

    PAYMENT_STATUS = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("partial", "Partial"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    container = models.ForeignKey(
        Container, on_delete=models.CASCADE, related_name="transactions"
    )
    customer = models.ForeignKey(
        UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="purchases"
    )
    company = models.ForeignKey(
        Company, on_delete=models.SET_NULL, null=True, blank=True, related_name="container_transactions"
    )

    product = models.CharField(max_length=255, blank=True)
    quantity = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Quantity of product involved in this transaction"
    )
    port_of_origin = models.CharField(max_length=255, blank=True)
    port_of_discharge = models.CharField(max_length=255, blank=True)
    total_price = models.DecimalField(max_digits=14, decimal_places=0, validators=[MinValueValidator(0)], null=True, blank=True)

    sale_status = models.CharField(max_length=32, choices=SALE_STATUS, default="in_store")
    transport_status = models.CharField(max_length=32, choices=TRANSPORT_STATUS, default="pending")
    payment_status = models.CharField(max_length=32, choices=PAYMENT_STATUS, default="pending")

    arrival_date = models.DateField(null=True, blank=True)
    arrived_date = models.DateField(null=True, blank=True)

    note = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name = "Container Transaction"
        verbose_name_plural = "Container Transactions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["transport_status"]),
            models.Index(fields=["arrival_date"]),
            models.Index(fields=["arrived_date"]),
        ]

    def __str__(self):
        return f"{self.container.container_number} | {self.product} | {self.sale_status}"

    def save(self, *args, **kwargs):
        # منطق به‌روزرسانی موجودی
        if self.sale_status in ["sold_to_company", "sold_to_customer"]:
            try:
                inventory_item = Inventory_List.objects.filter(container=self.container).first()
                if inventory_item and inventory_item.in_stock_qty >= self.quantity:
                    inventory_item.in_stock_qty -= self.quantity
                    if self.quantity > 0 and self.total_price:
                        inventory_item.sold_price = self.total_price / self.quantity
                    inventory_item.total_sold_qty += self.quantity
                    inventory_item.total_sold_count += 1
                    inventory_item.qty_sold = inventory_item.total_sold_qty
                    inventory_item.save()
                    
                    # بروزرسانی total_sales کانتینر
                    if self.container:
                        self.container.total_sales = (self.container.total_sales or 0) + (self.total_price or 0)
                        self.container.save()
            except Inventory_List.DoesNotExist:
                pass

        super().save(*args, **kwargs)