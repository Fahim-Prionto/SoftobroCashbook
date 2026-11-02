import getpass
from django.core.management.base import BaseCommand
from accounts.models import User, UserRole, AccountStatus


class Command(BaseCommand):
    help = "Sets up or updates a Super Admin account with custom username, email, and password."

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Super Admin username', default=None)
        parser.add_argument('--email', type=str, help='Super Admin email', default=None)
        parser.add_argument('--password', type=str, help='Super Admin password', default=None)

    def handle(self, *args, **options):
        username = options.get('username')
        email = options.get('email')
        password = options.get('password')

        if not username:
            username = input("Enter Super Admin username (e.g. admin): ").strip()
            if not username:
                username = 'admin'

        if not email:
            email = input("Enter Super Admin email (e.g. admin@softobro.com): ").strip()
            if not email:
                email = 'admin@softobro.com'

        if not password:
            try:
                password = getpass.getpass("Enter Super Admin password: ").strip()
            except Exception:
                password = input("Enter Super Admin password: ").strip()

        if not password:
            self.stdout.write(self.style.ERROR("Password cannot be blank."))
            return

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'role': UserRole.SUPER_ADMIN,
                'status': AccountStatus.ACTIVE,
                'is_staff': True,
                'is_superuser': True,
            }
        )

        user.email = email
        user.role = UserRole.SUPER_ADMIN
        user.status = AccountStatus.ACTIVE
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        action = "Created new" if created else "Updated existing"
        self.stdout.write(self.style.SUCCESS(
            f"Successfully {action} Super Admin!\n"
            f"  Username: {username}\n"
            f"  Email:    {email}\n"
            f"  Status:   ACTIVE\n"
            f"  Role:     SUPER_ADMIN\n"
        ))
