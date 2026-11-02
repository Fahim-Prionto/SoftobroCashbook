from rest_framework import serializers
from accounts.models import User
from businesses.models import Business
from cashbooks.models import Cashbook
from notifications.models import Notification
from payments.models import Payment
from subscriptions.models import Subscription, SubscriptionPlan
from transactions.models import Transaction, TransactionType


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'business_name', 'phone_number', 'role', 'status']
        read_only_fields = ['id', 'username', 'role', 'status']


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    features = serializers.SerializerMethodField()

    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'name', 'slug', 'description', 'billing_cycle',
            'duration_days', 'price_bdt', 'max_businesses',
            'max_cashbooks_per_business', 'max_transactions', 'features', 'is_popular'
        ]

    def get_features(self, obj):
        return obj.get_features_list()


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = SubscriptionPlanSerializer(read_only=True)
    remaining_days = serializers.ReadOnlyField()
    is_currently_active = serializers.ReadOnlyField()

    class Meta:
        model = Subscription
        fields = ['id', 'plan', 'status', 'start_date', 'end_date', 'grace_period_days', 'remaining_days', 'is_currently_active']


class PaymentSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source='plan.name', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'plan', 'plan_name', 'amount_bdt', 'bkash_transaction_id',
            'sender_bkash_number', 'payment_date', 'status', 'approval_date', 'admin_notes', 'is_renewal'
        ]
        read_only_fields = ['id', 'status', 'approval_date', 'admin_notes']


class TransactionSerializer(serializers.ModelSerializer):
    cashbook_name = serializers.CharField(source='cashbook.name', read_only=True)
    business_name = serializers.CharField(source='cashbook.business.name', read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id', 'cashbook', 'cashbook_name', 'business_name', 'transaction_type',
            'amount', 'date', 'category', 'description', 'reference_number', 'attachment', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class CashbookSerializer(serializers.ModelSerializer):
    total_in = serializers.SerializerMethodField()
    total_out = serializers.SerializerMethodField()
    current_balance = serializers.SerializerMethodField()

    class Meta:
        model = Cashbook
        fields = ['id', 'business', 'name', 'opening_balance', 'description', 'status', 'total_in', 'total_out', 'current_balance']

    def get_total_in(self, obj):
        return str(obj.get_total_cash_in())

    def get_total_out(self, obj):
        return str(obj.get_total_cash_out())

    def get_current_balance(self, obj):
        return str(obj.get_current_balance())


class BusinessSerializer(serializers.ModelSerializer):
    cashbooks_count = serializers.SerializerMethodField()
    total_in = serializers.SerializerMethodField()
    total_out = serializers.SerializerMethodField()
    current_balance = serializers.SerializerMethodField()

    class Meta:
        model = Business
        fields = [
            'id', 'name', 'address', 'phone', 'email', 'description',
            'opening_balance', 'cashbooks_count', 'total_in', 'total_out', 'current_balance'
        ]

    def get_cashbooks_count(self, obj):
        return obj.cashbooks.count()

    def get_total_in(self, obj):
        return str(obj.get_total_cash_in())

    def get_total_out(self, obj):
        return str(obj.get_total_cash_out())

    def get_current_balance(self, obj):
        return str(obj.get_current_balance())


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'notification_type', 'link', 'is_read', 'created_at']

