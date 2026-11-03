import logging
import secrets
import string
from django.conf import settings
from django.db import connections, connection
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
    In PostgreSQL, routes to a dedicated tenant schema (e.g. scb_tenant_X) via search_path.
    """
    alias = get_tenant_db_alias(tenant.tenant_id)
    schema_name = tenant.db_name

    engine = getattr(settings, 'CENTRAL_DB_ENGINE', 'django.db.backends.postgresql')

    if alias not in connections.databases:
        if 'postgresql' in engine or tenant.db_engine == 'postgresql':
            base_dict = settings.DATABASES.get('default', {}).copy()
            existing_options = base_dict.get('OPTIONS', {}).copy()
            existing_pg_options = existing_options.get('options', '')
            schema_option = f"-c search_path={schema_name},public"
            if existing_pg_options:
                existing_options['options'] = f"{existing_pg_options} {schema_option}"
            else:
                existing_options['options'] = schema_option

            base_dict['OPTIONS'] = existing_options
            base_dict['TIME_ZONE'] = getattr(settings, 'TIME_ZONE', 'Asia/Dhaka')
            base_dict['AUTOCOMMIT'] = True
            connections.databases[alias] = base_dict
        else:
            # SQLite fallback (useful for CI/tests)
            base_dict = settings.DATABASES.get('default', {}).copy()
            connections.databases[alias] = base_dict

    # Ensure search_path is set on the active cursor for PostgreSQL
    if 'postgresql' in engine:
        try:
            with connections[alias].cursor() as cur:
                cur.execute(f'SET search_path TO "{schema_name}", public')
        except Exception:
            pass

    return alias


def provision_tenant_database(service_admin, actor=None, ip_address=None):
    """
    Provisions a dedicated PostgreSQL Schema and service tables for an approved Service Admin.
    1. Generates unique schema identifier (e.g. scb_tenant_<id>).
    2. Creates the schema in PostgreSQL (CREATE SCHEMA IF NOT EXISTS).
    3. Creates all tenant service tables (businesses, cashbooks, transactions) inside the schema.
    4. Records tenant metadata and audit log.
    """
    schema_name = f"{getattr(settings, 'TENANT_DB_PREFIX', 'scb_tenant_')}{service_admin.id}"

    default_user = settings.DATABASES.get('default', {}).get('USER', 'postgres')
    default_host = settings.DATABASES.get('default', {}).get('HOST', '127.0.0.1')
    default_port = int(settings.DATABASES.get('default', {}).get('PORT', 5432))
    default_pass = settings.DATABASES.get('default', {}).get('PASSWORD', 'postgres')

    tenant, created = Tenant.objects.get_or_create(
        service_admin=service_admin,
        defaults={
            'tenant_id': f"tenant_{service_admin.id}",
            'db_name': schema_name,
            'db_user': default_user,
            'db_host': default_host,
            'db_port': default_port,
            'status': TenantStatus.PENDING,
        }
    )

    tenant.db_name = schema_name
    tenant.db_user = default_user
    tenant.db_host = default_host
    tenant.db_port = default_port
    tenant.set_db_password(default_pass)
    tenant.save()

    engine = getattr(settings, 'CENTRAL_DB_ENGINE', 'django.db.backends.postgresql')

    try:
        if 'postgresql' in engine:
            # 1. Create dedicated PostgreSQL Schema
            with connection.cursor() as cur:
                cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"')
                logger.info(f"PostgreSQL Schema '{schema_name}' created successfully.")

            # 2. Register alias in Django connections with search_path pointing to schema
            alias = ensure_tenant_database_registered(tenant)

            # 3. Create tenant tables directly inside this schema
            from django.apps import apps
            tenant_models = [
                apps.get_model('businesses', 'Business'),
                apps.get_model('cashbooks', 'Cashbook'),
                apps.get_model('transactions', 'Transaction'),
            ]

            tenant_conn = connections[alias]
            with tenant_conn.cursor() as t_cur:
                t_cur.execute(f'SET search_path TO "{schema_name}", public')

            with tenant_conn.schema_editor() as editor:
                for model in tenant_models:
                    table_name = model._meta.db_table
                    with tenant_conn.cursor() as check_cur:
                        check_cur.execute(
                            """
                            SELECT 1 FROM information_schema.tables 
                            WHERE table_schema = %s AND table_name = %s
                            """,
                            [schema_name, table_name],
                        )
                        exists = check_cur.fetchone()
                    if not exists:
                        editor.create_model(model)
                        logger.info(f"Created table {schema_name}.{table_name}")
        else:
            # SQLite fallback for test suite
            alias = ensure_tenant_database_registered(tenant)
            from django.apps import apps
            tenant_models = [
                apps.get_model('businesses', 'Business'),
                apps.get_model('cashbooks', 'Cashbook'),
                apps.get_model('transactions', 'Transaction'),
            ]
            with connections[alias].schema_editor() as editor:
                for model in tenant_models:
                    try:
                        editor.create_model(model)
                    except Exception:
                        pass

        tenant.status = TenantStatus.PROVISIONED
        tenant.provisioned_at = timezone.now()
        tenant.error_message = ""
        tenant.save()

        # Audit log
        AuditLog.objects.create(
            actor=actor or service_admin,
            action=AuditLog.Action.TENANT_PROVISION,
            target=f"{tenant.tenant_id} ({schema_name})",
            details=f"Tenant schema provisioned for {service_admin.username} ({service_admin.email}).",
            ip_address=ip_address,
        )

        logger.info(f"Tenant {tenant.tenant_id} schema provisioned successfully.")
        return tenant

    except Exception as e:
        logger.error(f"Failed to provision tenant schema {schema_name}: {str(e)}", exc_info=True)
        tenant.status = TenantStatus.ERROR
        tenant.error_message = str(e)
        tenant.save()
        raise


def delete_tenant_database(tenant, actor=None, ip_address=None):
    """
    Safely drops a tenant's PostgreSQL Schema and all tables inside it (DROP SCHEMA ... CASCADE).
    Guaranteed not to crash or leave the admin stuck.
    """
    if not tenant:
        raise ValueError("Tenant is required for deletion.")

    alias = get_tenant_db_alias(tenant.tenant_id)
    schema_name = tenant.db_name

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
            with connection.cursor() as cur:
                cur.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
                logger.info(f"PostgreSQL Schema '{schema_name}' dropped successfully.")
        except Exception as e:
            logger.warning(f"Notice while dropping PostgreSQL schema {schema_name}: {e}")
    else:
        # SQLite fallback
        import os
        db_path = settings.BASE_DIR / f"{schema_name}.sqlite3"
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass

    try:
        AuditLog.objects.create(
            actor=actor,
            action=AuditLog.Action.TENANT_DELETE,
            target=f"{tenant.tenant_id} ({schema_name})",
            details=f"Tenant schema safely dropped by {actor.username if actor else 'System'}.",
            ip_address=ip_address,
        )
    except Exception:
        pass

    tenant.status = TenantStatus.DELETED
    tenant.delete()
    return True
