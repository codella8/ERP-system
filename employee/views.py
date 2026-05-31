# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from decimal import Decimal
from .models import Person, SarafTransaction
from .forms import PersonForm, SarafTransactionForm

@login_required
def person_list(request):
    """صفحه اصلی اشخاص """
    persons = Person.objects.all().order_by('-created_at')
    
    # محاسبات آماری
    stats = {
        'total': persons.count(),
        'employees': persons.filter(person_type='employee').count(),
        'sarafs': persons.filter(person_type='saraf').count(),
        'active': persons.filter(status='active').count(),
        'total_balance': sum(p.balance for p in persons),
        'total_salary': sum(p.salary or 0 for p in persons if p.is_employee),
    }
    
    context = {
        'persons': persons,
        'stats': stats,
    }
    return render(request, 'employees/person_list.html', context)


@login_required
@require_POST
def person_create_ajax(request):
    """ایجاد شخص جدید با AJAX"""
    try:
        person = Person.objects.create(
            person_type=request.POST.get('person_type'),
            name=request.POST.get('name'),
            phone=request.POST.get('phone', ''),
            email=request.POST.get('email', ''),
            address=request.POST.get('address', ''),
            salary=Decimal(request.POST.get('salary', 0)) if request.POST.get('salary') else None,
            department=request.POST.get('department', ''),
            hire_date=request.POST.get('hire_date') or None,
            license_number=request.POST.get('license_number', ''),
            commission_rate=Decimal(request.POST.get('commission_rate', 0)) if request.POST.get('commission_rate') else None,
            status=request.POST.get('status', 'active'),
        )
        
        return JsonResponse({
            'success': True,
            'id': str(person.id),
            'name': person.name,
            'type': person.get_person_type_display(),
            'balance': float(person.balance),
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_POST
def person_update_ajax(request, pk):
    """بروزرسانی شخص با AJAX (ویرایش درون خطی)"""
    try:
        person = get_object_or_404(Person, pk=pk)
        data = request.POST.dict()
        
        # بروزرسانی فیلدها
        for field in ['name', 'phone', 'email', 'address', 'department', 'license_number', 'status']:
            if field in data:
                setattr(person, field, data[field])
        
        if 'person_type' in data:
            person.person_type = data['person_type']
        
        if 'salary' in data and data['salary']:
            person.salary = Decimal(data['salary'])
        
        if 'commission_rate' in data and data['commission_rate']:
            person.commission_rate = Decimal(data['commission_rate'])
        
        if 'hire_date' in data and data['hire_date']:
            person.hire_date = data['hire_date']
        
        person.save()
        
        return JsonResponse({
            'success': True,
            'id': str(person.id),
            'balance': float(person.balance),
            'type_display': person.get_person_type_display(),
            'status_display': person.get_status_display(),
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
def person_detail(request, pk):
    """صفحه جزئیات شخص با تراکنش‌های صرافی"""
    person = get_object_or_404(Person, pk=pk)
    
    if person.is_saraf:
        transactions = SarafTransaction.objects.filter(saraf=person).order_by('-date')
    else:
        transactions = []
    
    # فرم تراکنش جدید برای صراف‌ها
    if request.method == 'POST' and person.is_saraf:
        form = SarafTransactionForm(request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.saraf = person
            transaction.save()
            messages.success(request, 'Transaction added successfully.')
            return redirect('employees:detail', pk=person.pk)
    else:
        form = SarafTransactionForm(initial={'saraf': person, 'date': timezone.now().date()})
    
    # محاسبات مالی
    if person.is_saraf:
        total_cash_in = sum(t.cash_in for t in transactions)
        total_cash_out = sum(t.cash_out for t in transactions)
        net = total_cash_in - total_cash_out
    else:
        total_cash_in = total_cash_out = net = 0
    
    context = {
        'person': person,
        'transactions': transactions,
        'form': form if person.is_saraf else None,
        'total_cash_in': total_cash_in,
        'total_cash_out': total_cash_out,
        'net': net,
    }
    return render(request, 'employees/person_detail.html', context)


@login_required
@require_POST
def transaction_create_ajax(request):
    """ایجاد تراکنش صرافی با AJAX"""
    try:
        saraf_id = request.POST.get('saraf')
        saraf = get_object_or_404(Person, pk=saraf_id, person_type='saraf')
        
        transaction = SarafTransaction.objects.create(
            saraf=saraf,
            day=request.POST.get('day', ''),
            date=request.POST.get('date') or timezone.now().date(),
            description=request.POST.get('description', ''),
            paid_by=request.POST.get('paid_by', ''),
            received_by=request.POST.get('received_by', ''),
            category=request.POST.get('category', 'other'),
            cash_in=Decimal(request.POST.get('cash_in', 0)),
            cash_out=Decimal(request.POST.get('cash_out', 0)),
        )
        
        return JsonResponse({
            'success': True,
            'id': str(transaction.id),
            'date': transaction.date.strftime('%Y-%m-%d'),
            'description': transaction.description,
            'cash_in': float(transaction.cash_in),
            'cash_out': float(transaction.cash_out),
            'balance': float(transaction.balance),
            'saraf_balance': float(saraf.balance),
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)