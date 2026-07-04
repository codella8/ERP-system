# daily_sale/apps.py
from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class DailySaleConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'daily_sale'
    
    def ready(self):
        import daily_sale.signals
        logger.info(" DailySale signals registered")