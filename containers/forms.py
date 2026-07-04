# forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Sum
from decimal import Decimal
from .models import Container, Inventory_List

# ============================================
# فرم‌های Container
# ============================================

class ContainerForm(forms.ModelForm):
    """
    فرم اصلی کانتینر - دقیقاً مطابق فیلدهای اکسل کارفرما
    """
    
    class Meta:
        model = Container
        fields = [
            'supplier',           # تامین‌کننده (Active, T Wicki, Car Click, Xpress)
            'container_no',       # شماره کانتینر (MRSU-5724751)
            'code',               # کد کانتینر (G50, U19, F6, E31...)
            'arrival_date',       # تاریخ ورود (Jan 31, Jan 22...)
        ]
        widgets = {
            'supplier': forms.TextInput(attrs={
                'class': 'form-control excel-input',
                'placeholder': 'e.g., Active, T Wicki, Car Click',
                'data-field': 'supplier',
                'autocomplete': 'off'
            }),
            'container_no': forms.TextInput(attrs={
                'class': 'form-control excel-input',
                'placeholder': 'e.g., MRSU-5724751',
                'data-field': 'container_no',
                'autofocus': True
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control excel-input',
                'placeholder': 'e.g., G50',
                'data-field': 'code'
            }),
            'arrival_date': forms.TextInput(attrs={
                'class': 'form-control excel-input',
                'placeholder': 'e.g., Jan 31, Feb 8',
                'data-field': 'arrival_date'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # تنظیم برچسب‌ها (مطابق با اکسل)
        self.fields['supplier'].label = 'Supplier'
        self.fields['container_no'].label = 'Container No.'
        self.fields['code'].label = 'Code'
        self.fields['arrival_date'].label = 'Arrival Date'
        
        # فیلدهای فقط خواندنی (برای نمایش در فرم ویرایش)
        if self.instance and self.instance.pk:
            self.fields['total_sales'] = forms.DecimalField(
                initial=self.instance.total_sales,
                disabled=True,
                required=False,
                widget=forms.NumberInput(attrs={'class': 'form-control bg-light'})
            )
            self.fields['total_expenses'] = forms.DecimalField(
                initial=self.instance.total_expenses,
                disabled=True,
                required=False,
                widget=forms.NumberInput(attrs={'class': 'form-control bg-light'})
            )
            self.fields['net_value'] = forms.DecimalField(
                initial=self.instance.net_value,
                disabled=True,
                required=False,
                widget=forms.NumberInput(attrs={'class': 'form-control bg-light fw-bold'})
            )
    
    def clean_container_no(self):
        """اعتبارسنجی شماره کانتینر - یکتا و الزامی"""
        container_no = self.cleaned_data.get('container_no', '').strip().upper()
        
        if not container_no:
            raise ValidationError('Container number is required')
        
        # بررسی یکتا بودن
        queryset = Container.objects.filter(container_no=container_no)
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise ValidationError(f'Container "{container_no}" already exists')
        
        return container_no
    
    def clean_code(self):
        """کد کانتینر - اختیاری ولی یکتا در ترکیب با شماره"""
        code = self.cleaned_data.get('code', '').strip().upper()
        return code if code else None
    
    def clean_arrival_date(self):
        """تاریخ ورود - فرمت آزاد (مثل Jan 31)"""
        arrival_date = self.cleaned_data.get('arrival_date', '').strip()
        return arrival_date if arrival_date else None


class ContainerFilterForm(forms.Form):
    """
    فرم فیلتر و جستجوی کانتینرها
    """
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by container no., code, or supplier...'
        })
    )
    
    supplier = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Supplier name'
        })
    )
    
    code = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Code (G50, U19...)'
        })
    )
    
    date_from = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Arrival date from (e.g., Jan 1)'
        })
    )
    
    date_to = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Arrival date to (e.g., Dec 31)'
        })
    )


# ============================================
# فرم‌های Inventory (موجودی)
# ============================================

class InventoryItemForm(forms.ModelForm):
    """
    فرم آیتم‌های موجودی - مطابق با اکسل Daily Sales
    """
    
    class Meta:
        model = Inventory_List
        fields = [
            'product_name',   # نام محصول (Bidford G21-1, 4JJ2 MQ139...)
            'code',           # کد محصول
            'unit_price',     # قیمت واحد (Sold Price در اکسل)
            'in_stock_qty',   # موجودی اولیه (Qty در اکسل)
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
            'unit_price': forms.NumberInput(attrs={
                'class': 'form-control excel-input price-input text-end',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00',
                'data-field': 'unit_price',
                'data-type': 'currency'
            }),
            'in_stock_qty': forms.NumberInput(attrs={
                'class': 'form-control excel-input qty-input text-end',
                'step': '1',
                'min': '0',
                'placeholder': '0',
                'data-field': 'in_stock_qty'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['product_name'].label = 'Items'
        self.fields['code'].label = 'Code'
        self.fields['unit_price'].label = 'Sold Price'
        self.fields['in_stock_qty'].label = 'Qty'
        
        # فیلدهای محاسباتی فقط خواندنی (برای نمایش)
        if self.instance and self.instance.pk:
            self.fields['total_sold'] = forms.IntegerField(
                initial=self.instance.total_sold_qty,
                disabled=True,
                required=False,
                widget=forms.NumberInput(attrs={'class': 'form-control bg-light text-end'})
            )
            self.fields['in_stock'] = forms.IntegerField(
                initial=self.instance.in_stock,
                disabled=True,
                required=False,
                widget=forms.NumberInput(attrs={'class': 'form-control bg-light text-end fw-bold'})
            )
    
    def clean_product_name(self):
        """نام محصول الزامی است"""
        name = self.cleaned_data.get('product_name', '').strip()
        if not name:
            raise ValidationError('Product name is required')
        return name
    
    def clean_unit_price(self):
        """قیمت واحد - حداقل 0"""
        price = self.cleaned_data.get('unit_price', 0)
        if price < 0:
            raise ValidationError('Price cannot be negative')
        return price
    
    def clean_in_stock_qty(self):
        """موجودی - عدد صحیح و نامنفی"""
        qty = self.cleaned_data.get('in_stock_qty', 0)
        if qty < 0:
            raise ValidationError('Quantity cannot be negative')
        return int(qty) if qty else 0


class InventoryItemFormSet(forms.BaseInlineFormSet):
    """
    فرم‌ست برای مدیریت چند آیتم در یک کانتینر
    با محاسبات خودکار مجموع ارزش و تعداد
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.total_value = Decimal('0')
        self.total_qty = 0
    
    def clean(self):
        """اعتبارسنجی کل فرم‌ست و محاسبه مجموع ارزش"""
        if any(self.errors):
            return
        
        products = []
        total_value = Decimal('0')
        total_qty = 0
        
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                product_name = form.cleaned_data.get('product_name')
                code = form.cleaned_data.get('code')
                qty = form.cleaned_data.get('in_stock_qty', 0)
                price = form.cleaned_data.get('unit_price', 0)
                
                # محاسبه ارزش کل
                if qty and price:
                    total_value += Decimal(str(qty)) * Decimal(str(price))
                    total_qty += int(qty) if qty else 0
                
                # بررسی تکراری نبودن محصولات
                if product_name and code:
                    if (product_name, code) in products:
                        raise ValidationError(
                            f'Duplicate item: "{product_name}" with code "{code}"'
                        )
                    products.append((product_name, code))
        
        self.total_value = total_value
        self.total_qty = total_qty
    
    def save(self, commit=True):
        """ذخیره با به‌روزرسانی خودکار کانتینر"""
        instances = super().save(commit=False)
        
        if commit:
            for instance in instances:
                instance.save()
            
            # به‌روزرسانی total_sales کانتینر (از مجموع آیتم‌ها)
            if self.instance and self.instance.pk:
                total_inventory_value = Inventory_List.objects.filter(
                    container=self.instance
                ).aggregate(
                    total=Sum('in_stock_qty') * Sum('unit_price')
                )['total'] or 0
                # توجه: total_sales از DailySaleTransaction محاسبه می‌شود
                # اینجا فقط ارزش موجودی را محاسبه می‌کنیم
        
        return instances


# inline formset برای اضافه کردن آیتم‌های موجودی به فرم کانتینر
InventoryInlineFormSet = forms.inlineformset_factory(
    Container,
    Inventory_List,
    form=InventoryItemForm,
    formset=InventoryItemFormSet,
    extra=5,
    can_delete=True,
    min_num=1,
    validate_min=True
)


# ============================================
# فرم‌های Bulk Import (برای وارد کردن از اکسل)
# ============================================

class ContainerBulkImportForm(forms.Form):
    """
    فرم آپلود فایل اکسل برای وارد کردن دسته‌ای کانتینرها
    """
    excel_file = forms.FileField(
        label='Excel File',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.xlsx, .xls, .csv'
        })
    )
    
    def clean_excel_file(self):
        file = self.cleaned_data['excel_file']
        max_size = 5 * 1024 * 1024  # 5MB
        
        if file.size > max_size:
            raise ValidationError(f'File too large (max {max_size / 1024 / 1024}MB)')
        
        # بررسی پسوند
        if not file.name.endswith(('.xlsx', '.xls', '.csv')):
            raise ValidationError('Only Excel or CSV files are allowed')
        
        return file


class InventoryBulkImportForm(forms.Form):
    """
    فرم آپلود فایل اکسل برای وارد کردن دسته‌ای موجودی
    """
    excel_file = forms.FileField(
        label='Excel File',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.xlsx, .xls, .csv'
        })
    )
    
    container = forms.ModelChoiceField(
        queryset=Container.objects.all(),
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def clean_excel_file(self):
        file = self.cleaned_data['excel_file']
        if file.size > 5 * 1024 * 1024:
            raise ValidationError('File too large (max 5MB)')
        return file


# ============================================
# فرم‌های گزارش و تحلیل
# ============================================

class ContainerReportForm(forms.Form):
    """
    فرم گزارش‌گیری از کانتینرها
    """
    REPORT_TYPE_CHOICES = [
        ('summary', 'Summary Report'),
        ('detailed', 'Detailed Report'),
        ('financial', 'Financial Report'),
    ]
    
    report_type = forms.ChoiceField(
        choices=REPORT_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    date_from = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'From (e.g., Jan 1)'
        })
    )
    
    date_to = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'To (e.g., Dec 31)'
        })
    )
    
    include_zero_sales = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )