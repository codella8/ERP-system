# containers/apps.py
from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class ContainersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'containers'
    
    def ready(self):
        import containers.signals
        logger.info("✅ Containers signals registered")