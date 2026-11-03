from django.contrib import admin
from payments.models import Payment, BKashSetting


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'service_admin', 'plan', 'amount_bdt', 'bkash_transaction_id', 'sender_bkash_number', 'status', 'created_at')
    list_filter = ('status', 'is_renewal')
    search_fields = ('bkash_transaction_id', 'sender_bkash_number', 'service_admin__username', 'service_admin__email')


@admin.register(BKashSetting)
class BKashSettingAdmin(admin.ModelAdmin):
    list_display = ('company_number', 'account_type', 'is_active', 'updated_at', 'updated_by')
