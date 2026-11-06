from django.contrib import admin
from .models import Partner, PartnerEntry, PartnerEntryLine, PartnerReceipt, InvoiceTemplate


class PartnerEntryLineInline(admin.TabularInline):
    model = PartnerEntryLine
    extra = 1
    fields = ['description', 'price', 'quantity', 'uom']


class PartnerReceiptInline(admin.TabularInline):
    model = PartnerReceipt
    extra = 1
    fields = ['amount', 'payment_method', 'received_at', 'notes']


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ['name', 'partner_type', 'phone', 'email', 'is_active', 'created_at']
    list_filter = ['partner_type', 'is_active']
    search_fields = ['name', 'phone', 'email']
    ordering = ['name']


@admin.register(PartnerEntry)
class PartnerEntryAdmin(admin.ModelAdmin):
    list_display = [
        'reference_number', 'partner', 'direction', 'entry_type',
        'total_amount', 'settled_amount', 'payment_status', 'date_time',
    ]
    list_filter = ['direction', 'payment_status', 'entry_type']
    search_fields = ['reference_number', 'partner__name', 'remarks']
    readonly_fields = ['reference_number', 'total_amount', 'settled_amount', 'payment_status']
    inlines = [PartnerEntryLineInline, PartnerReceiptInline]
    ordering = ['-date_time']


@admin.register(InvoiceTemplate)
class InvoiceTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']
    list_filter = ['is_active']
