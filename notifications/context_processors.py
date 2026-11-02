def notification_context(request):
    if not request.user.is_authenticated:
        return {'unread_notifications_count': 0, 'recent_notifications': []}

    try:
        user_notifications = request.user.notifications.all()
        unread_count = user_notifications.filter(is_read=False).count()
        recent = user_notifications[:5]
        return {
            'unread_notifications_count': unread_count,
            'recent_notifications': recent,
        }
    except Exception:
        return {'unread_notifications_count': 0, 'recent_notifications': []}

