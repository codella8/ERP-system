from uuid import uuid4
from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

class Person(models.Model):
    PERSON_TYPES = [
        ('employee', ' کارمند'),
        ('saraf', ' صراف'),
        
    ]
    STATUS_CHOICES = [
        ('active', ' فعال'),
        ('inactive', ' غیرفعال'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    person_type = models.CharField(max_length=20, choices=PERSON_TYPES, verbose_name="نوع شخص")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name="وضعیت")
    
    # اطلاعات پایه
    name = models.CharField(max_length=200, verbose_name="نام و نام خانوادگی")
    phone = models.CharField(max_length=50, blank=True, verbose_name="شماره تماس")
    email = models.EmailField(blank=True, verbose_name="ایمیل")
    address = models.TextField(blank=True, verbose_name="آدرس")
    
    # اطلاعات مالی مشترک
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="مانده حساب")
    
    # فیلدهای مخصوص کارمند
    salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="حقوق")
    department = models.CharField(max_length=100, blank=True, verbose_name="دپارتمان")
    hire_date = models.DateField(null=True, blank=True, verbose_name="تاریخ استخدام")
    
    # فیلدهای مخصوص صراف
    license_number = models.CharField(max_length=100, blank=True, verbose_name="شماره مجوز")
    commission_rate = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="درصد کمیسیون"
    )
    
    # تاریخ‌ها
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")
    
    class Meta:
        verbose_name = "شخص"
        verbose_name_plural = "اشخاص"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['person_type']),
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return f"{self.get_person_type_display()} - {self.name}"
    
    @property
    def is_employee(self):
        return self.person_type == 'employee'
    
    @property
    def is_saraf(self):
        return self.person_type == 'saraf'


class SarafTransaction(models.Model):
    TRANSACTION_CATEGORIES = [
        ('buy', 'خرید ارز'),
        ('sell', 'فروش ارز'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    
    # ارتباط با صراف (اختیاری - برای گزارشات)
    saraf = models.ForeignKey(
        Person, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        limit_choices_to={'person_type': 'saraf'},
        verbose_name="صراف",
        related_name='transactions'
    )
    
    # تاریخ (مطابق خواسته کارفرما)
    day = models.CharField(max_length=150, blank=True, verbose_name="روز")
    date = models.DateField(default=timezone.now, db_index=True, verbose_name="تاریخ")
    
    # توضیحات
    description = models.TextField(blank=True, verbose_name="شرح تراکنش")
    
    # طرفین تراکنش (متن آزاد برای انعطاف بیشتر)
    paid_by = models.CharField(max_length=150, blank=True, verbose_name="پرداخت کننده")
    received_by = models.CharField(max_length=150, blank=True, verbose_name="دریافت کننده")
    
    # دسته‌بندی
    category = models.CharField(
        max_length=50, 
        choices=TRANSACTION_CATEGORIES,
        default='other',
        verbose_name="دسته‌بندی"
    )
    
    # مقادیر مالی
    cash_in = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="ورودی")
    cash_out = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="خروجی")
    
    # تاریخ‌ها
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")

    class Meta:
        verbose_name = "تراکنش صرافی"
        verbose_name_plural = "تراکنش‌های صرافی"
        ordering = ["-date", "-created_at"]
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return f"{self.date} - {self.get_category_display()} - {self.description[:30]}"
    
    @property
    def balance(self):
        """محاسبه خودکار مانده"""
        return self.cash_in - self.cash_out
    
    @property
    def balance_display(self):
        """نمایش مانده با رنگ مناسب"""
        balance = self.balance
        if balance > 0:
            return f"{balance:,.0f}"
        elif balance < 0:
            return f" {balance:,.0f}"
        return f" {balance:,.0f}"
    
    def save(self, *args, **kwargs):
        if not self.day and self.date:
            pass
        super().save(*args, **kwargs)

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver([post_save, post_delete], sender=SarafTransaction)
def update_person_balance(sender, instance, **kwargs):
    """بروزرسانی خودکار balance صراف بعد از هر تراکنش"""
    if instance.saraf:
        transactions = SarafTransaction.objects.filter(saraf=instance.saraf)
        total_balance = sum(t.balance for t in transactions)
        instance.saraf.balance = total_balance
        instance.saraf.save()