import threading

_thread_locals = threading.local()


def get_current_tenant_alias():
    """Retrieve the current thread's active tenant database alias."""
    return getattr(_thread_locals, 'tenant_db_alias', None)


def set_current_tenant_alias(alias):
    """Set the active tenant database alias for the current thread."""
    _thread_locals.tenant_db_alias = alias


def clear_current_tenant_alias():
    """Clear active tenant database alias."""
    if hasattr(_thread_locals, 'tenant_db_alias'):
        delattr(_thread_locals, 'tenant_db_alias')

