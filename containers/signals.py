# containers/signals.py
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from decimal import Decimal
import logging
from django.db.models import F
from .models import Inventory_List

logger = logging.getLogger(__name__)


# سیگنال‌های مربوط به Inventory_List


@receiver(pre_save, sender='containers.Inventory_List')
def validate_inventory_before_save(sender, instance, **kwargs):
    """اعتبارسنجی قبل از ذخیره موجودی"""
    if instance.in_stock_qty < 0:
        raise ValidationError("Quantity cannot be negative")
    
    if instance.total_sold_qty < 0:
        raise ValidationError("Sold quantity cannot be negative")
    
    if instance.total_sold_qty > instance.in_stock_qty:
        raise ValidationError(
            f"Sold quantity ({instance.total_sold_qty}) cannot exceed total quantity ({instance.in_stock_qty})"
        )
    
    if instance.unit_price < 0:
        raise ValidationError("Unit price cannot be negative")


@receiver(post_save, sender='containers.Inventory_List')
def update_container_on_inventory_change(sender, instance, created, **kwargs):
    """بروزرسانی خودکار کانتینر وقتی موجودی تغییر میکنه"""
    if instance.container:
        container = instance.container
        
        # محاسبه مجموع فروش از همه آیتم‌های این کانتینر
        from django.db.models import Sum, F
        total_sales = container.inventory_items.aggregate(
            total=Sum(F('total_sold_qty') * F('unit_price'))
        )['total'] or 0
        
        # محاسبه مجموع ارزش موجودی
        total_inventory_value = container.inventory_items.aggregate(
            total=Sum(F('in_stock_qty') * F('unit_price'))
        )['total'] or 0
        
        container.total_sales = total_sales
        container.save(update_fields=['total_sales', 'updated_at'])
        
        logger.info(f"Container {container.container_number} total_sales updated to {total_sales}")



# سیگنال‌های ارتباط با daily_sale


# containers/signals.py باید این تابع رو داشته باشه:

def update_inventory_from_daily_sale(sender, instance, created, **kwargs):
    """وقتی تراکنشی در daily_sale ثبت میشه، موجودی کم میشه"""
    try:
        if hasattr(instance, 'item') and instance.item:
            inventory_item = Inventory_List.objects.filter(
                code=instance.item.code,
                product_name__icontains=instance.item.product_name
            ).first()
            
            if inventory_item:
                inventory_item.total_sold_qty += instance.quantity
                inventory_item.save()
                logger.info(f"✅ Inventory updated: {inventory_item.product_name} - sold {instance.quantity}")
                
    except Exception as e:
        logger.error(f"❌ Error updating inventory: {str(e)}")


def rollback_inventory_from_daily_sale(sender, instance, **kwargs):
    """
    برگردوندن موجودی وقتی تراکنشی در daily_sale حذف میشه
    """
    try:
        if hasattr(instance, 'item') and instance.item and instance.item.container:
            
            inventory_item = instance.item.container.inventory_items.filter(
                product_name__iexact=instance.item.product_name
            ).first()
            
            if inventory_item:
                quantity = instance.quantity or 1
                
                # برگردوندن موجودی
                inventory_item.total_sold_qty = max(inventory_item.total_sold_qty - quantity, 0)
                inventory_item.total_sold_count = max(inventory_item.total_sold_count - 1, 0)
                inventory_item.save()
                
                # برگردوندن total_sales کانتینر
                if inventory_item.container:
                    inventory_item.container.total_sales = max(
                        (inventory_item.container.total_sales or 0) - (instance.unit_price * quantity),
                        0
                    )
                    inventory_item.container.save()
                
                logger.info(f"Inventory rollback: {inventory_item.product_name} - returned {quantity}")
                
    except Exception as e:
        logger.error(f"Error in rollback_inventory_from_daily_sale: {str(e)}")



# سیگنال‌های مربوط به Container


@receiver(pre_save, sender='containers.Container')
def validate_container_before_save(sender, instance, **kwargs):
    """اعتبارسنجی قبل از ذخیره کانتینر"""
    if instance.total_expenses and instance.total_expenses < 0:
        raise ValidationError("Total expenses cannot be negative")
    
    if instance.total_sales and instance.total_sales < 0:
        raise ValidationError("Total sales cannot be negative")


@receiver(post_save, sender='containers.Container')
def container_post_save(sender, instance, created, **kwargs):
    """بعد از ذخیره کانتینر"""
    if created:
        logger.info(f"New container created: {instance.container_number}")
    else:
        logger.info(f"Container updated: {instance.container_number}")



# اتصال سیگنال‌ها به daily_sale (این تابع در apps.py صدا زده میشه)


def connect_daily_sale_signals():
    """اتصال سیگنال‌های daily_sale به containers"""
    try:
        from daily_sale.models import DailySaleTransaction
        from django.db.models.signals import post_save, post_delete
        
        # اتصال سیگنال‌ها
        post_save.connect(
            update_inventory_from_daily_sale,
            sender=DailySaleTransaction,
            dispatch_uid='update_inventory_from_daily_sale'
        )
        
        post_delete.connect(
            rollback_inventory_from_daily_sale,
            sender=DailySaleTransaction,
            dispatch_uid='rollback_inventory_from_daily_sale'
        )
        
        logger.info("✅ Daily sale signals connected to containers")
        
    except ImportError:
        logger.warning("⚠️ Daily sale app not available")
    except Exception as e:
        logger.error(f"❌ Error connecting daily sale signals: {str(e)}")