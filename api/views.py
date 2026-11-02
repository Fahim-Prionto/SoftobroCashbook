from decimal import Decimal
from django.contrib.auth import authenticate
from django.db.models import Sum, Q
from rest_framework import viewsets, permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from accounts.models import User, UserRole, AccountStatus
from api.serializers import (
    UserProfileSerializer,
    SubscriptionPlanSerializer,
    SubscriptionSerializer,
    PaymentSerializer,
    BusinessSerializer,
    CashbookSerializer,
    TransactionSerializer,
    NotificationSerializer,
)
from businesses.models import Business
from cashbooks.models import Cashbook
from notifications.models import Notification
from payments.models import Payment, PaymentStatus
from subscriptions.models import Subscription, SubscriptionPlan, SubscriptionStatus
from tenants.models import TenantStatus
from transactions.models import Transaction, TransactionType


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def api_login(request):
    username_or_email = request.data.get('username')
    password = request.data.get('password')

    if not username_or_email or not password:
        return Response({'error': 'Please provide both username and password.'}, status=status.HTTP_400_BAD_REQUEST)

    user = authenticate(username=username_or_email, password=password)
    if not user and '@' in username_or_email:
        user_obj = User.objects.filter(email__iexact=username_or_email).first()
        if user_obj:
            user = authenticate(username=user_obj.username, password=password)

    if not user:
        return Response({'error': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)

    token, _ = Token.objects.get_or_create(user=user)
    tenant = getattr(user, 'tenant', None)
    subscription = getattr(user, 'subscription', None)

    return Response({
        'token': token.key,
        'user': UserProfileSerializer(user).data,
        'tenant_status': tenant.status if tenant else None,
        'subscription_status': subscription.status if subscription else None,
    })


@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([permissions.IsAuthenticated])
def api_profile(request):
    if request.method == 'GET':
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)
    else:
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BusinessViewSet(viewsets.ModelViewSet):
    serializer_class = BusinessSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Business.objects.all()

    def create(self, request, *args, **kwargs):
        subscription = getattr(request.user, 'subscription', None)
        if subscription:
            current_count = Business.objects.count()
            if not subscription.can_create_business(current_count):
                return Response(
                    {'error': f"Business limit of {subscription.plan.max_businesses} reached."},
                    status=status.HTTP_403_FORBIDDEN
                )
        return super().create(request, *args, **kwargs)


class CashbookViewSet(viewsets.ModelViewSet):
    serializer_class = CashbookSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Cashbook.objects.select_related('business').all()
        biz_id = self.request.query_params.get('business')
        if biz_id:
            qs = qs.filter(business_id=biz_id)
        return qs

    def create(self, request, *args, **kwargs):
        biz_id = request.data.get('business')
        if not biz_id:
            return Response({'error': 'business field is required.'}, status=status.HTTP_400_BAD_REQUEST)

        subscription = getattr(request.user, 'subscription', None)
        if subscription:
            biz = Business.objects.filter(id=biz_id).first()
            if biz and not subscription.can_create_cashbook(biz.cashbooks.count()):
                return Response(
                    {'error': f"Cashbook limit of {subscription.plan.max_cashbooks_per_business} reached for this business."},
                    status=status.HTTP_403_FORBIDDEN
                )
        return super().create(request, *args, **kwargs)


class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Transaction.objects.select_related('cashbook__business').all()
        cb_id = self.request.query_params.get('cashbook')
        t_type = self.request.query_params.get('type')
        category = self.request.query_params.get('category')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        if cb_id:
            qs = qs.filter(cashbook_id=cb_id)
        if t_type:
            qs = qs.filter(transaction_type=t_type)
        if category:
            qs = qs.filter(category=category)
        if start_date:
            qs = qs.filter(date__gte=start_date)
        if end_date:
            qs = qs.filter(date__lte=end_date)
        return qs

    def create(self, request, *args, **kwargs):
        subscription = getattr(request.user, 'subscription', None)
        if subscription:
            current_count = Transaction.objects.count()
            if not subscription.can_create_transaction(current_count):
                return Response(
                    {'error': f"Transaction limit of {subscription.plan.max_transactions} reached."},
                    status=status.HTTP_403_FORBIDDEN
                )
        return super().create(request, *args, **kwargs)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def api_financial_summary(request):
    businesses = Business.objects.all()
    cashbooks = Cashbook.objects.all()

    total_in = Transaction.objects.filter(transaction_type=TransactionType.CASH_IN).aggregate(t=Sum('amount'))['t'] or Decimal('0.00')
    total_out = Transaction.objects.filter(transaction_type=TransactionType.CASH_OUT).aggregate(t=Sum('amount'))['t'] or Decimal('0.00')

    total_opening = sum((b.opening_balance for b in businesses), Decimal('0.00')) + sum((cb.opening_balance for cb in cashbooks), Decimal('0.00'))
    current_balance = total_opening + total_in - total_out

    return Response({
        'total_businesses': businesses.count(),
        'total_cashbooks': cashbooks.count(),
        'total_cash_in': str(total_in),
        'total_cash_out': str(total_out),
        'total_opening_balance': str(total_opening),
        'current_balance': str(current_balance),
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def api_subscription_status(request):
    sub = getattr(request.user, 'subscription', None)
    if not sub:
        return Response({'subscription': None})
    return Response(SubscriptionSerializer(sub).data)


@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def api_payments(request):
    if request.method == 'GET':
        payments = Payment.objects.filter(service_admin=request.user).order_by('-created_at')
        return Response(PaymentSerializer(payments, many=True).data)
    else:
        serializer = PaymentSerializer(data=request.data)
        if serializer.is_valid():
            payment = serializer.save(service_admin=request.user)
            return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.request.user.notifications.all().order_by('-created_at')

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notif = self.get_object()
        notif.is_read = True
        notif.save()
        return Response({'status': 'marked as read'})
