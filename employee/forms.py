from django import forms
from .models import Person, PersonTransaction

class PersonForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = ['person_type', 'status', 'name', 'phone', 'email', 'address']
        widgets = {
            'person_type': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Address'}),
        }


class PersonTransactionForm(forms.ModelForm):    
    class Meta:
        model = PersonTransaction
        fields = ['person', 'day', 'date', 'description', 'paid_by', 'received_by', 
                  'category', 'cash_in', 'cash_out']
        widgets = {
            'person': forms.Select(attrs={'class': 'form-select'}),
            'day': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Saturday'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Description'}),
            'paid_by': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Paid by'}),
            'received_by': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Received by'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'cash_in': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'placeholder': '0.00'}),
            'cash_out': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'placeholder': '0.00'}),
        }