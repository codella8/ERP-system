# daily_sale/forms.py
from django import forms
from decimal import Decimal
from django.utils import timezone
from . import models
from .models import DailySaleTransaction
from containers.models import Inventory_List, Container


class DailySaleTransactionForm(forms.ModelForm):
    item_search = forms.CharField(
        required=False,
        label="Item",
        widget=forms.TextInput(attrs={
            'class': 'form-control item-search',
            'placeholder': 'Search item by name or code...',
            'autocomplete': 'off'
        })
    )
    container_search = forms.CharField(
        required=False,
        label="Container",
        widget=forms.TextInput(attrs={
            'class': 'form-control container-search',
            'placeholder': 'Search container...',
            'autocomplete': 'off'
        })
    )
    
    class Meta:
        model = DailySaleTransaction
        fields = [
            'date',
            'customer_name',
            'invoice_number',
            'code',
            'item_description',
            'qty',
            'sales',
            'paid',
            'discount',
        ]
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'required': True
            }),
            'customer_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter customer name',
                'required': True
            }),
            'invoice_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Auto-generated',
                'readonly': True
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Item code'
            }),
            'item_description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Item description'
            }),
            'qty': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'step': '1',
                'value': '1',
                'required': True
            }),
            'sales': forms.NumberInput(attrs={
                'class': 'form-control sales-input',
                'min': '0',
                'step': '0.01',
                'value': '0',
                'required': True
            }),
            'paid': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01',
                'value': '0',
                'required': True
            }),
            'discount': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01',
                'value': '0'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
        if not self.instance.pk: 
            self.fields['date'].initial = timezone.now().date()
            self.fields['qty'].initial = 1
            self.fields['sales'].initial = Decimal('0.00')
            self.fields['paid'].initial = Decimal('0.00')
            self.fields['discount'].initial = Decimal('0.00')
        if self.instance and self.instance.pk and self.instance.item:
            self.fields['item_search'].initial = self.instance.item.product_name
            if self.instance.container:
                self.fields['container_search'].initial = self.instance.container.container_no
    
    def clean(self):
        cleaned_data = super().clean()
         
        qty = cleaned_data.get('qty') or 1
        sales = cleaned_data.get('sales') or Decimal('0')
        paid = cleaned_data.get('paid') or Decimal('0')
        discount = cleaned_data.get('discount') or Decimal('0')
        
        if qty <= 0:
            self.add_error('qty', 'QTY must be greater than 0')
        
        if sales < 0:
            self.add_error('sales', 'Sales cannot be negative')
        
        if paid < 0:
            self.add_error('paid', 'Paid cannot be negative')
        
        if discount < 0:
            self.add_error('discount', 'Discount cannot be negative')
        
        if discount > sales:
            self.add_error('discount', 'Discount cannot be greater than Sales')
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        item_search = self.cleaned_data.get('item_search')
        container_search = self.cleaned_data.get('container_search')
        if item_search:
            try:
                item = Inventory_List.objects.filter(
                    models.Q(product_name__iexact=item_search) |
                    models.Q(code__iexact=item_search)
                ).first()
                
                if item:
                    instance.item = item
                    if not instance.code:
                        instance.code = item.code
                    if not instance.item_description:
                        instance.item_description = item.product_name
                    
                    if instance.sales == 0:
                        instance.sales = item.unit_price * instance.qty
                        
            except Exception as e:
                pass
    
        if container_search:
            try:
                container = Container.objects.filter(
                    models.Q(container_no__iexact=container_search) |
                    models.Q(code__iexact=container_search)
                ).first()
                
                if container:
                    instance.container = container
            except Exception as e:
                pass
        
        if commit:
            instance.save()
        
        return instance


class TransactionFilterForm(forms.Form):
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by customer, invoice, code...'
        })
    )
    payment_status = forms.ChoiceField(
        required=False,
        choices=[('', 'All')] + DailySaleTransaction.PAYMENT_STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    per_page = forms.ChoiceField(
        required=False,
        choices=[(25, '25'), (50, '50'), (100, '100'), (250, '250')],
        initial=25,
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class QuickSaleForm(forms.Form):
    customer_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Customer name',
            'required': True
        })
    )
    code = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Code'
        })
    )
    item_description = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Item description'
        })
    )
    qty = forms.IntegerField(
        initial=1,
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'value': '1'
        })
    )
    sales = forms.DecimalField(
        initial=0,
        min_value=0,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control sales-input',
            'step': '0.01'
        })
    )
    paid = forms.DecimalField(
        initial=0,
        min_value=0,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01'
        })
    )
    discount = forms.DecimalField(
        initial=0,
        min_value=0,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        sales = cleaned_data.get('sales') or Decimal('0')
        discount = cleaned_data.get('discount') or Decimal('0')
        
        if discount > sales:
            self.add_error('discount', 'Discount cannot be greater than Sales')
        
        return cleaned_data