from django.conf import settings


def site_settings(request):
    return {
        'SITE_NAME': getattr(settings, 'SITE_NAME', 'SoftobroCashBook'),
        'CURRENCY_SYMBOL': getattr(settings, 'CURRENCY_SYMBOL', '৳'),
        'BKASH_COMPANY_NUMBER': getattr(settings, 'BKASH_COMPANY_NUMBER', '01712345678'),
        'BKASH_ACCOUNT_TYPE': getattr(settings, 'BKASH_ACCOUNT_TYPE', 'Merchant / Personal'),
        'SUPPORT_EMAIL': getattr(settings, 'SUPPORT_EMAIL', 'support@softobrocashbook.com'),
        'SUPPORT_PHONE': getattr(settings, 'SUPPORT_PHONE', '+880 1700-000000'),
    }

