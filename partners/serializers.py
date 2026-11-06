from decimal import Decimal
from django.utils import timezone
from rest_framework import serializers
from .models import Partner, PartnerEntry, PartnerEntryLine, PartnerReceipt, InvoiceTemplate


class PartnerSerializer(serializers.ModelSerializer):
    total_amount = serializers.SerializerMethodField()
    settled_amount = serializers.SerializerMethodField()
    outstanding = serializers.SerializerMethodField()

    class Meta:
        model = Partner
        fields = [
            'id', 'name', 'partner_type', 'phone', 'email',
            'address', 'notes', 'is_active',
            'total_amount', 'settled_amount', 'outstanding',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'total_amount', 'settled_amount', 'outstanding']

    def get_total_amount(self, obj):
        return str(obj.get_total_amount())

    def get_settled_amount(self, obj):
        return str(obj.get_total_received())

    def get_outstanding(self, obj):
        return str(obj.get_outstanding())


class PartnerEntryLineSerializer(serializers.ModelSerializer):
    line_total = serializers.ReadOnlyField()

    class Meta:
        model = PartnerEntryLine
        fields = ['id', 'description', 'price', 'quantity', 'uom', 'line_total', 'created_at']
        read_only_fields = ['id', 'line_total', 'created_at']


class PartnerReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = PartnerReceipt
        fields = ['id', 'amount', 'payment_method', 'received_at', 'notes', 'created_at']
        read_only_fields = ['id', 'created_at']


class PartnerEntrySerializer(serializers.ModelSerializer):
    lines = PartnerEntryLineSerializer(many=True, required=False)
    receipts = PartnerReceiptSerializer(many=True, required=False)
    partner_name = serializers.SerializerMethodField()
    business_name = serializers.SerializerMethodField()
    cashbook_name = serializers.SerializerMethodField()
    outstanding_amount = serializers.ReadOnlyField()

    class Meta:
        model = PartnerEntry
        fields = [
            'id', 'reference_number',
            'partner', 'partner_name',
            'business', 'business_name',
            'cashbook', 'cashbook_name',
            'direction', 'entry_type',
            'date_time', 'remarks',
            'total_amount', 'settled_amount', 'outstanding_amount', 'payment_status',
            'lines', 'receipts',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'reference_number', 'total_amount', 'settled_amount',
            'outstanding_amount', 'payment_status', 'created_at', 'updated_at',
        ]

    def get_partner_name(self, obj):
        return obj.partner.name if obj.partner else ''

    def get_business_name(self, obj):
        return obj.business.name if obj.business else ''

    def get_cashbook_name(self, obj):
        return obj.cashbook.name if obj.cashbook else ''

    def create(self, validated_data):
        lines_data = validated_data.pop('lines', [])
        receipts_data = validated_data.pop('receipts', [])
        entry = PartnerEntry.objects.create(**validated_data)
        for line in lines_data:
            PartnerEntryLine.objects.create(entry=entry, **line)
        for receipt in receipts_data:
            PartnerReceipt.objects.create(entry=entry, **receipt)
        entry.recalculate_totals()
        return entry

    def update(self, instance, validated_data):
        lines_data = validated_data.pop('lines', None)
        receipts_data = validated_data.pop('receipts', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if lines_data is not None:
            instance.lines.all().delete()
            for line in lines_data:
                PartnerEntryLine.objects.create(entry=instance, **line)
        if receipts_data is not None:
            instance.receipts.all().delete()
            for receipt in receipts_data:
                PartnerReceipt.objects.create(entry=instance, **receipt)
        instance.recalculate_totals()
        return instance


class InvoiceTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceTemplate
        fields = ['id', 'name', 'pdf_file', 'description', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class PartnerBalanceSerializer(serializers.ModelSerializer):
    """Detailed balance summary for a single partner."""
    total_amount = serializers.SerializerMethodField()
    settled_amount = serializers.SerializerMethodField()
    outstanding = serializers.SerializerMethodField()
    entry_count = serializers.SerializerMethodField()
    paid_count = serializers.SerializerMethodField()
    partial_count = serializers.SerializerMethodField()
    unpaid_count = serializers.SerializerMethodField()

    class Meta:
        model = Partner
        fields = [
            'id', 'name', 'partner_type', 'phone', 'email',
            'total_amount', 'settled_amount', 'outstanding',
            'entry_count', 'paid_count', 'partial_count', 'unpaid_count',
        ]

    def get_total_amount(self, obj):
        return str(obj.get_total_amount())

    def get_settled_amount(self, obj):
        return str(obj.get_total_received())

    def get_outstanding(self, obj):
        return str(obj.get_outstanding())

    def get_entry_count(self, obj):
        return obj.entries.count()

    def get_paid_count(self, obj):
        return obj.entries.filter(payment_status='PAID').count()

    def get_partial_count(self, obj):
        return obj.entries.filter(payment_status='PARTIAL').count()

    def get_unpaid_count(self, obj):
        return obj.entries.filter(payment_status='UNPAID').count()

