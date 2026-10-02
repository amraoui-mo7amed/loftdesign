from django import template

from core.content_i18n import tr as _tr

register = template.Library()


@register.filter
def tr(obj, field):
    """{{ product|tr:"title" }}: the text in the visitor's language, or the main text."""
    return _tr(obj, field)
