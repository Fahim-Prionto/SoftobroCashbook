from django.core.management.base import BaseCommand
from django.db.models import Count
from accounts.models import User


class Command(BaseCommand):
    help = "Finds and removes duplicate user accounts sharing the exact same email address."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Display duplicate accounts without deleting them.',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        self.stdout.write("Scanning database for duplicate user emails...")

        duplicates = (
            User.objects.values('email')
            .annotate(email_count=Count('id'))
            .filter(email_count__gt=1)
            .exclude(email='')
        )

        if not duplicates:
            self.stdout.write(self.style.SUCCESS("No duplicate email accounts found! Database is clean."))
            return

        def score_user(u):
            # Higher score = higher priority to keep
            score = 0
            if u.is_superuser:
                score += 1000
            if u.is_staff:
                score += 200
            try:
                if hasattr(u, 'tenant') and u.tenant:
                    score += 500
            except Exception:
                pass
            try:
                if hasattr(u, 'subscription') and u.subscription:
                    score += 300
            except Exception:
                pass
            try:
                if u.payments.exists():
                    score += 100
            except Exception:
                pass
            if u.last_login:
                score += 50
            return score

        total_cleaned = 0
        for item in duplicates:
            email = item['email']
            count = item['email_count']
            self.stdout.write(f"\nFound {count} users sharing email '{email}':")

            all_users = list(User.objects.filter(email__iexact=email).order_by('-date_joined'))
            # Sort descending by priority score
            all_users.sort(key=score_user, reverse=True)

            primary_user = all_users[0]
            redundant_users = all_users[1:]

            self.stdout.write(self.style.SUCCESS(
                f"  KEEPING: '{primary_user.username}' (Superuser={primary_user.is_superuser}, Role={primary_user.role})"
            ))

            for r_user in redundant_users:
                if dry_run:
                    self.stdout.write(self.style.NOTICE(
                        f"  [DRY RUN] Would delete: '{r_user.username}' (id={r_user.id}, Role={r_user.role})"
                    ))
                else:
                    self.stdout.write(self.style.WARNING(
                        f"  DELETING DUPLICATE: '{r_user.username}' (id={r_user.id}, Role={r_user.role})"
                    ))
                    r_user.delete()
                    total_cleaned += 1

        if dry_run:
            self.stdout.write(self.style.NOTICE("\nDry run completed. No users were deleted."))
        else:
            self.stdout.write(self.style.SUCCESS(f"\nCleanup complete! Removed {total_cleaned} duplicate user account(s)."))
