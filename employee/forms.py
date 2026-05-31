# forms.py
from django import forms
from .models import Person, SarafTransaction

class PersonForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = [
            'person_type', 'status', 'name', 'phone', 'email', 'address',
            'salary', 'department', 'hire_date',
            'license_number', 'commission_rate'
        ]
        widgets = {
            'person_type': forms.Select(attrs={'class': 'excel-select'}),
            'status': forms.Select(attrs={'class': 'excel-select'}),
            'name': forms.TextInput(attrs={'class': 'excel-input', 'placeholder': 'Full name'}),
            'phone': forms.TextInput(attrs={'class': 'excel-input', 'placeholder': 'Phone number'}),
            'email': forms.EmailInput(attrs={'class': 'excel-input', 'placeholder': 'Email address'}),
            'address': forms.Textarea(attrs={'class': 'excel-input', 'rows': 2, 'placeholder': 'Address'}),
            'salary': forms.NumberInput(attrs={'class': 'excel-input', 'step': '0.01', 'min': '0'}),
            'department': forms.TextInput(attrs={'class': 'excel-input', 'placeholder': 'Department'}),
            'hire_date': forms.DateInput(attrs={'class': 'excel-input', 'type': 'date'}),
            'license_number': forms.TextInput(attrs={'class': 'excel-input', 'placeholder': 'License number'}),
            'commission_rate': forms.NumberInput(attrs={'class': 'excel-input', 'step': '0.1', 'min': '0', 'max': '100'}),
        }


class SarafTransactionForm(forms.ModelForm):
    class Meta:
        model = SarafTransaction
        fields = ['saraf', 'day', 'date', 'description', 'paid_by', 'received_by', 'category', 'cash_in', 'cash_out']
        widgets = {
            'saraf': forms.Select(attrs={'class': 'excel-select'}),
            'day': forms.TextInput(attrs={'class': 'excel-input', 'placeholder': 'e.g., Monday'}),
            'date': forms.DateInput(attrs={'class': 'excel-input', 'type': 'date'}),
            'description': forms.Textarea(attrs={'class': 'excel-input', 'rows': 2, 'placeholder': 'Transaction description'}),
            'paid_by': forms.TextInput(attrs={'class': 'excel-input', 'placeholder': 'Who paid?'}),
            'received_by': forms.TextInput(attrs={'class': 'excel-input', 'placeholder': 'Who received?'}),
            'category': forms.Select(attrs={'class': 'excel-select'}),
            'cash_in': forms.NumberInput(attrs={'class': 'excel-input', 'step': '0.01', 'min': '0'}),
            'cash_out': forms.NumberInput(attrs={'class': 'excel-input', 'step': '0.01', 'min': '0'}),
        }