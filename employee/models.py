from uuid import uuid4
from decimal import Decimal
from django.db import models
from django.utils import timezone

class Person(models.Model):
    PERSON_TYPES = [
        ('employee', 'Employee'),
        ('saraf', 'saraf'),
    ]
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    person_type = models.CharField(max_length=20, choices=PERSON_TYPES, default='employee')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_person_type_display()} - {self.name}"
    
    @property
    def is_employee(self):
        return self.person_type == 'employee'
    
    @property
    def is_saraf(self):
        return self.person_type == 'saraf'


class PersonTransaction(models.Model):
    
    CATEGORY_CHOICES = [
        ('salary', 'Salary'),
        ('deposit', 'Deposit'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    day = models.CharField(max_length=50, blank=True)           # Day
    date = models.DateField(default=timezone.now)               # Date
    description = models.TextField(blank=True)                  # Description
    paid_by = models.CharField(max_length=150, blank=True)      # Paid by
    received_by = models.CharField(max_length=150, blank=True)  # Received by
    category = models.CharField(                                # Category
        max_length=50,
        choices=CATEGORY_CHOICES,
        default='other'
    )
    cash_in = models.DecimalField(max_digits=15, decimal_places=2, default=0)    # Cash-In
    cash_out = models.DecimalField(max_digits=15, decimal_places=2, default=0)   # Cash-Out
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.person.name} - {self.date} - {self.description[:30]}"
    
    @property
    def balance(self):
        return self.cash_in - self.cash_out
    
    def save(self, *args, **kwargs):
        if not self.day and self.date:
            self.day = self.date.strftime("%A")
        super().save(*args, **kwargs)

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver([post_save, post_delete], sender=PersonTransaction)
def update_person_balance(sender, instance, **kwargs):
    if instance.person:
        transactions = PersonTransaction.objects.filter(person=instance.person)
        total_balance = sum(t.balance for t in transactions)
        instance.person.balance = total_balance
        instance.person.save(update_fields=['balance'])