from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from accounts.models import User, AccountStatus
from core.decorators import super_admin_required
from tenants.models import Tenant, TenantStatus, AuditLog
from tenants.provisioning import delete_tenant_database, provision_tenant_database


@login_required
@super_admin_required
def admin_tenant_list_view(request):
    status_filter = request.GET.get('status')
    search_query = request.GET.get('q', '').strip()

    tenants = Tenant.objects.select_related('service_admin').order_by('-created_at')

    if status_filter:
        tenants = tenants.filter(status=status_filter)

    if search_query:
        tenants = tenants.filter(
            tenant_id__icontains=search_query
        ) | tenants.filter(
            db_name__icontains=search_query
        ) | tenants.filter(
            service_admin__username__icontains=search_query
        ) | tenants.filter(
            service_admin__email__icontains=search_query
        )

    return render(request, 'tenants/admin_tenant_list.html', {
        'tenants': tenants,
        'status_filter': status_filter,
        'search_query': search_query,
    })


@login_required
@super_admin_required
def admin_tenant_detail_view(request, tenant_id):
    tenant = get_object_or_404(Tenant.objects.select_related('service_admin'), id=tenant_id)
    return render(request, 'tenants/admin_tenant_detail.html', {'tenant': tenant})


@login_required
@super_admin_required
def admin_tenant_reprovision_view(request, tenant_id):
    tenant = get_object_or_404(Tenant, id=tenant_id)
    try:
        from core.utils import get_client_ip
        provision_tenant_database(tenant.service_admin, actor=request.user, ip_address=get_client_ip(request))
        messages.success(request, f"Tenant {tenant.tenant_id} reprovisioned successfully.")
    except Exception as e:
        messages.error(request, f"Reprovisioning failed: {e}")
    return redirect('tenants:admin_tenant_detail', tenant_id=tenant.id)


@login_required
@super_admin_required
def admin_tenant_delete_view(request, tenant_id):
    tenant = get_object_or_404(Tenant.objects.select_related('service_admin'), id=tenant_id)
    service_admin = tenant.service_admin

    if request.method == 'POST':
        try:
            from core.utils import get_client_ip
            delete_tenant_database(
                tenant,
                actor=request.user,
                ip_address=get_client_ip(request),
            )
            messages.success(request, f"Tenant database '{tenant.db_name}' has been automatically dropped and purged.")
            return redirect('tenants:admin_tenant_list')
        except Exception as e:
            messages.error(request, f"Failed to delete tenant database: {e}")
            return render(request, 'tenants/admin_delete_confirm.html', {'tenant': tenant, 'service_admin': service_admin})

    return render(request, 'tenants/admin_delete_confirm.html', {
        'tenant': tenant,
        'service_admin': service_admin,
    })


@login_required
@super_admin_required
def admin_audit_log_view(request):
    action_filter = request.GET.get('action')
    logs = AuditLog.objects.select_related('actor').order_by('-created_at')
    if action_filter:
        logs = logs.filter(action=action_filter)

    return render(request, 'tenants/admin_audit_log.html', {
        'logs': logs[:100],
        'action_filter': action_filter,
        'actions': AuditLog.Action.choices,
    })
