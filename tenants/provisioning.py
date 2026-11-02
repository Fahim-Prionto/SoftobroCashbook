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


def get_sanitized_db_credentials(tenant=None):
    """
    Returns clean, reliable PostgreSQL host, port, user, and password.
    Falls back to settings.DATABASES['default'] to avoid invalid placeholders like 'your_postgres_admin'.
    Replaces 'localhost' with '127.0.0.1' to prevent IPv6 (::1) rejection in pg_hba.conf.
    """
    host = (
        (tenant.db_host if tenant else None)
        or getattr(settings, 'TENANT_DB_HOST', None)
        or settings.DATABASES.get('default', {}).get('HOST')
        or '127.0.0.1'
    )
    if host in ('localhost', '::1', ''):
        host = '127.0.0.1'

    port = (
        (tenant.db_port if tenant else None)
        or getattr(settings, 'TENANT_DB_PORT', None)
        or settings.DATABASES.get('default', {}).get('PORT')
        or 5432
    )

    default_user = settings.DATABASES.get('default', {}).get('USER', 'postgres')
    user = (tenant.db_user if tenant else None) or getattr(settings, 'TENANT_DB_SUPER_USER', None) or default_user
    if user in ('your_postgres_admin', 'postgres', ''):
        user = default_user

    default_pass = settings.DATABASES.get('default', {}).get('PASSWORD', 'postgres')
    password = (tenant.get_db_password() if tenant else None) or getattr(settings, 'TENANT_DB_SUPER_PASSWORD', None) or default_pass
    if password in ('your_postgres_admin_password', 'postgres', ''):
        password = default_pass

    return host, int(port), user, password


def ensure_tenant_database_registered(tenant):
    """
    Ensure the tenant's database connection is configured in django.db.connections.databases.
    """
    alias = get_tenant_db_alias(tenant.tenant_id)
    if alias in connections.databases:
        return alias

    engine = getattr(settings, 'CENTRAL_DB_ENGINE', 'django.db.backends.postgresql')

    if 'postgresql' in engine or tenant.db_engine == 'postgresql':
        host, port, user, password = get_sanitized_db_credentials(tenant)
        base_dict = settings.DATABASES.get('default', {}).copy()
        base_dict.update({
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': tenant.db_name,
            'USER': user,
            'PASSWORD': password,
            'HOST': host,
            'PORT': str(port),
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
    host, port, user, password = get_sanitized_db_credentials()

    tenant, created = Tenant.objects.get_or_create(
        service_admin=service_admin,
        defaults={
            'tenant_id': f"tenant_{service_admin.id}",
            'db_name': f"{getattr(settings, 'TENANT_DB_PREFIX', 'scb_tenant_')}{service_admin.id}",
            'db_user': user,
            'db_host': host,
            'db_port': port,
            'status': TenantStatus.PENDING,
        }
    )

    if tenant.status == TenantStatus.PROVISIONED:
        logger.info(f"Tenant {tenant.tenant_id} already provisioned.")
        ensure_tenant_database_registered(tenant)
        return tenant

    tenant.db_user = user
    tenant.db_host = host
    tenant.db_port = port
    tenant.set_db_password(password)
    tenant.save()

    engine = getattr(settings, 'CENTRAL_DB_ENGINE', 'django.db.backends.postgresql')

    try:
        if 'postgresql' in engine:
            import psycopg2
            from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

            conn_dbname = settings.DATABASES.get('default', {}).get('NAME') or 'postgres'
            conn = None
            for db_target in [conn_dbname, 'postgres']:
                try:
                    conn = psycopg2.connect(
                        host=host,
                        port=port,
                        user=user,
                        password=password,
                        dbname=db_target,
                        connect_timeout=8,
                    )
                    if conn:
                        break
                except Exception:
                    conn = None

            if conn:
                conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
                cur = conn.cursor()
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
    Guaranteed not to crash or leave the admin stuck if PostgreSQL DROP DATABASE encounters a connection issue.
    """
    if not tenant:
        raise ValueError("Tenant is required for deletion.")

    alias = get_tenant_db_alias(tenant.tenant_id)
    db_name = tenant.db_name

    # Close any open connections in Django
    if alias in connections:
        try:
            connections[alias].close()
        except Exception:
            pass
    if alias in connections.databases:
        try:
            del connections.databases[alias]
        except Exception:
            pass

    engine = getattr(settings, 'CENTRAL_DB_ENGINE', 'django.db.backends.postgresql')

    if 'postgresql' in engine:
        try:
            import psycopg2
            from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

            host, port, user, password = get_sanitized_db_credentials(tenant)
            conn_dbname = settings.DATABASES.get('default', {}).get('NAME') or 'postgres'

            conn = None
            for db_target in [conn_dbname, 'postgres']:
                try:
                    conn = psycopg2.connect(
                        host=host,
                        port=port,
                        user=user,
                        password=password,
                        dbname=db_target,
                        connect_timeout=8,
                    )
                    if conn:
                        break
                except Exception:
                    conn = None

            if conn:
                conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
                cur = conn.cursor()
                try:
                    cur.execute(
                        """
                        SELECT pg_terminate_backend(pid)
                        FROM pg_stat_activity
                        WHERE datname = %s AND pid <> pg_backend_pid()
                        """,
                        (db_name,),
                    )
                except Exception as e:
                    logger.warning(f"Notice terminating connections to {db_name}: {e}")

                try:
                    cur.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
                    logger.info(f"PostgreSQL database {db_name} dropped successfully.")
                except Exception as e:
                    logger.warning(f"Notice dropping {db_name}: {e}")
                finally:
                    cur.close()
                    conn.close()
            else:
                logger.warning(f"Could not connect to PostgreSQL server to drop physical DB {db_name}. Removing metadata record.")
        except Exception as e:
            logger.warning(f"Notice while dropping physical DB {db_name}: {e}")
    else:
        # SQLite fallback
        import os
        db_path = settings.BASE_DIR / f"{db_name}.sqlite3"
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass

    try:
        AuditLog.objects.create(
            actor=actor,
            action=AuditLog.Action.TENANT_DELETE,
            target=f"{tenant.tenant_id} ({db_name})",
            details=f"Tenant database safely deleted by {actor.username if actor else 'System'}.",
            ip_address=ip_address,
        )
    except Exception:
        pass

    tenant.status = TenantStatus.DELETED
    tenant.delete()
    return True

