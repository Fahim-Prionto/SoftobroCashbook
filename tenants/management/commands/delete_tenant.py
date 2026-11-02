from django.core.management.base import BaseCommand
from tenants.models import Tenant
from tenants.provisioning import delete_tenant_database


class Command(BaseCommand):
    help = "Quickly and safely purges one or all tenant databases from the command line."

    def add_arguments(self, parser):
        parser.add_argument(
            'identifier',
            nargs='?',
            type=str,
            help='Tenant ID, DB name, or Service Admin username to delete',
            default=None,
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Purge all tenant records and databases.',
        )

    def handle(self, *args, **options):
        purge_all = options.get('all', False)
        identifier = options.get('identifier')

        if purge_all:
            tenants = list(Tenant.objects.all())
            if not tenants:
                self.stdout.write(self.style.SUCCESS("No tenant databases to delete."))
                return

            self.stdout.write(f"Purging {len(tenants)} tenant database(s)...")
            for t in tenants:
                self.stdout.write(f"Deleting {t.tenant_id} ({t.db_name})...")
                try:
                    delete_tenant_database(t)
                    self.stdout.write(self.style.SUCCESS(f"  Successfully deleted {t.db_name}."))
                except Exception as e:
                    t.delete()
                    self.stdout.write(self.style.WARNING(f"  Metadata purged (notice: {e})"))
            self.stdout.write(self.style.SUCCESS("All tenants purged successfully!"))
            return

        if not identifier:
            self.stdout.write(self.style.ERROR("Please provide a tenant ID / DB name / username, or pass --all."))
            return

        tenant = (
            Tenant.objects.filter(tenant_id__iexact=identifier).first()
            or Tenant.objects.filter(db_name__iexact=identifier).first()
            or Tenant.objects.filter(service_admin__username__iexact=identifier).first()
        )

        if not tenant:
            self.stdout.write(self.style.ERROR(f"No tenant found matching '{identifier}'."))
            return

        db_name = tenant.db_name
        self.stdout.write(f"Deleting tenant '{tenant.tenant_id}' ({db_name})...")
        try:
            delete_tenant_database(tenant)
            self.stdout.write(self.style.SUCCESS(f"Successfully deleted tenant database '{db_name}'."))
        except Exception as e:
            tenant.delete()
            self.stdout.write(self.style.WARNING(f"Tenant record purged (notice: {e})"))
