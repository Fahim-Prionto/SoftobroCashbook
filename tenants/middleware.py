import logging
from tenants.context import set_current_tenant_alias, clear_current_tenant_alias
from tenants.models import TenantStatus
from tenants.provisioning import ensure_tenant_database_registered

logger = logging.getLogger(__name__)


class TenantMiddleware:
    """
    Middleware that identifies the current tenant based on the authenticated Service Admin,
    registers the tenant database connection if needed, and sets the thread-local database alias.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.tenant = None
        user = getattr(request, 'user', None)

        if user and user.is_authenticated and hasattr(user, 'is_service_admin') and user.is_service_admin:
            try:
                tenant = getattr(user, 'tenant', None)
                if tenant and tenant.status == TenantStatus.PROVISIONED:
                    alias = ensure_tenant_database_registered(tenant)
                    set_current_tenant_alias(alias)
                    request.tenant = tenant
                else:
                    clear_current_tenant_alias()
            except Exception as e:
                logger.error(f"Error establishing tenant context for user {user.id}: {e}", exc_info=True)
                clear_current_tenant_alias()
        else:
            clear_current_tenant_alias()

        try:
            response = self.get_response(request)
        finally:
            clear_current_tenant_alias()

        return response

