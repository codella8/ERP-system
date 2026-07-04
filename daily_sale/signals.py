# daily_sale/signals.py
import logging
from decimal import Decimal
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Sum
from .models import DailySaleTransaction, CodeSummary

logger = logging.getLogger(__name__)


@receiver(post_save, sender=DailySaleTransaction)
def transaction_post_save(sender, instance, created, **kwargs):
    try:
        logger.info(f" Processing transaction: {instance.invoice_number}")
        
        if instance.item and instance.qty > 0: 
            new_in_stock = instance.item.in_stock_qty - instance.qty
            new_sold = instance.item.total_sold_qty + instance.qty
            
            if new_in_stock < 0:
                logger.error(f"Not enough stock! Item: {instance.item.product_name}, Available: {instance.item.in_stock_qty}, Requested: {instance.qty}")
                return
            
            instance.item.in_stock_qty = new_in_stock
            instance.item.total_sold_qty = new_sold
            instance.item.save(update_fields=['in_stock_qty', 'total_sold_qty', 'updated_at'])
            logger.info(f"Stock updated: {instance.item.product_name} -> In Stock: {new_in_stock}, Sold: {new_sold}")
        elif instance.item and instance.qty == 0:
            logger.info(f"ℹQTY is zero, no stock change for {instance.item.product_name}")
        else:
            logger.warning(f"No item associated with transaction {instance.invoice_number}")
        if instance.container:
            total_sales = DailySaleTransaction.objects.filter(
                container=instance.container
            ).aggregate(total=Sum('total'))['total'] or Decimal('0')
            
            if instance.container.total_sales != total_sales:
                instance.container.total_sales = total_sales
                instance.container.save(update_fields=['total_sales', 'updated_at'])
                logger.info(f"Container {instance.container.container_no} total_sales updated to {total_sales}")
        else:
            logger.warning(f"No container associated with transaction {instance.invoice_number}")
        
        # ============================================================
        # 3. update CodeSummary
        # ============================================================
        CodeSummary.update_for_date(instance.date)
        logger.info(f"CodeSummary updated for {instance.date}")
        
        logger.info(f"Transaction {instance.invoice_number} processed successfully")
        
    except Exception as e:
        logger.error(f"Error in transaction_post_save: {e}")


@receiver(post_delete, sender=DailySaleTransaction)
def transaction_post_delete(sender, instance, **kwargs):
    try:
        logger.info(f"Deleting transaction: {instance.invoice_number}")
        if instance.item:
            instance.item.in_stock_qty += instance.qty
            instance.item.total_sold_qty -= instance.qty
            instance.item.save(update_fields=['in_stock_qty', 'total_sold_qty', 'updated_at'])
            logger.info(f"🔄 Stock restored: {instance.item.product_name} -> In Stock: {instance.item.in_stock_qty}")
        
        # به‌روزرسانی total_sales کانتینر
        if instance.container:
            total_sales = DailySaleTransaction.objects.filter(
                container=instance.container
            ).aggregate(total=Sum('total'))['total'] or Decimal('0')
            
            instance.container.total_sales = total_sales
            instance.container.save(update_fields=['total_sales', 'updated_at'])
            logger.info(f"✅ Container {instance.container.container_no} total_sales updated to {total_sales}")
        CodeSummary.update_for_date(instance.date)
        logger.info(f"✅ CodeSummary updated for {instance.date}")
        
        logger.info(f"✅ Transaction {instance.invoice_number} deleted successfully")
        
    except Exception as e:
        logger.error(f"❌ Error in transaction_post_delete: {e}")