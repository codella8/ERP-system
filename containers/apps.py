# containers/apps.py
from django.apps import AppConfig


class ContainersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'containers'
    verbose_name = 'Container Management'

    def ready(self):
        """
        وقتی اپلیکیشن آماده میشه، سیگنال‌ها رو ایمپورت کن
        """
        import containers.signals  # noqa
        
        try:
            from containers.signals import connect_daily_sale_signals
            connect_daily_sale_signals()
        except:
            pass