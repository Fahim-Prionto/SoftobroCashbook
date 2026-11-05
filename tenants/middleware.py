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

        # Support DRF token authentication & JWT Bearer authentication in middleware
        if not user or not user.is_authenticated:
            auth_header = request.headers.get('Authorization', '') or request.META.get('HTTP_AUTHORIZATION', '')
            if auth_header.startswith('Bearer '):
                jwt_token = auth_header.split(' ', 1)[1].strip()
                try:
                    from rest_framework_simplejwt.tokens import AccessToken
                    from accounts.models import User
                    validated_token = AccessToken(jwt_token)
                    user_id = validated_token.get('user_id')
                    if user_id:
                        user = User.objects.filter(id=user_id).first()
                        if user:
                            request.user = user
                except Exception as e:
                    logger.warning(f"JWT validation in TenantMiddleware failed: {e}")
            elif auth_header.startswith('Token '):
                token_key = auth_header.split(' ', 1)[1].strip()
                try:
                    from rest_framework.authtoken.models import Token
                    token = Token.objects.select_related('user').get(key=token_key)
                    user = token.user
                    request.user = user
                except Exception:
                    pass

        if user and user.is_authenticated and hasattr(user, 'is_service_admin') and user.is_service_admin:
            try:
                tenant = getattr(user, 'tenant', None)

                # If user is ACTIVE but tenant DB is not yet provisioned, auto-provision
                if getattr(user, 'status', None) == 'ACTIVE' and (not tenant or tenant.status != TenantStatus.PROVISIONED):
                    try:
                        from tenants.provisioning import provision_tenant_database
                        tenant = provision_tenant_database(user)
                    except Exception as e:
                        logger.error(f"On-the-fly tenant provisioning failed for user {user.id}: {e}")

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

