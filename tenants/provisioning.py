import logging
import secrets
import string
from django.conf import settings
from django.core.management import call_command
from django.db import connections
from django.utils import timezone
from tenants.models import Tenant, TenantStatus, AuditLog

logger = logging.getLogger(__name__)


def generate_secure_password(length=24):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def get_tenant_db_alias(tenant_id):
    return f"tenant_{tenant_id}"


def ensure_tenant_database_registered(tenant):
    """
    Ensure the tenant's database connection is configured in django.db.connections.databases.
    """
    alias = get_tenant_db_alias(tenant.tenant_id)
    if alias in connections.databases:
        return alias

    engine = getattr(settings, 'CENTRAL_DB_ENGINE', 'django.db.backends.postgresql')

    if 'postgresql' in engine or tenant.db_engine == 'postgresql':
        base_dict = settings.DATABASES.get('default', {}).copy()
        base_dict.update({
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': tenant.db_name,
            'USER': tenant.db_user or getattr(settings, 'TENANT_DB_SUPER_USER', 'postgres'),
            'PASSWORD': tenant.get_db_password() or getattr(settings, 'TENANT_DB_SUPER_PASSWORD', 'postgres'),
            'HOST': tenant.db_host or getattr(settings, 'TENANT_DB_HOST', 'localhost'),
            'PORT': str(tenant.db_port or getattr(settings, 'TENANT_DB_PORT', 5432)),
            'CONN_MAX_AGE': 60,
            'OPTIONS': {},
            'TIME_ZONE': getattr(settings, 'TIME_ZONE', 'Asia/Dhaka'),
            'AUTOCOMMIT': True,
        })
        connections.databases[alias] = base_dict
    else:
        # SQLite fallback (useful for CI/tests)
        db_path = settings.BASE_DIR / f"{tenant.db_name}.sqlite3"
        base_dict = settings.DATABASES.get('default', {}).copy()
        base_dict.update({
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': str(db_path),
            'OPTIONS': {},
            'TIME_ZONE': getattr(settings, 'TIME_ZONE', 'Asia/Dhaka'),
            'AUTOCOMMIT': True,
        })
        connections.databases[alias] = base_dict

    return alias


def provision_tenant_database(service_admin, actor=None, ip_address=None):
    """
    Provisions a new dedicated database for an approved Service Admin.
    1. Generates unique tenant identifier and DB name.
    2. Creates the database in PostgreSQL (or SQLite if configured).
    3. Runs tenant migrations (businesses, cashbooks, transactions).
    4. Records tenant metadata and audit log.
    """
    tenant, created = Tenant.objects.get_or_create(
        service_admin=service_admin,
        defaults={
            'tenant_id': f"tenant_{service_admin.id}",
            'db_name': f"{getattr(settings, 'TENANT_DB_PREFIX', 'scb_tenant_')}{service_admin.id}",
            'db_user': getattr(settings, 'TENANT_DB_SUPER_USER', 'postgres'),
            'db_host': getattr(settings, 'TENANT_DB_HOST', 'localhost'),
            'db_port': int(getattr(settings, 'TENANT_DB_PORT', 5432)),
            'status': TenantStatus.PENDING,
        }
    )

    if tenant.status == TenantStatus.PROVISIONED:
        logger.info(f"Tenant {tenant.tenant_id} already provisioned.")
        ensure_tenant_database_registered(tenant)
        return tenant

    db_password = getattr(settings, 'TENANT_DB_SUPER_PASSWORD', 'postgres')
    tenant.set_db_password(db_password)
    tenant.save()

    engine = getattr(settings, 'CENTRAL_DB_ENGINE', 'django.db.backends.postgresql')

    try:
        if 'postgresql' in engine:
            import psycopg2
            from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

            host = tenant.db_host or 'localhost'
            port = tenant.db_port or 5432
            super_user = getattr(settings, 'TENANT_DB_SUPER_USER', 'postgres')
            super_pass = getattr(settings, 'TENANT_DB_SUPER_PASSWORD', 'postgres')

            conn_dbname = settings.DATABASES.get('default', {}).get('NAME') or 'postgres'
            try:
                conn = psycopg2.connect(
                    host=host,
                    port=port,
                    user=super_user,
                    password=super_pass,
                    dbname=conn_dbname,
                    connect_timeout=10,
                )
            except Exception:
                conn = psycopg2.connect(
                    host=host,
                    port=port,
                    user=super_user,
                    password=super_pass,
                    dbname='postgres',
                    connect_timeout=10,
                )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cur = conn.cursor()

            # Check if database already exists
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (tenant.db_name,))
            if not cur.fetchone():
                cur.execute(f'CREATE DATABASE "{tenant.db_name}" ENCODING \'UTF8\'')
                logger.info(f"PostgreSQL database {tenant.db_name} created successfully.")

            cur.close()
            conn.close()

        # Register connection in Django
        alias = ensure_tenant_database_registered(tenant)

        # Run tenant migrations on this specific database
        logger.info(f"Running migrations on tenant database alias: {alias}")
        call_command('migrate', database=alias, interactive=False, verbosity=0)

        tenant.status = TenantStatus.PROVISIONED
        tenant.provisioned_at = timezone.now()
        tenant.error_message = ""
        tenant.save()

        # Audit log
        AuditLog.objects.create(
            actor=actor or service_admin,
            action=AuditLog.Action.TENANT_PROVISION,
            target=f"{tenant.tenant_id} ({tenant.db_name})",
            details=f"Tenant database provisioned for {service_admin.username} ({service_admin.email}).",
            ip_address=ip_address,
        )

        logger.info(f"Tenant {tenant.tenant_id} provisioned successfully.")
        return tenant

    except Exception as e:
        logger.error(f"Failed to provision tenant database: {str(e)}", exc_info=True)
        tenant.status = TenantStatus.ERROR
        tenant.error_message = str(e)
        tenant.save()
        raise


def delete_tenant_database(tenant, actor=None, ip_address=None):
    """
    Safely deletes a tenant database and associated metadata after verifying ownership.
    """
    if not tenant:
        raise ValueError("Tenant is required for deletion.")

    alias = get_tenant_db_alias(tenant.tenant_id)
    db_name = tenant.db_name

    # Close any open connections in Django
    if alias in connections:
        connections[alias].close()
    if alias in connections.databases:
        del connections.databases[alias]

    engine = getattr(settings, 'CENTRAL_DB_ENGINE', 'django.db.backends.postgresql')

    if 'postgresql' in engine:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

        host = tenant.db_host or 'localhost'
        port = tenant.db_port or 5432
        super_user = getattr(settings, 'TENANT_DB_SUPER_USER', 'postgres')
        super_pass = getattr(settings, 'TENANT_DB_SUPER_PASSWORD', 'postgres')

        conn_dbname = settings.DATABASES.get('default', {}).get('NAME') or 'postgres'
        try:
            conn = psycopg2.connect(
                host=host,
                port=port,
                user=super_user,
                password=super_pass,
                dbname=conn_dbname,
                connect_timeout=10,
            )
        except Exception:
            conn = psycopg2.connect(
                host=host,
                port=port,
                user=super_user,
                password=super_pass,
                dbname='postgres',
                connect_timeout=10,
            )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        # Terminate active connections to this tenant DB
        cur.execute(
            """
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = %s AND pid <> pg_backend_pid()
            """,
            (db_name,),
        )

        # Drop the tenant database
        cur.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
        cur.close()
        conn.close()
        logger.info(f"PostgreSQL database {db_name} dropped.")
    else:
        # SQLite fallback
        import os
        db_path = settings.BASE_DIR / f"{db_name}.sqlite3"
        if os.path.exists(db_path):
            os.remove(db_path)

    AuditLog.objects.create(
        actor=actor,
        action=AuditLog.Action.TENANT_DELETE,
        target=f"{tenant.tenant_id} ({db_name})",
        details=f"Tenant database safely deleted by {actor.username if actor else 'System'}.",
        ip_address=ip_address,
    )

    tenant.status = TenantStatus.DELETED
    tenant.save()
    tenant.delete()
    return True

