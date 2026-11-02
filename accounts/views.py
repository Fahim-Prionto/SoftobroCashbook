from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import render, redirect
from accounts.forms import ServiceAdminRegistrationForm, LoginForm, UserProfileForm
from accounts.models import UserRole, AccountStatus
from subscriptions.models import Subscription, SubscriptionStatus
from tenants.models import AuditLog


def register_view(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard_redirect')

    selected_plan_id = request.GET.get('plan')

    if request.method == 'POST':
        form = ServiceAdminRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = UserRole.SERVICE_ADMIN
            user.status = AccountStatus.PENDING_APPROVAL
            user.set_password(form.cleaned_data['password'])
            user.save()

            plan = form.cleaned_data['plan']
            Subscription.objects.create(
                user=user,
                plan=plan,
                status=SubscriptionStatus.PENDING,
            )

            # Audit log
            AuditLog.objects.create(
                actor=user,
                action=AuditLog.Action.LOGIN,
                target=f"User Registration: {user.username}",
                details=f"Registered with business: {user.business_name}, Plan: {plan.name}",
                ip_address=request.META.get('REMOTE_ADDR'),
            )

            login(request, user)
            messages.success(request, f"Welcome to SoftobroCashBook! Please complete your bKash payment for the {plan.name}.")
            return redirect('payments:submit_payment')
    else:
        initial_data = {}
        if selected_plan_id:
            initial_data['plan'] = selected_plan_id
        form = ServiceAdminRegistrationForm(initial=initial_data)

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard_redirect')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            remember_me = form.cleaned_data.get('remember_me')
            login(request, user)

            if not remember_me:
                request.session.set_expiry(0)  # Browser close expires session
            else:
                request.session.set_expiry(1209600)  # 2 weeks

            AuditLog.objects.create(
                actor=user,
                action=AuditLog.Action.LOGIN,
                target=f"User Login: {user.username}",
                details=f"Role: {user.get_role_display()}, IP: {request.META.get('REMOTE_ADDR')}",
                ip_address=request.META.get('REMOTE_ADDR'),
            )

            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            return redirect('core:dashboard_redirect')
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, "You have been securely signed out.")
    return redirect('accounts:login')


@login_required
def profile_view(request):
    user = request.user
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile details have been updated successfully.")
            return redirect('accounts:profile')
    else:
        form = UserProfileForm(instance=user)

    password_form = PasswordChangeForm(user=user)
    return render(request, 'accounts/profile.html', {
        'form': form,
        'password_form': password_form,
    })


@login_required
def change_password_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Your password was successfully updated!")
            return redirect('accounts:profile')
        else:
            messages.error(request, "Please correct the password errors below.")
            profile_form = UserProfileForm(instance=request.user)
            return render(request, 'accounts/profile.html', {
                'form': profile_form,
                'password_form': form,
            })
    return redirect('accounts:profile')
