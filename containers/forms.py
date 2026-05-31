# forms.py
from django import forms
from django.core.exceptions import ValidationError
from .models import Container, Inventory_List, Company
from decimal import Decimal

class ContainerForm(forms.ModelForm):
    transport_company = forms.ModelChoiceField(
        queryset=Company.objects.all(),
        required=False,
        empty_label="Select Transport Company",
        widget=forms.Select(attrs={
            'class': 'form-control excel-select',
            'data-field': 'transport_company'
        })
    )
    
    class Meta:
        model = Container
        fields = [
            'container_number',  # Container Name/Number
            'name',              
            'code',              
            'arrival_date',       # Arrival Date
            'transport_status',   # Status (In Transit, Arrived)
            'supplier',           # Transport Company
            'description',        
        ]
        widgets = {
            'container_number': forms.TextInput(attrs={
                'class': 'form-control excel-input',
                'placeholder': 'e.g., CNT-001',
                'data-field': 'container_number',
                'autofocus': True
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control excel-input',
                'placeholder': 'Container name (optional)',
                'data-field': 'name'
            }),
            'code': forms.TextInput(attrs={ 
                'class': 'form-control excel-input',
                'placeholder': 'e.g., G50',
                'data-field': 'code'
            }),
            'arrival_date': forms.DateInput(attrs={
                'class': 'form-control excel-input',
                'type': 'date',
                'data-field': 'arrival_date'
            }),
            'transport_status': forms.Select(attrs={
                'class': 'form-control excel-select',
                'data-field': 'transport_status'
            }),
            'supplier': forms.TextInput(attrs={
                'class': 'form-control excel-input',
                'placeholder': 'Transport company name',
                'data-field': 'supplier'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control excel-input',
                'rows': 2,
                'placeholder': 'Additional notes...',
                'data-field': 'description'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # تنظیم وضعیت‌های حمل و نقل 
        self.fields['transport_status'].choices = [
            ('in_transit', ' In Transit'),
            ('arrived', ' Arrived'),
            ('awaiting', ' Awaiting'),
            ('cleared', ' Cleared'),
        ]
        self.fields['transport_status'].initial = 'awaiting'
        
        # برچسب‌ها
        self.fields['container_number'].label = 'Container Number'
        self.fields['name'].label = 'Container Name (Optional)'
        self.fields['code'].label = 'Code'  
        self.fields['arrival_date'].label = 'Arrival Date'
        self.fields['transport_status'].label = 'Status'
        self.fields['supplier'].label = 'Transport Company'
        self.fields['transport_company'].label = 'Select Transport Company'
        self.fields['description'].label = 'Notes'

    def clean_container_number(self):
        """اعتبارسنجی شماره کانتینر (یکتا)"""
        container_number = self.cleaned_data['container_number']
        if not container_number:
            raise ValidationError("Container number is required")
        
        # بررسی یکتا بودن
        qs = Container.objects.filter(container_number=container_number)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        
        if qs.exists():
            raise ValidationError(f"Container '{container_number}' already exists")
        
        return container_number.upper() 



class InventoryItemForm(forms.ModelForm):
    """فرم آیتم‌های موجودی داخل کانتینر"""
    
    class Meta:
        model = Inventory_List
        fields = [
            'product_name',  # نام محصول
            'code',          # کد محصول
            'in_stock_qty',  # تعداد
            'unit_price',    # قیمت واحد
            'description',   # توضیحات
        ]
        widgets = {
            'product_name': forms.TextInput(attrs={
                'class': 'form-control excel-input',
                'placeholder': 'Product name',
                'data-field': 'product_name'
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control excel-input',
                'placeholder': 'Product code',
                'data-field': 'code'
            }),
            'in_stock_qty': forms.NumberInput(attrs={
                'class': 'form-control excel-input qty-input',
                'step': '1',
                'min': '0',
                'data-field': 'in_stock_qty'
            }),
            'unit_price': forms.NumberInput(attrs={
                'class': 'form-control excel-input price-input',
                'step': '0.01',
                'min': '0',
                'data-field': 'unit_price',
                'data-type': 'currency'
            }),
            'description': forms.TextInput(attrs={
                'class': 'form-control excel-input',
                'placeholder': 'Short description',
                'data-field': 'description'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['in_stock_qty'].label = 'Quantity'
        self.fields['unit_price'].label = 'Unit Price (AED)'


class InventoryItemFormSet(forms.BaseInlineFormSet):
    """فرم‌ست برای مدیریت چند آیتم"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.total_value = 0
        self.total_qty = 0

    def clean(self):
        """اعتبارسنجی و محاسبات خودکار"""
        if any(self.errors):
            return
        
        products = []
        total_value = 0
        total_qty = 0
        
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                product_name = form.cleaned_data.get('product_name')
                code = form.cleaned_data.get('code')
                qty = form.cleaned_data.get('in_stock_qty', 0)
                price = form.cleaned_data.get('unit_price', 0)
                
                # محاسبه مجموع
                if qty and price:
                    total_value += float(qty) * float(price)
                    total_qty += float(qty) if qty else 0
                
                # بررسی تکراری نبودن
                if product_name and code:
                    if (product_name, code) in products:
                        raise ValidationError(
                            f"Duplicate item: {product_name} with code {code}"
                        )
                    products.append((product_name, code))
        
        self.total_value = total_value
        self.total_qty = total_qty


# فرم‌ست برای آیتم‌های موجودی (هر کانتینر چند آیتم داشته باشه)
InventoryItemInlineFormSet = forms.inlineformset_factory(
    Container,
    Inventory_List,
    form=InventoryItemForm,
    formset=InventoryItemFormSet,
    extra=5,           # ۵ ردیف خالی برای آیتم‌های جدید
    can_delete=True,   # قابلیت حذف
    min_num=1,         # حداقل ۱ آیتم
    validate_min=True
)


class ContainerFilterForm(forms.Form):
    """فرم فیلتر برای صفحه لیست کانتینرها"""
    
    STATUS_CHOICES = [
        ('', 'All Status'),
        ('in_transit', ' In Transit'),
        ('arrived', ' Arrived'),
        ('awaiting', ' Awaiting'),
        ('cleared', ' Cleared'),
    ]
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search container number...'
        })
    )
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date', 
            'class': 'form-control',
            'placeholder': 'From'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date', 
            'class': 'form-control',
            'placeholder': 'To'
        })
    )


class ContainerQuickForm(forms.ModelForm):
    """فرم سریع برای ویرایش درون‌خطی"""
    
    class Meta:
        model = Container
        fields = [
            'container_number',
            'name',
            'arrival_date',
            'transport_status',
            'supplier',
        ]
        widgets = {
            'container_number': forms.TextInput(attrs={
                'class': 'excel-inline-edit',
                'data-field': 'container_number'
            }),
            'name': forms.TextInput(attrs={
                'class': 'excel-inline-edit',
                'data-field': 'name'
            }),
            'arrival_date': forms.DateInput(attrs={
                'class': 'excel-inline-edit',
                'type': 'date',
                'data-field': 'arrival_date'
            }),
            'transport_status': forms.Select(attrs={
                'class': 'excel-inline-edit',
                'data-field': 'transport_status'
            }),
            'supplier': forms.TextInput(attrs={
                'class': 'excel-inline-edit',
                'data-field': 'supplier'
            }),
        }