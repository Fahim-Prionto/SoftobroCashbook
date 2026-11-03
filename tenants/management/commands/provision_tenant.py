from django.core.management.base import BaseCommand
from accounts.models import User, UserRole, AccountStatus
from tenants.models import TenantStatus
from tenants.provisioning import provision_tenant_database


class Command(BaseCommand):
    help = "Provisions dedicated PostgreSQL schema and tables for one or all active service admins."

    def add_arguments(self, parser):
        parser.add_argument(
            'identifier',
            nargs='?',
            type=str,
            help='Username or Email of the Service Admin to provision',
            default=None,
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Provision dedicated schemas for all active Service Admins who do not have one.',
        )

    def handle(self, *args, **options):
        provision_all = options.get('all', False)
        identifier = options.get('identifier')

        if provision_all:
            admins = User.objects.filter(role=UserRole.SERVICE_ADMIN, status=AccountStatus.ACTIVE)
            if not admins:
                self.stdout.write(self.style.WARNING("No active Service Admins found."))
                return

            self.stdout.write(f"Checking {admins.count()} active Service Admin(s)...")
            count = 0
            for admin in admins:
                tenant = getattr(admin, 'tenant', None)
                if not tenant or tenant.status != TenantStatus.PROVISIONED:
                    self.stdout.write(f"Provisioning schema for '{admin.username}'...")
                    try:
                        tenant = provision_tenant_database(admin)
                        self.stdout.write(self.style.SUCCESS(f"  Schema '{tenant.db_name}' provisioned successfully!"))
                        count += 1
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"  Failed for '{admin.username}': {e}"))
                else:
                    self.stdout.write(f"  '{admin.username}' already has schema '{tenant.db_name}'.")

            self.stdout.write(self.style.SUCCESS(f"\nDone! Provisioned {count} tenant schema(s)."))
            return

        if not identifier:
            self.stdout.write(self.style.ERROR("Please provide a Service Admin username/email, or use --all."))
            return

        admin = (
            User.objects.filter(username__iexact=identifier, role=UserRole.SERVICE_ADMIN).first()
            or User.objects.filter(email__iexact=identifier, role=UserRole.SERVICE_ADMIN).first()
        )

        if not admin:
            self.stdout.write(self.style.ERROR(f"No Service Admin found matching '{identifier}'."))
            return

        self.stdout.write(f"Provisioning dedicated schema for '{admin.username}'...")
        try:
            tenant = provision_tenant_database(admin)
            self.stdout.write(self.style.SUCCESS(f"Successfully provisioned schema '{tenant.db_name}' for '{admin.username}'!"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Provisioning failed: {e}"))
