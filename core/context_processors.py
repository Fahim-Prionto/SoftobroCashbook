from django.conf import settings


def site_settings(request):
    bkash_num = getattr(settings, 'BKASH_COMPANY_NUMBER', '01712345678')
    bkash_type = getattr(settings, 'BKASH_ACCOUNT_TYPE', 'Personal (Send Money)')
    bkash_instruction = ''

    try:
        from payments.models import BKashSetting
        s = BKashSetting.objects.filter(is_active=True).first()
        if s and s.company_number:
            bkash_num = s.company_number
            bkash_type = s.account_type
            bkash_instruction = s.instruction_text
    except Exception:
        pass

    return {
        'SITE_NAME': getattr(settings, 'SITE_NAME', 'SoftobroCashBook'),
        'CURRENCY_SYMBOL': getattr(settings, 'CURRENCY_SYMBOL', '৳'),
        'BKASH_COMPANY_NUMBER': bkash_num,
        'BKASH_ACCOUNT_TYPE': bkash_type,
        'BKASH_INSTRUCTION_TEXT': bkash_instruction,
        'SUPPORT_EMAIL': getattr(settings, 'SUPPORT_EMAIL', 'support@softobrocashbook.com'),
        'SUPPORT_PHONE': getattr(settings, 'SUPPORT_PHONE', '+880 1700-000000'),
    }

