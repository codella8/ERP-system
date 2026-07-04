# containers/signals.py
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
import logging
from .models import Inventory_List, Container

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Inventory_List)
def validate_inventory_before_save(sender, instance, **kwargs):
    """اعتبارسنجی قبل از ذخیره موجودی (بدون شرط اضافی)"""
    if instance.in_stock_qty < 0:
        raise ValidationError("Quantity cannot be negative")
    
    if instance.total_sold_qty < 0:
        raise ValidationError("Sold quantity cannot be negative")
    
    if instance.unit_price < 0:
        raise ValidationError("Unit price cannot be negative")
    
    # ✅ فقط بررسی کن که فروش از کل موجودی بیشتر نباشد
    total_initial = instance.in_stock_qty + instance.total_sold_qty
    if instance.total_sold_qty > total_initial:
        raise ValidationError(
            f"Sold quantity ({instance.total_sold_qty}) cannot exceed total quantity ({total_initial})"
        )


@receiver(pre_save, sender=Container)
def validate_container_before_save(sender, instance, **kwargs):
    """اعتبارسنجی قبل از ذخیره کانتینر"""
    if instance.total_expenses and instance.total_expenses < 0:
        raise ValidationError("Total expenses cannot be negative")
    
    if instance.total_sales and instance.total_sales < 0:
        raise ValidationError("Total sales cannot be negative")