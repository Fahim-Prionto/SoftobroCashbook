import ipaddress


def get_client_ip(request) -> str | None:
    """
    Safely extracts and validates an IPv4 or IPv6 client address from request headers.
    Strips ports and ignores non-IP proxy strings.
    """
    if not request:
        return None

    ip = request.META.get('HTTP_X_FORWARDED_FOR')
    if ip:
        ip = ip.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')

    if ip:
        # Strip port if present (e.g. "103.145.74.22:54832")
        if ':' in ip and '.' in ip:
            ip = ip.split(':')[0].strip()
        try:
            ipaddress.ip_address(ip)
        except (ValueError, TypeError):
            ip = None

    return ip
