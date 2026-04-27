from django import template
from frontend.utils import get_website_name

register = template.Library()


@register.simple_tag
def website_name():
    """
    Returns the dynamic website name based on current language.
    Usage: {% website_name %}
    """
    return get_website_name()
