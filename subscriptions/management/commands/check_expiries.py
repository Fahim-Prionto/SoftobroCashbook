from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from notifications.models import Notification, NotificationType
from subscriptions.models import Subscription, SubscriptionStatus
from tenants.models import AuditLog


class Command(BaseCommand):
    help = "Checks subscription expiration dates and updates statuses / sends notifications."

    def handle(self, *args, **options):
        now = timezone.now()
        three_days_later = now + timedelta(days=3)

        # 1. Expire past subscriptions
        expired_subs = Subscription.objects.filter(
            status=SubscriptionStatus.ACTIVE,
            end_date__lt=now,
        )
        count_expired = 0
        for sub in expired_subs:
            sub.status = SubscriptionStatus.EXPIRED
            sub.save()
            count_expired += 1

            Notification.objects.create(
                recipient=sub.user,
                title="Subscription Expired",
                message=f"Your subscription for plan '{sub.plan.name}' has expired. Please renew to continue managing your ledger.",
                notification_type=NotificationType.DANGER,
                link='/subscriptions/renew/',
            )

            AuditLog.objects.create(
                actor=None,
                action=AuditLog.Action.SUBSCRIPTION_EXPIRE,
                target=f"User: {sub.user.username}",
                details=f"Subscription for plan {sub.plan.name} expired on {sub.end_date}",
            )

        # 2. Notify subscriptions expiring in 3 days
        nearing_expiry = Subscription.objects.filter(
            status=SubscriptionStatus.ACTIVE,
            end_date__gte=now,
            end_date__lte=three_days_later,
        )
        count_warned = 0
        for sub in nearing_expiry:
            # Check if warning notification was already sent today
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            already_notified = Notification.objects.filter(
                recipient=sub.user,
                title="Subscription Expiring Soon",
                created_at__gte=today_start,
            ).exists()

            if not already_notified:
                days = sub.remaining_days
                Notification.objects.create(
                    recipient=sub.user,
                    title="Subscription Expiring Soon",
                    message=f"Your subscription '{sub.plan.name}' expires in {days} day(s). Renew with bKash to avoid service interruption.",
                    notification_type=NotificationType.WARNING,
                    link='/subscriptions/renew/',
                )
                count_warned += 1

        self.stdout.write(self.style.SUCCESS(
            f"Successfully checked subscriptions. Expired: {count_expired}, Warned: {count_warned}"
        ))

