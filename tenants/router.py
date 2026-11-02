from django.conf import settings
from tenants.context import get_current_tenant_alias


class TenantDatabaseRouter:
    """
    Multi-tenant database router for SoftobroCashBook.
    - Central apps reside on the 'default' PostgreSQL database.
    - Tenant apps (businesses, cashbooks, transactions) reside on the isolated tenant database.
    """

    TENANT_APPS = {'businesses', 'cashbooks', 'transactions'}
    CENTRAL_APPS = {
        'accounts',
        'subscriptions',
        'payments',
        'tenants',
        'notifications',
        'auth',
        'contenttypes',
        'sessions',
        'admin',
        'authtoken',
    }

    def db_for_read(self, model, **hints):
        app_label = model._meta.app_label
        if app_label in self.TENANT_APPS:
            alias = get_current_tenant_alias()
            return alias if alias else 'default'
        return 'default'

    def db_for_write(self, model, **hints):
        app_label = model._meta.app_label
        if app_label in self.TENANT_APPS:
            alias = get_current_tenant_alias()
            return alias if alias else 'default'
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        # Allow relations if models are both central or both tenant
        app1 = obj1._meta.app_label
        app2 = obj2._meta.app_label
        if (app1 in self.TENANT_APPS and app2 in self.TENANT_APPS) or (
            app1 not in self.TENANT_APPS and app2 not in self.TENANT_APPS
        ):
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        import sys
        # When running automated unit tests, allow all apps in test database
        if 'test' in sys.argv:
            return True

        # Tenant apps should only migrate into tenant databases (non-default),
        # Central apps should only migrate into default.
        if app_label in self.TENANT_APPS:
            return db != 'default'
        else:
            return db == 'default'

