# reports/models.py
from django.db import models
from django.utils import timezone
from uuid import uuid4
from decimal import Decimal

class ProfitLossReport(models.Model):
    """ذخیره گزارش‌های سود و زیان برای مقایسه دوره‌ای"""
    
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    period_start = models.DateField()
    period_end = models.DateField()
    period_type = models.CharField(max_length=20, choices=[
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ])
    
    # درآمدها
    total_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    sales_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    other_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # هزینه‌ها
    total_expenses = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    container_expenses = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    shipping_expenses = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    other_expenses = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # سود
    gross_profit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    net_profit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-period_start']
        unique_together = ['period_start', 'period_end']
    
    def __str__(self):
        return f"{self.period_type} - {self.period_start} to {self.period_end}"