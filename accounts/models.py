from django.contrib.auth.models import AbstractUser
from django.db import models


class UserRole(models.TextChoices):
    SUPER_ADMIN = 'SUPER_ADMIN', 'Super Admin'
    SERVICE_ADMIN = 'SERVICE_ADMIN', 'Service Admin'


class AccountStatus(models.TextChoices):
    PENDING_APPROVAL = 'PENDING_APPROVAL', 'Pending Approval'
    ACTIVE = 'ACTIVE', 'Active'
    SUSPENDED = 'SUSPENDED', 'Suspended'
    DEACTIVATED = 'DEACTIVATED', 'Deactivated'


class User(AbstractUser):
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.SERVICE_ADMIN,
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=AccountStatus.choices,
        default=AccountStatus.PENDING_APPROVAL,
        db_index=True,
    )
    business_name = models.CharField(max_length=255, blank=True, help_text="Registered company or business name")
    phone_number = models.CharField(max_length=30, blank=True, help_text="Contact / bKash phone number")
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']

    def __str__(self):
        full = self.get_full_name()
        display = full if full else self.username
        return f"{display} ({self.get_role_display()})"

    @property
    def is_super_admin(self):
        return self.role == UserRole.SUPER_ADMIN or self.is_superuser

    @property
    def is_service_admin(self):
        return self.role == UserRole.SERVICE_ADMIN

    @property
    def is_approved(self):
        return self.status == AccountStatus.ACTIVE
