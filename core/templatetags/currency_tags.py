from decimal import Decimal
from django import template
from django.conf import settings

register = template.Library()


@register.filter(name='bdt')
def bdt(value):
    """
    Format a number as BDT currency, e.g. 12500.5 -> ৳ 12,500.50
    """
    if value is None or value == '':
        return f"{settings.CURRENCY_SYMBOL} 0.00"
    try:
        val = Decimal(str(value))
        formatted = f"{val:,.2f}"
        return f"{settings.CURRENCY_SYMBOL} {formatted}"
    except (ValueError, TypeError):
        return f"{settings.CURRENCY_SYMBOL} {value}"

