# employee/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from decimal import Decimal
import json
import logging
from django.db.models import Sum, F

from .models import Person, PersonTransaction
from .forms import PersonForm, PersonTransactionForm

logger = logging.getLogger(__name__)

@login_required
@never_cache
def person_list(request):
    persons = Person.objects.all().order_by('-created_at')
    transactions = PersonTransaction.objects.select_related('person').all().order_by('-date')
    stats = {
        'total': persons.count(),
        'employees': persons.filter(person_type='employee').count(),
        'sarafs': persons.filter(person_type='saraf').count(),
        'active': persons.filter(status='active').count(),
        'total_balance': sum(p.balance for p in persons),
    }
    
    context = {
        'persons': persons,
        'transactions': transactions,
        'stats': stats,
        'form': PersonForm(),
        'transaction_form': PersonTransactionForm(),
    }
    
    return render(request, 'employee/person_list.html', context)


@login_required
@never_cache
def people_management(request):    
    persons = Person.objects.all().order_by('-created_at')
    transactions = PersonTransaction.objects.select_related('person').all().order_by('-date')
    
    if request.method == 'POST':
        if 'person_submit' in request.POST:
            edit_id = request.POST.get('edit_id')
            if edit_id:
                person = get_object_or_404(Person, id=edit_id)
                form = PersonForm(request.POST, instance=person)
            else:
                form = PersonForm(request.POST)
            
            if form.is_valid():
                person = form.save()
                messages.success(request, f'✅ Person "{person.name}" saved successfully!')
                return redirect('employee:management')
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f'{field}: {error}')
        
        elif 'transaction_submit' in request.POST:
            form = PersonTransactionForm(request.POST)
            if form.is_valid():
                transaction = form.save()
                messages.success(request, f'✅ Transaction added successfully for {transaction.person.name}!')
                return redirect('employee:management')
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f'{field}: {error}')
    
    stats = {
        'total': persons.count(),
        'employees': persons.filter(person_type='employee').count(),
        'sarafs': persons.filter(person_type='saraf').count(),
        'total_balance': sum(p.balance for p in persons),
    }
    
    edit_person = None
    edit_id = request.GET.get('edit')
    if edit_id:
        try:
            edit_person = get_object_or_404(Person, id=edit_id)
        except:
            pass
    
    form = PersonForm(instance=edit_person) if edit_person else PersonForm()
    transaction_form = PersonTransactionForm()
    
    context = {
        'persons': persons,
        'transactions': transactions,
        'stats': stats,
        'form': form,
        'edit_person': edit_person,
        'transaction_form': transaction_form,
    }
    
    return render(request, 'employee/person_list.html', context)

@login_required
@require_POST
def person_create_ajax(request):
    try:
        person_type = request.POST.get('person_type', 'employee')
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip()
        address = request.POST.get('address', '').strip()
        status = 'active' if request.POST.get('status') == 'on' else 'inactive'

        if not name:
            return JsonResponse({'success': False, 'error': 'Name is required.'}, status=400)

        person = Person.objects.create(
            person_type=person_type,
            name=name,
            phone=phone,
            email=email,
            address=address,
            status=status,
        )

        return JsonResponse({
            'success': True,
            'id': str(person.id),
            'name': person.name,
            'type_display': person.get_person_type_display(),
            'status_display': person.get_status_display(),
            'balance': float(person.balance),
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_POST
def person_update_ajax(request, pk):
    try:
        person = get_object_or_404(Person, pk=pk)
        data = json.loads(request.body)
        
        for field in ['name', 'phone', 'email', 'address', 'status']:
            if field in data:
                setattr(person, field, data[field])
        
        if 'person_type' in data:
            person.person_type = data['person_type']
        
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
def person_delete(request, pk):
    person = get_object_or_404(Person, pk=pk)
    person.status = 'inactive'
    person.save()
    messages.success(request, f'Person "{person.name}" has been deactivated.')
    return redirect('employee:management')

@login_required
@never_cache
def person_detail(request, pk):
    person = get_object_or_404(Person, pk=pk)
    transactions = PersonTransaction.objects.filter(person=person).order_by('-date')
    total_cash_in = sum(t.cash_in for t in transactions)
    total_cash_out = sum(t.cash_out for t in transactions)
    net_balance = total_cash_in - total_cash_out
    transaction_stats = {
        'total': transactions.count(),
        'salary': transactions.filter(category='salary').count(),
        'deposit': transactions.filter(category='deposit').count(),
        'loan': transactions.filter(category='loan').count(),
        'payment': transactions.filter(category='payment').count(),
        'transfer': transactions.filter(category='transfer').count(),
        'other': transactions.filter(category='other').count(),
    }
    if request.method == 'POST':
        form = PersonTransactionForm(request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.person = person
            transaction.save()
            person.balance = PersonTransaction.objects.filter(person=person).aggregate(
                total=Sum(F('cash_in') - F('cash_out'))
            )['total'] or Decimal('0')
            person.save(update_fields=['balance'])
            
            messages.success(request, '✅ Transaction added successfully.')
            return redirect('employee:person_detail', pk=person.pk)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = PersonTransactionForm(initial={'person': person, 'date': timezone.now().date()})
    
    context = {
        'person': person,
        'transactions': transactions,
        'form': form,
        'total_cash_in': total_cash_in,
        'total_cash_out': total_cash_out,
        'net_balance': net_balance,
        'transaction_stats': transaction_stats,
    }
    return render(request, 'employee/person_detail.html', context)

@login_required
def get_person_json(request, pk):
    try:
        person = get_object_or_404(Person, pk=pk)
        return JsonResponse({
            'id': str(person.id),
            'person_type': person.person_type,
            'name': person.name,
            'phone': person.phone,
            'email': person.email,
            'address': person.address,
            'status': person.status,
            'balance': float(person.balance),
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
@require_POST
def transaction_create_ajax(request):
    try:
        person_id = request.POST.get('person')
        person = get_object_or_404(Person, pk=person_id)
        
        transaction = PersonTransaction.objects.create(
            person=person,
            day=request.POST.get('day', ''),
            date=request.POST.get('date') or timezone.now().date(),
            description=request.POST.get('description', ''),
            paid_by=request.POST.get('paid_by', ''),
            received_by=request.POST.get('received_by', ''),
            category=request.POST.get('category', 'other'),
            cash_in=Decimal(request.POST.get('cash_in', 0)),
            cash_out=Decimal(request.POST.get('cash_out', 0)),
        )
        person.balance = PersonTransaction.objects.filter(person=person).aggregate(
            total=Sum(F('cash_in') - F('cash_out'))
        )['total'] or Decimal('0')
        person.save(update_fields=['balance'])
        
        return JsonResponse({
            'success': True,
            'id': str(transaction.id),
            'date': transaction.date.strftime('%Y-%m-%d'),
            'description': transaction.description,
            'paid_by': transaction.paid_by,
            'received_by': transaction.received_by,
            'category_display': transaction.get_category_display(),
            'cash_in': float(transaction.cash_in),
            'cash_out': float(transaction.cash_out),
            'balance': float(transaction.balance),
            'person_balance': float(person.balance),
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
@require_POST
@csrf_exempt
def transaction_update_ajax(request, pk):
    try:
        transaction = get_object_or_404(PersonTransaction, pk=pk)
        data = json.loads(request.body)
        editable_fields = ['day', 'date', 'description', 'paid_by', 'received_by', 'category', 'cash_in', 'cash_out']
        
        for field, value in data.items():
            if field in editable_fields:
                if field == 'date':
                    from datetime import datetime
                    try:
                        value = datetime.strptime(value, '%Y-%m-%d').date()
                    except:
                        value = timezone.now().date()
                elif field in ['cash_in', 'cash_out']:
                    value = Decimal(str(value)) if value else Decimal('0')
                setattr(transaction, field, value)
        
        transaction.save()
        person = transaction.person
        total_balance = PersonTransaction.objects.filter(person=person).aggregate(
            total=Sum(F('cash_in') - F('cash_out'))
        )['total'] or Decimal('0')
        person.balance = total_balance
        person.save(update_fields=['balance'])
        return JsonResponse({
            'success': True,
            'id': str(transaction.id),
            'person_name': transaction.person.name,
            'day': transaction.day,
            'date': transaction.date.strftime('%Y-%m-%d'),
            'description': transaction.description,
            'paid_by': transaction.paid_by,
            'received_by': transaction.received_by,
            'category': transaction.category,
            'category_display': transaction.get_category_display(),
            'cash_in': float(transaction.cash_in),
            'cash_out': float(transaction.cash_out),
            'balance': float(transaction.balance),
            'person_balance': float(person.balance),
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error in transaction_update_ajax: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_POST
def transaction_delete_ajax(request, pk):
    try:
        transaction = get_object_or_404(PersonTransaction, pk=pk)
        person = transaction.person
        transaction.delete()
        person.balance = PersonTransaction.objects.filter(person=person).aggregate(
            total=Sum(F('cash_in') - F('cash_out'))
        )['total'] or Decimal('0')
        person.save(update_fields=['balance'])
        
        return JsonResponse({'success': True, 'id': str(pk)})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
