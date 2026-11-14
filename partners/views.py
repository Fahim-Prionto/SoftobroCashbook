import io
from decimal import Decimal
from django.db import models as django_models
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.utils import timezone
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import (
    Partner, PartnerEntry, PartnerEntryLine, PartnerReceipt,
    InvoiceTemplate, InvoiceCustomization
)
from .serializers import (
    PartnerSerializer, PartnerEntrySerializer, PartnerEntryLineSerializer,
    PartnerReceiptSerializer, InvoiceTemplateSerializer, PartnerBalanceSerializer,
)


# ─── REST API ViewSets ──────────────────────────────────────────────────────────

class PartnerViewSet(viewsets.ModelViewSet):
    """CRUD for Partners (Customers & Vendors)."""
    serializer_class = PartnerSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'phone', 'email', 'address']
    ordering_fields = ['name', 'created_at']

    def get_queryset(self):
        qs = Partner.objects.filter(is_active=True)
        ptype = self.request.query_params.get('partner_type')
        if ptype:
            qs = qs.filter(partner_type=ptype)
        return qs

    @action(detail=True, methods=['get'])
    def balance(self, request, pk=None):
        """Return detailed balance summary for a partner."""
        partner = self.get_object()
        serializer = PartnerBalanceSerializer(partner)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def entries(self, request, pk=None):
        """Return all ledger entries for this partner."""
        partner = self.get_object()
        entries = partner.entries.all().order_by('-date_time')
        # Apply direction filter
        direction = request.query_params.get('direction')
        if direction:
            entries = entries.filter(direction=direction)
        payment_status = request.query_params.get('payment_status')
        if payment_status:
            entries = entries.filter(payment_status=payment_status)
        serializer = PartnerEntrySerializer(entries, many=True)
        return Response(serializer.data)


class PartnerEntryViewSet(viewsets.ModelViewSet):
    """CRUD for Partner Ledger Entries with nested lines and receipts."""
    serializer_class = PartnerEntrySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['reference_number', 'remarks', 'partner__name', 'entry_type']
    ordering_fields = ['date_time', 'created_at', 'total_amount']

    def get_queryset(self):
        qs = PartnerEntry.objects.select_related(
            'partner'
        ).prefetch_related('lines', 'receipts').all()

        # Filters from query params
        partner_id = self.request.query_params.get('partner')
        if partner_id:
            qs = qs.filter(partner_id=partner_id)
        business_id = self.request.query_params.get('business')
        if business_id:
            qs = qs.filter(business_id=business_id)
        cashbook_id = self.request.query_params.get('cashbook')
        if cashbook_id:
            qs = qs.filter(cashbook_id=cashbook_id)
        direction = self.request.query_params.get('direction')
        if direction:
            qs = qs.filter(direction=direction)
        payment_status = self.request.query_params.get('payment_status')
        if payment_status:
            qs = qs.filter(payment_status=payment_status)
        entry_type = self.request.query_params.get('entry_type')
        if entry_type:
            qs = qs.filter(entry_type=entry_type)
        date_from = self.request.query_params.get('date_from')
        if date_from:
            qs = qs.filter(date_time__date__gte=date_from)
        date_to = self.request.query_params.get('date_to')
        if date_to:
            qs = qs.filter(date_time__date__lte=date_to)
        return qs.order_by('-date_time')

    @action(detail=True, methods=['post'])
    def add_line(self, request, pk=None):
        """Add a single line item to an existing entry."""
        entry = self.get_object()
        serializer = PartnerEntryLineSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(entry=entry)
            entry.recalculate_totals()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'], url_path='remove_line/(?P<line_id>[^/.]+)')
    def remove_line(self, request, pk=None, line_id=None):
        """Remove a specific line item from an entry."""
        entry = self.get_object()
        line = get_object_or_404(PartnerEntryLine, pk=line_id, entry=entry)
        line.delete()
        entry.recalculate_totals()
        return Response({'detail': 'Line removed.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def add_receipt(self, request, pk=None):
        """Add a payment receipt to an existing entry."""
        entry = self.get_object()
        serializer = PartnerReceiptSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(entry=entry)
            entry.recalculate_totals()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'], url_path='remove_receipt/(?P<receipt_id>[^/.]+)')
    def remove_receipt(self, request, pk=None, receipt_id=None):
        """Remove a specific receipt from an entry."""
        entry = self.get_object()
        receipt = get_object_or_404(PartnerReceipt, pk=receipt_id, entry=entry)
        receipt.delete()
        entry.recalculate_totals()
        return Response({'detail': 'Receipt removed.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def invoice(self, request, pk=None):
        """Generate HTML invoice for an entry (ready for browser print)."""
        entry = self.get_object()
        entry.lines.all()
        entry.receipts.all()
        return render(request, 'partners/invoice_print.html', {'entry': entry})

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Aggregate summary: total, settled, outstanding across all entries."""
        qs = self.get_queryset()
        agg = qs.aggregate(
            total=django_models.Sum('total_amount'),
            settled=django_models.Sum('settled_amount'),
        )
        total = agg['total'] or Decimal('0.00')
        settled = agg['settled'] or Decimal('0.00')
        return Response({
            'total_entries': qs.count(),
            'total_amount': str(total),
            'settled_amount': str(settled),
            'outstanding_amount': str(total - settled),
            'paid_count': qs.filter(payment_status='PAID').count(),
            'partial_count': qs.filter(payment_status='PARTIAL').count(),
            'unpaid_count': qs.filter(payment_status='UNPAID').count(),
        })


class InvoiceTemplateViewSet(viewsets.ModelViewSet):
    """Upload and manage blank invoice PDF templates."""
    serializer_class = InvoiceTemplateSerializer
    permission_classes = [IsAuthenticated]
    queryset = InvoiceTemplate.objects.filter(is_active=True).order_by('-created_at')


# ─── Web Views (Service Admin UI) ───────────────────────────────────────────────

@login_required
def partner_list_view(request):
    partners = Partner.objects.filter(is_active=True).order_by('name')
    partner_type = request.GET.get('type', '')
    search = request.GET.get('q', '').strip()
    if partner_type:
        partners = partners.filter(partner_type=partner_type)
    if search:
        partners = partners.filter(
            django_models.Q(name__icontains=search) |
            django_models.Q(phone__icontains=search) |
            django_models.Q(email__icontains=search)
        )
    return render(request, 'partners/partner_list.html', {
        'partners': partners,
        'partner_type': partner_type,
        'search': search,
    })


@login_required
def partner_create_view(request):
    from .forms import PartnerForm
    if request.method == 'POST':
        form = PartnerForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Customer created successfully.')
            return redirect('partners:partner_list')
    else:
        form = PartnerForm()
    return render(request, 'partners/partner_form.html', {'form': form, 'action': 'Create'})


@login_required
def partner_edit_view(request, pk):
    from .forms import PartnerForm
    partner = get_object_or_404(Partner, pk=pk)
    if request.method == 'POST':
        form = PartnerForm(request.POST, instance=partner)
        if form.is_valid():
            form.save()
            messages.success(request, 'Customer updated.')
            return redirect('partners:partner_list')
    else:
        form = PartnerForm(instance=partner)
    return render(request, 'partners/partner_form.html', {'form': form, 'action': 'Edit', 'partner': partner})


@login_required
def partner_delete_view(request, pk):
    partner = get_object_or_404(Partner, pk=pk)
    if request.method == 'POST':
        partner.is_active = False
        partner.save()
        messages.success(request, f'Customer "{partner.name}" has been removed.')
        return redirect('partners:partner_list')
    return render(request, 'partners/partner_confirm_delete.html', {'partner': partner})


@login_required
def partner_balance_view(request, pk):
    partner = get_object_or_404(Partner, pk=pk)
    entries = partner.entries.prefetch_related('lines', 'receipts').order_by('-date_time')
    total = partner.get_total_amount()
    settled = partner.get_total_received()
    outstanding = partner.get_outstanding()
    return render(request, 'partners/partner_balance.html', {
        'partner': partner,
        'entries': entries,
        'total': total,
        'settled': settled,
        'outstanding': outstanding,
    })


@login_required
def ledger_list_view(request):
    from businesses.models import Business
    from cashbooks.models import Cashbook
    entries = PartnerEntry.objects.select_related(
        'partner'
    ).prefetch_related('lines', 'receipts').order_by('-date_time')

    # Filters
    partner_id = request.GET.get('partner', '')
    business_id = request.GET.get('business', '')
    cashbook_id = request.GET.get('cashbook', '')
    direction = request.GET.get('direction', '')
    payment_status = request.GET.get('payment_status', '')
    partner_type = request.GET.get('partner_type', '')
    search = request.GET.get('q', '').strip()
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if partner_id:
        entries = entries.filter(partner_id=partner_id)
    if business_id:
        entries = entries.filter(business_id=business_id)
    if cashbook_id:
        entries = entries.filter(cashbook_id=cashbook_id)
    if direction:
        entries = entries.filter(direction=direction)
    if payment_status:
        entries = entries.filter(payment_status=payment_status)
    if partner_type:
        entries = entries.filter(partner__partner_type=partner_type)
    if search:
        entries = entries.filter(
            django_models.Q(reference_number__icontains=search) |
            django_models.Q(remarks__icontains=search) |
            django_models.Q(partner__name__icontains=search)
        )
    if date_from:
        entries = entries.filter(date_time__date__gte=date_from)
    if date_to:
        entries = entries.filter(date_time__date__lte=date_to)

    # Summary
    agg = entries.aggregate(
        total=django_models.Sum('total_amount'),
        settled=django_models.Sum('settled_amount'),
    )
    total = agg['total'] or Decimal('0.00')
    settled = agg['settled'] or Decimal('0.00')

    return render(request, 'partners/ledger_list.html', {
        'entries': entries,
        'partners': Partner.objects.filter(is_active=True),
        'businesses': Business.objects.all(),
        'cashbooks': Cashbook.objects.all(),
        'total': total,
        'settled': settled,
        'outstanding': total - settled,
        'entry_count': entries.count(),
        # Active filters
        'f_partner': partner_id,
        'f_business': business_id,
        'f_cashbook': cashbook_id,
        'f_direction': direction,
        'f_payment_status': payment_status,
        'f_partner_type': partner_type,
        'f_search': search,
        'f_date_from': date_from,
        'f_date_to': date_to,
        # Pill filter choices
        'filter_directions': [('', 'All'), ('CASH_IN', 'Cash In'), ('CASH_OUT', 'Cash Out')],
        'filter_partner_types': [('', 'All'), ('CUSTOMER', 'Customer'), ('VENDOR', 'Vendor')],
        'filter_payment_statuses': [('', 'All'), ('PAID', 'Paid'), ('PARTIAL', 'Partial'), ('UNPAID', 'Unpaid')],
    })


@login_required
def entry_create_view(request):
    from businesses.models import Business
    from cashbooks.models import Cashbook
    businesses = Business.objects.all()
    cashbooks = Cashbook.objects.all()
    partners = Partner.objects.filter(is_active=True)
    initial_cashbook = request.GET.get('cashbook')
    initial_business = request.GET.get('business')
    initial_partner = request.GET.get('partner')

    if initial_cashbook and not initial_business:
        try:
            cb_obj = Cashbook.objects.get(pk=initial_cashbook)
            initial_business = cb_obj.business_id
        except Exception:
            pass

    return render(request, 'partners/entry_detail.html', {
        'businesses': businesses,
        'cashbooks': cashbooks,
        'partners': partners,
        'initial_cashbook': int(initial_cashbook) if initial_cashbook and str(initial_cashbook).isdigit() else None,
        'initial_business': int(initial_business) if initial_business and str(initial_business).isdigit() else None,
        'initial_partner': int(initial_partner) if initial_partner and str(initial_partner).isdigit() else None,
        'uom_choices': PartnerEntryLine._meta.get_field('uom').choices,
        'payment_method_choices': PartnerReceipt._meta.get_field('payment_method').choices,
        'action': 'create',
    })


@login_required
def entry_edit_view(request, pk):
    from businesses.models import Business
    from cashbooks.models import Cashbook
    entry = get_object_or_404(
        PartnerEntry.objects.select_related('partner')
        .prefetch_related('lines', 'receipts'),
        pk=pk
    )
    businesses = Business.objects.all()
    cashbooks = Cashbook.objects.all()
    partners = Partner.objects.filter(is_active=True)
    return render(request, 'partners/entry_detail.html', {
        'entry': entry,
        'businesses': businesses,
        'cashbooks': cashbooks,
        'partners': partners,
        'uom_choices': PartnerEntryLine._meta.get_field('uom').choices,
        'payment_method_choices': PartnerReceipt._meta.get_field('payment_method').choices,
        'action': 'edit',
    })


@login_required
def invoice_print_view(request, pk):
    """Render a printable invoice for a given entry, using custom styling/signature/Canva if configured."""
    entry = get_object_or_404(
        PartnerEntry.objects.select_related('partner')
        .prefetch_related('lines', 'receipts'),
        pk=pk
    )
    template = InvoiceTemplate.objects.filter(is_active=True).first()

    # Resolve customization: entry-specific -> business-specific -> any default -> None
    customization = getattr(entry, 'customization', None)
    if not customization and entry.business_id:
        customization = InvoiceCustomization.objects.filter(
            business_id=entry.business_id, entry__isnull=True
        ).first()
    if not customization:
        customization = InvoiceCustomization.objects.filter(entry__isnull=True).first()

    return render(request, 'partners/invoice_print.html', {
        'entry': entry,
        'template': template,
        'customization': customization,
    })


@login_required
def save_invoice_customization_view(request, pk):
    """Save or update invoice customization (header, signature, Canva design, stamp, terms)."""
    import json
    entry = get_object_or_404(PartnerEntry, pk=pk)
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required.'}, status=405)

    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body.decode('utf-8'))
        else:
            data = request.POST

        save_as_default = str(data.get('save_as_default', '')).lower() in ('true', '1', 'yes')

        if save_as_default and entry.business_id:
            cust, _ = InvoiceCustomization.objects.get_or_create(
                business_id=entry.business_id,
                entry__isnull=True,
            )
        else:
            cust, _ = InvoiceCustomization.objects.get_or_create(
                entry=entry,
                defaults={'business_id': entry.business_id}
            )

        cust.invoice_title = data.get('invoice_title', cust.invoice_title) or 'INVOICE / BILL'
        cust.company_name = data.get('company_name', cust.company_name) or ''
        cust.tagline = data.get('tagline', cust.tagline) or ''
        cust.phone = data.get('phone', cust.phone) or ''
        cust.email = data.get('email', cust.email) or ''
        cust.address = data.get('address', cust.address) or ''
        cust.header_theme = data.get('header_theme', cust.header_theme) or 'blue'
        cust.custom_accent_color = data.get('custom_accent_color', cust.custom_accent_color) or '#2563eb'
        cust.canva_design_url = data.get('canva_design_url', cust.canva_design_url) or ''

        # Update images/data if present in payload
        if 'logo_image' in data:
            cust.logo_image = data.get('logo_image') or ''
        if 'header_banner_image' in data:
            cust.header_banner_image = data.get('header_banner_image') or ''
        if 'signature_data' in data:
            cust.signature_data = data.get('signature_data') or ''
        if 'seal_data' in data:
            cust.seal_data = data.get('seal_data') or ''

        cust.signatory_name = data.get('signatory_name', cust.signatory_name) or ''
        cust.signatory_title = data.get('signatory_title', cust.signatory_title) or ''
        cust.show_stamp = str(data.get('show_stamp', cust.show_stamp)).lower() in ('true', '1', 'yes')
        cust.terms_and_conditions = data.get('terms_and_conditions', cust.terms_and_conditions) or ''
        cust.footer_notes = data.get('footer_notes', cust.footer_notes) or ''
        cust.save()

        return JsonResponse({
            'status': 'success',
            'message': 'Invoice customization saved successfully!',
            'save_as_default': save_as_default,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def invoice_settings_view(request):
    """Dedicated studio to customize default invoice and statement template from sidebar."""
    from businesses.models import Business
    businesses = Business.objects.all()
    selected_biz_id = request.GET.get('business')

    if selected_biz_id:
        customization = InvoiceCustomization.objects.filter(
            business_id=selected_biz_id, entry__isnull=True
        ).first()
    else:
        customization = InvoiceCustomization.objects.filter(entry__isnull=True).first()
        if customization and customization.business_id:
            selected_biz_id = str(customization.business_id)
        elif businesses.exists():
            selected_biz_id = str(businesses.first().id)
            customization = InvoiceCustomization.objects.filter(
                business_id=selected_biz_id, entry__isnull=True
            ).first()

    if not customization:
        customization = InvoiceCustomization(
            business_id=int(selected_biz_id) if selected_biz_id and selected_biz_id.isdigit() else None,
            company_name=getattr(request.user, 'business_name', '') or "Cash Hisab SoftoBro",
            invoice_title="INVOICE / BILL",
            signatory_name="Authorized Signatory",
            signatory_title="Proprietor / Manager",
            header_theme="blue",
        )

    return render(request, 'partners/invoice_settings.html', {
        'businesses': businesses,
        'selected_biz_id': selected_biz_id,
        'customization': customization,
    })


@login_required
def save_global_invoice_settings_view(request):
    """Save business/global default customization so all invoices and statements reflect it."""
    import json
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required.'}, status=405)

    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body.decode('utf-8'))
        else:
            data = request.POST

        biz_id = data.get('business_id') or None
        if biz_id and str(biz_id).isdigit():
            cust, _ = InvoiceCustomization.objects.get_or_create(
                business_id=int(biz_id),
                entry__isnull=True,
            )
        else:
            cust = InvoiceCustomization.objects.filter(entry__isnull=True).first()
            if not cust:
                cust = InvoiceCustomization(entry=None)

        cust.invoice_title = data.get('invoice_title', cust.invoice_title) or 'INVOICE / BILL'
        cust.company_name = data.get('company_name', cust.company_name) or ''
        cust.tagline = data.get('tagline', cust.tagline) or ''
        cust.phone = data.get('phone', cust.phone) or ''
        cust.email = data.get('email', cust.email) or ''
        cust.address = data.get('address', cust.address) or ''
        cust.header_theme = data.get('header_theme', cust.header_theme) or 'blue'
        cust.custom_accent_color = data.get('custom_accent_color', cust.custom_accent_color) or '#2563eb'
        cust.canva_design_url = data.get('canva_design_url', cust.canva_design_url) or ''

        if 'logo_image' in data:
            cust.logo_image = data.get('logo_image') or ''
        if 'header_banner_image' in data:
            cust.header_banner_image = data.get('header_banner_image') or ''
        if 'signature_data' in data:
            cust.signature_data = data.get('signature_data') or ''
        if 'seal_data' in data:
            cust.seal_data = data.get('seal_data') or ''

        cust.signatory_name = data.get('signatory_name', cust.signatory_name) or ''
        cust.signatory_title = data.get('signatory_title', cust.signatory_title) or ''
        cust.show_stamp = str(data.get('show_stamp', cust.show_stamp)).lower() in ('true', '1', 'yes')
        cust.terms_and_conditions = data.get('terms_and_conditions', cust.terms_and_conditions) or ''
        cust.footer_notes = data.get('footer_notes', cust.footer_notes) or ''
        cust.save()

        return JsonResponse({
            'status': 'success',
            'message': 'Invoice & Statement settings saved successfully and applied to all invoices!',
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
