import base64
import hashlib
from cryptography.fernet import Fernet
from django.conf import settings
from django.db import models


def get_fernet_instance():
    raw_key = getattr(settings, 'ENCRYPTION_KEY', '').strip()
    if not raw_key:
        raw_key = 'b5q3L9DVOgq27l6htokTAYMt3nC3R3pzZu1WonV18mk='
    if isinstance(raw_key, str):
        key_bytes = raw_key.encode('utf-8')
    else:
        key_bytes = raw_key
    # Try the key as-is (must be valid Fernet: 32 url-safe base64 bytes)
    try:
        return Fernet(key_bytes)
    except Exception:
        pass
    # Fallback: derive a valid 32-byte key from whatever value was set
    import base64, hashlib
    seed = key_bytes or getattr(settings, 'SECRET_KEY', 'softobro-secret-fallback').encode()
    if isinstance(seed, str):
        seed = seed.encode('utf-8')
    digest = hashlib.sha256(seed).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


class TenantStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending Provisioning'
    PROVISIONED = 'PROVISIONED', 'Provisioned & Active'
    ERROR = 'ERROR', 'Provisioning Failed'
    DELETED = 'DELETED', 'Deleted'


class Tenant(models.Model):
    service_admin = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tenant',
    )
    tenant_id = models.CharField(max_length=64, unique=True, db_index=True)
    db_name = models.CharField(max_length=128, unique=True)
    db_user = models.CharField(max_length=128)
    db_password_encrypted = models.TextField()
    db_host = models.CharField(max_length=128, default='localhost')
    db_port = models.IntegerField(default=5432)
    db_engine = models.CharField(max_length=50, default='postgresql')
    status = models.CharField(
        max_length=20,
        choices=TenantStatus.choices,
        default=TenantStatus.PENDING,
        db_index=True,
    )
    error_message = models.TextField(blank=True)
    provisioned_at = models.DateTimeField(null=True, blank=True)
    last_accessed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Tenant'
        verbose_name_plural = 'Tenants'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.tenant_id} ({self.db_name}) - {self.get_status_display()}"

    def set_db_password(self, raw_password: str):
        fernet = get_fernet_instance()
        self.db_password_encrypted = fernet.encrypt((raw_password or '').encode()).decode()

    def get_db_password(self) -> str:
        if not self.db_password_encrypted:
            return ""
        try:
            fernet = get_fernet_instance()
            return fernet.decrypt(self.db_password_encrypted.encode()).decode()
        except Exception:
            return ""


class AuditLog(models.Model):
    class Action(models.TextChoices):
        TENANT_PROVISION = 'TENANT_PROVISION', 'Tenant Provisioned'
        TENANT_DELETE = 'TENANT_DELETE', 'Tenant Deleted'
        PAYMENT_APPROVE = 'PAYMENT_APPROVE', 'Payment Approved'
        PAYMENT_REJECT = 'PAYMENT_REJECT', 'Payment Rejected'
        SUBSCRIPTION_ACTIVATE = 'SUBSCRIPTION_ACTIVATE', 'Subscription Activated'
        SUBSCRIPTION_RENEW = 'SUBSCRIPTION_RENEW', 'Subscription Renewed'
        SUBSCRIPTION_EXPIRE = 'SUBSCRIPTION_EXPIRE', 'Subscription Expired'
        USER_STATUS_CHANGE = 'USER_STATUS_CHANGE', 'User Status Changed'
        SETTINGS_UPDATE = 'SETTINGS_UPDATE', 'Settings Updated'
        LOGIN = 'LOGIN', 'User Logged In'

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
    )
    action = models.CharField(max_length=40, choices=Action.choices, db_index=True)
    target = models.CharField(max_length=255)
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.created_at.strftime('%Y-%m-%d %H:%M')}] {self.get_action_display()} - {self.target}"
